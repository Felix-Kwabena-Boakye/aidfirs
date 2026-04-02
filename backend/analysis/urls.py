from django.urls import path
from .views import AnalysisResultViewSet

# Use simple URL patterns instead of router to avoid queryset requirement
urlpatterns = [
    path('', AnalysisResultViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='analysis-list'),
    path('chat/', AnalysisResultViewSet.as_view({'post': 'chat'}), name='analysis-chat'),
    path('evidence-suggestions/', AnalysisResultViewSet.as_view({'post': 'evidence_suggestions'}), name='analysis-evidence-suggestions'),
    path('classify/', AnalysisResultViewSet.as_view({'post': 'classify'}), name='analysis-classify'),
    path('detect-anomalies/', AnalysisResultViewSet.as_view({'post': 'detect_anomalies'}), name='analysis-detect-anomalies'),
    path('generate-report/', AnalysisResultViewSet.as_view({'post': 'generate_report'}), name='analysis-generate-report'),
    path('<str:pk>/', AnalysisResultViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'update',
        'delete': 'destroy'
    }), name='analysis-detail'),
    path('<str:pk>/complete/', AnalysisResultViewSet.as_view({'post': 'complete'}), name='analysis-complete'),
]
