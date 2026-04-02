from django.urls import path
from .views import CaseViewSet

# Use simple URL patterns instead of router to avoid queryset requirement
urlpatterns = [
    path('', CaseViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='case-list'),
    path('<str:pk>/', CaseViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'update',
        'delete': 'destroy'
    }), name='case-detail'),
    path('<str:pk>/close/', CaseViewSet.as_view({'post': 'close'}), name='case-close'),
    path('<str:pk>/evidence/', CaseViewSet.as_view({'get': 'evidence'}), name='case-evidence'),
    path('<str:pk>/analyses/', CaseViewSet.as_view({'get': 'analyses'}), name='case-analyses'),
]
