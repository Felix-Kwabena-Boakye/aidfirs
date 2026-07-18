from django.urls import path
from .views import (
    RecoveryStartView, PendingJobsView, RecoveryJobDetailView,
    RecoveredFileUploadView, RecoveredFilesListView, RecoveredFileDownloadView
)

urlpatterns = [
    path('start/', RecoveryStartView.as_view(), name='recovery-start'),
    path('jobs/pending/', PendingJobsView.as_view(), name='recovery-pending-jobs'),
    path('jobs/<str:pk>/', RecoveryJobDetailView.as_view(), name='recovery-job-detail'),
    path('jobs/<str:pk>/upload/', RecoveredFileUploadView.as_view(), name='recovered-file-upload'),
    path('files/', RecoveredFilesListView.as_view(), name='recovered-files-list'),
    path('files/<str:pk>/download/', RecoveredFileDownloadView.as_view(), name='recovered-file-download'),
]
