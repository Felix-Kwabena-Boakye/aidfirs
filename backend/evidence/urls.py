from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EvidenceViewSet

# Use simple URL patterns instead of router to avoid queryset requirement
urlpatterns = [
    path('', EvidenceViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='evidence-list'),
    path('<str:pk>/', EvidenceViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'update',
        'delete': 'destroy'
    }), name='evidence-detail'),
    path('<str:pk>/analyze/', EvidenceViewSet.as_view({'post': 'analyze'}), name='evidence-analyze'),
    path('<str:pk>/mark_analyzed/', EvidenceViewSet.as_view({'post': 'mark_analyzed'}), name='evidence-mark-analyzed'),
    path('lookup_hash/', EvidenceViewSet.as_view({'post': 'lookup_hash'}), name='evidence-lookup-hash'),
    path('<str:pk>/tsk_image/', EvidenceViewSet.as_view({'post': 'tsk_image'}), name='evidence-tsk-image'),
    path('<str:pk>/tsk_partitions/', EvidenceViewSet.as_view({'post': 'tsk_partitions'}), name='evidence-tsk-partitions'),
    path('<str:pk>/tsk_files/', EvidenceViewSet.as_view({'post': 'tsk_files'}), name='evidence-tsk-files'),
    path('<str:pk>/tsk_extract/', EvidenceViewSet.as_view({'post': 'tsk_extract'}), name='evidence-tsk-extract'),
    path('<str:pk>/tsk_timeline/', EvidenceViewSet.as_view({'post': 'tsk_timeline'}), name='evidence-tsk-timeline'),
    path('<str:pk>/tsk_recovered_metadata/', EvidenceViewSet.as_view({'post': 'tsk_recovered_metadata'}), name='evidence-tsk-recovered-metadata'),
    path('<str:pk>/tsk_recover_deleted/', EvidenceViewSet.as_view({'post': 'tsk_recover_deleted'}), name='evidence-tsk-recover-deleted'),
    path('<str:pk>/tsk_recover_specific/', EvidenceViewSet.as_view({'post': 'tsk_recover_specific'}), name='evidence-tsk-recover-specific'),
    path('<str:pk>/report/', EvidenceViewSet.as_view({'get': 'report'}), name='evidence-report'),
    path('<str:pk>/recovery_json/', EvidenceViewSet.as_view({'post': 'recovery_json'}), name='evidence-recovery-json'),
    path('<str:pk>/download-file/', EvidenceViewSet.as_view({'get': 'download_file'}), name='evidence-download-file'),
    path('<str:pk>/photorec-carve/', EvidenceViewSet.as_view({'post': 'photorec_carve'}), name='evidence-photorec-carve'),
    path('<str:pk>/testdisk-scan/', EvidenceViewSet.as_view({'post': 'testdisk_scan'}), name='evidence-testdisk-scan'),
    path('<str:pk>/autopsy-ingest/', EvidenceViewSet.as_view({'post': 'autopsy_ingest'}), name='evidence-autopsy-ingest'),
    path('<str:pk>/exiftool/', EvidenceViewSet.as_view({'post': 'exiftool'}), name='evidence-exiftool'),
    path('<str:pk>/recover-and-analyze/', EvidenceViewSet.as_view({'post': 'recover_and_analyze'}), name='evidence-recover-and-analyze'),
    path('<str:pk>/restore-files/', EvidenceViewSet.as_view({'post': 'restore_files'}), name='evidence-restore-files'),

]

