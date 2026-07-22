from django.urls import path
from .views import (
    ReportGenerateView,
    ReportListView,
    ReportDetailView,
    ReportDownloadView,
)

urlpatterns = [
    path('generate/', ReportGenerateView.as_view(), name='report-generate'),
    path('', ReportListView.as_view(), name='report-list'),
    path('<str:pk>/', ReportDetailView.as_view(), name='report-detail'),
    path('<str:pk>/download/', ReportDownloadView.as_view(), name='report-download'),
]
