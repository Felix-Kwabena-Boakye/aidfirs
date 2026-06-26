from django.urls import path
from .views import DeviceListView, DeviceScanView, DeviceRefreshView, InotifyLogsView, DeviceDiagnosticsView

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('scan/', DeviceScanView.as_view(), name='device-scan'),
    path('refresh/', DeviceRefreshView.as_view(), name='device-refresh'),
    path('inotify-logs/', InotifyLogsView.as_view(), name='device-inotify-logs'),
    path('diagnostics/', DeviceDiagnosticsView.as_view(), name='device-diagnostics'),
]
