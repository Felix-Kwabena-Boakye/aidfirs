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
