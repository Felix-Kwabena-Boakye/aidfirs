from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsInvestigator
from .models import Device
from .serializers import DeviceSerializer


class DeviceListView(APIView):
    """
    GET /api/devices/
    Returns the current list of registered USB/removable devices from MongoDB.
    Accessible by any authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = Device.get_all()
        return Response({
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
            "scanning": True,  # Maintain backwards compatibility
        })


class DeviceScanView(APIView):
    """
    POST  /api/devices/scan/  — start scanning (mocked)
    DELETE /api/devices/scan/ — stop scanning (mocked)
    Admin / Investigator only.
    """
    permission_classes = [IsInvestigator]

    def post(self, request):
        return Response({"status": "scanning started"})

    def delete(self, request):
        return Response({"status": "scanning stopped"})


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
    Requires authenticated user (agent).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from cases.coc_models import ChainOfCustody
        from accounts.models import AuditLog

        serializer = DeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device = Device.create(
            device_name=data["device_name"],
            serial_number=data["serial_number"],
            model=data["model"],
            filesystem=data["filesystem"],
            size_gb=data["size_gb"],
            drive_letter=data["drive_letter"],
            connected_at=data.get("connected_at"),
            source=data.get("source", "AIDFIRS Agent")
        )

        # Log DEVICE_CONNECTED action
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
                notes=f"Device {device.device_name} (Serial: {device.serial_number}) connected via AIDFIRS Forensic Agent."
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
        from forensic_engine.inotify_monitor import inotify_monitor
        # Auto-ensure monitor is active
        if not inotify_monitor._running:
            inotify_monitor.start()
        return Response({
            "events": inotify_monitor.get_events(),
            "count": len(inotify_monitor.get_events()),
            "watch_dir": inotify_monitor.watch_dir
        })

from rest_framework import status
from .diagnostics import run_diagnostics

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
        
        report = run_diagnostics(device_path)
        return Response(report)


# Auto-start inotify monitor thread on backend load
from forensic_engine.inotify_monitor import inotify_monitor
try:
    inotify_monitor.start()
except Exception:
    pass
