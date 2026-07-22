from django.urls import path
from .views import (
    RecoveryStartView,
    PendingJobsView,
    RecoveryJobListView,
    RecoveryJobDetailView,
    RecoveredFileUploadView,
    RecoveredFilesListView,
    RecoveredFileDetailView,
    RecoveredFileSearchView,
    RecoveredFileHashVerifyView,
    RecoveredFilePreviewView,
    RecoveredFileDownloadView,
    RecoveryExportView,
    TimelineView,
    TimelineExportView,
    ChainOfCustodyExportView,
)

urlpatterns = [
    # Recovery jobs
    path('start/', RecoveryStartView.as_view(), name='recovery-start'),
    path('jobs/', RecoveryJobListView.as_view(), name='recovery-jobs-list'),
    path('jobs/pending/', PendingJobsView.as_view(), name='recovery-jobs-pending'),
    path('jobs/<str:pk>/', RecoveryJobDetailView.as_view(), name='recovery-job-detail'),
    path('jobs/<str:pk>/upload/', RecoveredFileUploadView.as_view(), name='recovery-file-upload'),

    # Recovered files
    path('files/', RecoveredFilesListView.as_view(), name='recovered-files-list'),
    path('files/search/', RecoveredFileSearchView.as_view(), name='recovered-files-search'),
    path('files/<str:pk>/', RecoveredFileDetailView.as_view(), name='recovered-file-detail'),
    path('files/<str:pk>/verify/', RecoveredFileHashVerifyView.as_view(), name='recovered-file-verify'),
    path('files/<str:pk>/preview/', RecoveredFilePreviewView.as_view(), name='recovered-file-preview'),
    path('files/<str:pk>/download/', RecoveredFileDownloadView.as_view(), name='recovered-file-download'),

    # Export
    path('export/', RecoveryExportView.as_view(), name='recovery-export'),

    # Timeline
    path('timeline/', TimelineView.as_view(), name='recovery-timeline'),
    path('timeline/export/', TimelineExportView.as_view(), name='recovery-timeline-export'),

    # Chain of Custody export
    path('coc/export/', ChainOfCustodyExportView.as_view(), name='coc-export'),
]
