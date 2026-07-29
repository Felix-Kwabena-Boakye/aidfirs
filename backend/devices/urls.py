from django.urls import path
from .views import (
    DeviceListView, DeviceDetailView, DeviceScanView,
    DeviceRefreshView, InotifyLogsView, DeviceDiagnosticsView, DeviceRegisterView
)

urlpatterns = [
    # Static named routes MUST come BEFORE dynamic <str:pk> to avoid
    # Django matching 'scan', 'refresh', etc. as primary keys.
    path('scan/', DeviceScanView.as_view(), name='device-scan'),
    path('scan', DeviceScanView.as_view()),
    path('refresh/', DeviceRefreshView.as_view(), name='device-refresh'),
    path('refresh', DeviceRefreshView.as_view()),
    path('register/', DeviceRegisterView.as_view(), name='device-register'),
    path('register', DeviceRegisterView.as_view()),
    path('inotify-logs/', InotifyLogsView.as_view(), name='device-inotify-logs'),
    path('inotify-logs', InotifyLogsView.as_view()),
    path('diagnostics/', DeviceDiagnosticsView.as_view(), name='device-diagnostics'),
    path('diagnostics', DeviceDiagnosticsView.as_view()),
    # Dynamic primary-key route — keep LAST so named routes above take priority
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('<str:pk>', DeviceDetailView.as_view()),
    # Root list
    path('', DeviceListView.as_view(), name='device-list'),
]
