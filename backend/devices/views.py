from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .usb_detector import usb_monitor
from accounts.permissions import IsInvestigator


class DeviceListView(APIView):
    """
    GET /api/devices/
    Returns the current list of USB/removable devices.
    Accessible by any authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = usb_monitor.scan_now()
        return Response({
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
            "scanning": usb_monitor._running,
        })


class DeviceScanView(APIView):
    """
    POST  /api/devices/scan/  — start background scanning
    DELETE /api/devices/scan/ — stop background scanning
    Admin / Investigator only.
    """
    permission_classes = [IsInvestigator]

    def post(self, request):
        usb_monitor.start()
        return Response({"status": "scanning started"})

    def delete(self, request):
        usb_monitor.stop()
        return Response({"status": "scanning stopped"})


class DeviceRefreshView(APIView):
    """
    POST /api/devices/refresh/
    Force an immediate scan and return results.
    Admin / Investigator only.
    """
    permission_classes = [IsInvestigator]

    def post(self, request):
        devices = usb_monitor.scan_now()
        return Response({
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
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
