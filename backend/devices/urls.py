from django.urls import path
from .views import DeviceListView, DeviceScanView, DeviceRefreshView

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('scan/', DeviceScanView.as_view(), name='device-scan'),
    path('refresh/', DeviceRefreshView.as_view(), name='device-refresh'),
]
