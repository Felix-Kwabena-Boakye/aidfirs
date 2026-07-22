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
    POST  /api/devices/scan/  — Returns status (actual scanning is performed by the local agent)
    DELETE /api/devices/scan/ — Returns status
    Admin / Investigator only.
    """
    permission_classes = [IsInvestigator]

    def post(self, request):
        devices = Device.get_all()
        return Response({
            "status": "agent_driven",
            "message": "Device scanning is performed by the AIDFIRS Local Forensic Agent. Connect the agent to this backend to register devices.",
            "registered_devices": len(devices),
        })

    def delete(self, request):
        return Response({
            "status": "agent_driven",
            "message": "Device monitoring is controlled by the AIDFIRS Local Forensic Agent."
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
            hash_sha256=data.get("hash_sha256", ""),
            hash_md5=data.get("hash_md5", ""),
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
                    f"SHA256 fingerprint: {device.hash_sha256[:16]}..."
                ),
                hash_after=device.hash_sha256
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
                    "hash_sha256": device.hash_sha256,
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
