from django.urls import path
from .views import (
    DeviceListView, DeviceDetailView, DeviceScanView,
    DeviceRefreshView, InotifyLogsView, DeviceDiagnosticsView, DeviceRegisterView
)

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('scan/', DeviceScanView.as_view(), name='device-scan'),
    path('refresh/', DeviceRefreshView.as_view(), name='device-refresh'),
    path('register/', DeviceRegisterView.as_view(), name='device-register'),
    path('inotify-logs/', InotifyLogsView.as_view(), name='device-inotify-logs'),
    path('diagnostics/', DeviceDiagnosticsView.as_view(), name='device-diagnostics'),
]
