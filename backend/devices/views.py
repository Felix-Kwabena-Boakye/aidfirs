from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from accounts.permissions import IsInvestigator
from .models import Device
from .serializers import DeviceSerializer


class DeviceListView(APIView):
    """
    GET /api/devices/
    Returns the current list of registered forensic devices from MongoDB.
    Accessible by any authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = Device.get_all()
        return Response({
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
            "scanning": False,  # Real scanning happens via local agent
        })


class DeviceDetailView(APIView):
    """
    GET  /api/devices/<pk>/  — Get device details
    DELETE /api/devices/<pk>/ — Remove device from registry
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        device = Device.get_by_id(pk)
        if not device:
            return Response({"success": False, "error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "device": device.to_dict()})

    def delete(self, request, pk):
        if request.user.role not in ('admin', 'investigator'):
            return Response({"success": False, "error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        device = Device.get_by_id(pk)
        if not device:
            return Response({"success": False, "error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        Device.delete_by_id(pk)

        try:
            from accounts.models import AuditLog
            AuditLog.log(
                user_id=str(request.user._id),
                username=request.user.username,
                action="DEVICE_REMOVED",
                resource_type="device",
                resource_id=str(pk),
                details={"device_name": device.device_name, "serial": device.serial_number}
            )
        except Exception:
            pass

        return Response({"success": True, "message": "Device removed from registry"})


class DeviceScanView(APIView):
    """
    POST   /api/devices/scan/   — Trigger a device scan
    DELETE /api/devices/scan/   — Stop active scanning (agent-driven)

    This view coordinates with the local AIDFIRS Forensic Agent to
    detect connected USB / external drives.  If the agent is reachable
    the backend returns its live device list; otherwise it falls back
    to previously registered devices from MongoDB.

    Admin / Investigator only.
    """
    permission_classes = [IsInvestigator]

    AGENT_HEALTH_URL = "http://127.0.0.1:8765/health"
    AGENT_SCAN_URL = "http://127.0.0.1:8765/devices"

    def _probe_agent(self):
        """Try to contact the local forensic agent.  Returns (ok, data)."""
        import requests as req
        try:
            r = req.get(self.AGENT_HEALTH_URL, timeout=3)
            if r.status_code == 200:
                return True, r.json()
        except (req.ConnectionError, req.Timeout):
            pass
        except Exception:
            pass
        return False, None

    def _agent_scan(self):
        """Ask the agent to return current device list."""
        import requests as req
        try:
            r = req.get(self.AGENT_SCAN_URL, timeout=5)
            if r.status_code == 200:
                return r.json().get("devices", [])
        except (req.ConnectionError, req.Timeout):
            pass
        except Exception:
            pass
        return None

    def _direct_scan(self):
        """Perform direct USB detection on host if agent HTTP is offline."""
        try:
            import sys
            import os
            agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'aidfirs-agent'))
            if agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
            from usb.detector import get_usb_devices
            devs = get_usb_devices()
            return [d.to_dict() for d in devs]
        except Exception as e:
            print(f"[DeviceScanView] Direct local USB scan note: {e}")
            return []

    def post(self, request):
        agent_ok, agent_health = self._probe_agent()
        agent_devices_raw = self._agent_scan()

        if not agent_devices_raw:
            agent_devices_raw = self._direct_scan()

        # Save/update detected devices into MongoDB
        if agent_devices_raw:
            for raw in agent_devices_raw:
                try:
                    serial = raw.get("serial_number", "")
                    drive_letter = raw.get("drive_letter", "")
                    existing = Device.get_all()
                    already_exists = any(
                        (serial and d.serial_number == serial) or
                        (drive_letter and d.drive_letter == drive_letter)
                        for d in existing
                    )
                    if not already_exists:
                        Device.create(
                            device_name=raw.get("volume_name") or raw.get("model") or "USB Drive",
                            serial_number=serial,
                            model=raw.get("model", ""),
                            filesystem=raw.get("filesystem", ""),
                            size_gb=float(raw.get("size_gb") or raw.get("capacity") or 0.0),
                            drive_letter=drive_letter,
                            source=raw.get("source", "AIDFIRS Agent"),
                            vendor=raw.get("vendor", ""),
                            manufacturer=raw.get("manufacturer", ""),
                            bus_type=raw.get("bus_type", "USB"),
                            device_path=raw.get("device_path", ""),
                            volume_label=raw.get("volume_label", ""),
                            mount_point=raw.get("mount_point", ""),
                            capacity_bytes=int(raw.get("capacity_bytes") or 0),
                            drive_type=raw.get("drive_type", "USB Drive"),
                        )
                except Exception as ex:
                    print(f"[DeviceScanView] Device save notice: {ex}")

        # Fetch current MongoDB stored devices
        db_devices = Device.get_all()

        # Merge live agent results with DB
        merged = []
        seen_serials = set()

        if agent_devices_raw:
            for raw in agent_devices_raw:
                serial = raw.get("serial_number", "")
                if serial and serial not in seen_serials:
                    seen_serials.add(serial)
                merged.append(raw)

        for d in db_devices:
            serial = d.serial_number
            if serial and serial not in seen_serials:
                seen_serials.add(serial)
                merged.append(d.to_dict())
            elif not serial and d.to_dict() not in merged:
                merged.append(d.to_dict())

        # Update scanning flag
        from django.conf import settings
        settings.DEVICE_SCANNING_ACTIVE = True

        return Response({
            "status": "scanning_started",
            "agent_reachable": agent_ok or len(agent_devices_raw) > 0,
            "agent_info": agent_health,
            "devices": merged,
            "count": len(merged),
            "scanning": True,
            "message": (
                f"Auto-Scan active. Detected {len(merged)} USB / storage device(s)."
            ),
        })

    def delete(self, request):
        from django.conf import settings
        settings.DEVICE_SCANNING_ACTIVE = False
        return Response({
            "status": "scanning_stopped",
            "scanning": False,
            "message": "Auto-scan deactivated.  The local forensic agent controls monitoring."
        })


class DeviceRefreshView(APIView):
    """
    POST /api/devices/refresh/
    Return the current saved devices from MongoDB.
    Admin / Investigator only.
    """
    permission_classes = [IsInvestigator]

    def post(self, request):
        devices = Device.get_all()
        return Response({
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
        })


class DeviceRegisterView(APIView):
    """
    POST /api/devices/register/
    Register a device connected to a local agent.
    Called by the AIDFIRS Local Forensic Agent with JWT authentication.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from cases.coc_models import ChainOfCustody
        from accounts.models import AuditLog
        from recovery.models import TimelineEvent

        serializer = DeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device = Device.create(
            device_name=data["device_name"],
            serial_number=data.get("serial_number", ""),
            model=data.get("model", ""),
            filesystem=data.get("filesystem", ""),
            size_gb=data.get("size_gb", 0.0),
            drive_letter=data.get("drive_letter", ""),
            connected_at=data.get("connected_at"),
            source=data.get("source", "AIDFIRS Agent"),
            # Extended forensic fields
            vendor=data.get("vendor", ""),
            manufacturer=data.get("manufacturer", ""),
            bus_type=data.get("bus_type", ""),
            device_path=data.get("device_path", ""),
            volume_label=data.get("volume_label", ""),
            mount_point=data.get("mount_point", ""),
            capacity_bytes=data.get("capacity_bytes", 0),
            drive_type=data.get("drive_type", "USB Drive"),
        )

        # Log forensic audit trail
        try:
            AuditLog.log(
                user_id=str(request.user._id),
                username=request.user.username,
                action="DEVICE_CONNECTED",
                resource_type="device",
                resource_id=str(device._id),
                details=device.to_dict()
            )
            ChainOfCustody.create(
                case_id="global",
                evidence_id=str(device._id),
                action="DEVICE_CONNECTED",
                performed_by=request.user.username,
                notes=(
                    f"Device '{device.device_name}' (Serial: {device.serial_number}, "
                    f"Model: {device.model}, Bus: {device.bus_type}) "
                    f"connected via AIDFIRS Forensic Agent. "
                    f"Identity fingerprint: {device.device_fingerprint[:16]}... "
                    f"(deterministic serial:model digest — not an evidence content hash)"
                ),
                hash_before='',
                hash_after='',
                hash_status="hash unavailable",
            )
            TimelineEvent.create(
                case_id="global",
                event_type="DEVICE_CONNECTED",
                description=(
                    f"Forensic device '{device.device_name}' detected and registered. "
                    f"Drive: {device.drive_letter}, Serial: {device.serial_number}, "
                    f"Size: {device.size_gb}GB, Bus: {device.bus_type}"
                ),
                actor=request.user.username,
                device_id=str(device._id),
                metadata={
                    "serial": device.serial_number,
                    "model": device.model,
                    "filesystem": device.filesystem,
                    "size_gb": device.size_gb,
                    "bus_type": device.bus_type,
                    "device_fingerprint": device.device_fingerprint,
                }
            )
        except Exception as e:
            print(f"[DeviceRegister] Logging failed: {e}")

        return Response({
            "success": True,
            "message": "Device registered successfully",
            "device": device.to_dict()
        })


class InotifyLogsView(APIView):
    """
    GET /api/devices/inotify-logs/
    Returns the recent filesystem inotify events list.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from forensic_engine.inotify_monitor import inotify_monitor
            if not inotify_monitor._running:
                inotify_monitor.start()
            return Response({
                "events": inotify_monitor.get_events(),
                "count": len(inotify_monitor.get_events()),
                "watch_dir": inotify_monitor.watch_dir
            })
        except Exception as e:
            return Response({
                "events": [],
                "count": 0,
                "watch_dir": "",
                "note": f"Inotify monitor not available: {str(e)}"
            })


class DeviceDiagnosticsView(APIView):
    """
    POST /api/devices/diagnostics/
    Expects body: {"device_path": "..."}
    Runs device accessibility, permissions, tool check diagnostics.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_path = request.data.get("device_path", "")
        if not device_path:
            return Response({"success": False, "error": "No device path provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .diagnostics import run_diagnostics
            report = run_diagnostics(device_path)
            return Response(report)
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e),
                "note": "Diagnostics unavailable — ensure the local forensic agent is running."
            })


# Auto-start inotify monitor thread on backend load (non-fatal)
try:
    from forensic_engine.inotify_monitor import inotify_monitor
    inotify_monitor.start()
except Exception:
    pass
