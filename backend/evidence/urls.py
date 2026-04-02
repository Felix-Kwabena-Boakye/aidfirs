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
    path('<str:pk>/report/', EvidenceViewSet.as_view({'get': 'report'}), name='evidence-report'),
]
