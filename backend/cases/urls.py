from django.urls import path
from .views import CaseViewSet

urlpatterns = [

    # Case CRUD
    path(
        '',
        CaseViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='case-list'
    ),

    # Global Search
    path(
        'search/',
        CaseViewSet.as_view({
            'get': 'search'
        }),
        name='case-search'
    ),

    # Single Case
    path(
        '<str:pk>/',
        CaseViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'update',
            'delete': 'destroy'
        }),
        name='case-detail'
    ),

    # Close
    path(
        '<str:pk>/close/',
        CaseViewSet.as_view({
            'post': 'close'
        }),
        name='case-close'
    ),

    # Archive
    path(
        '<str:pk>/archive/',
        CaseViewSet.as_view({
            'post': 'archive'
        }),
        name='case-archive'
    ),

    # Assign
    path(
        '<str:pk>/assign/',
        CaseViewSet.as_view({
            'post': 'assign'
        }),
        name='case-assign'
    ),

    # Evidence
    path(
        '<str:pk>/evidence/',
        CaseViewSet.as_view({
            'get': 'evidence'
        }),
        name='case-evidence'
    ),

    # Analysis
    path(
        '<str:pk>/analyses/',
        CaseViewSet.as_view({
            'get': 'analyses'
        }),
        name='case-analyses'
    ),

    # Timeline
    path(
        '<str:pk>/timeline/',
        CaseViewSet.as_view({
            'get': 'timeline'
        }),
        name='case-timeline'
    ),

    # Chain of Custody
    path(
        '<str:pk>/chain_of_custody/',
        CaseViewSet.as_view({
            'get': 'chain_of_custody'
        }),
        name='case-chain-of-custody'
    ),
]
