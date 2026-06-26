import os
import sys

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.permissions import IsAdmin, IsInvestigator
from analysis.views import AnalysisResultViewSet


class MockUser:
    def __init__(self, role='analyst', is_authenticated=True):
        self.role = role
        self.is_authenticated = is_authenticated
        self._id = 'test_user_id'
        self.username = f'{role}_user'


class MockRequest:
    def __init__(self, user=None, method='GET', data=None):
        self.user = user
        self.method = method
        self.data = data or {}


def _perm_for_action(action: str, request):
    view = AnalysisResultViewSet()
    view.action = action
    perms = view.get_permissions()
    # get_permissions returns instances; test first one
    perm = perms[0]
    return perm.has_permission(request, view)


@pytest.mark.parametrize(
    "role,action,expected",
    [
        ('admin', 'chat', True),
        ('investigator', 'chat', True),
        ('analyst', 'chat', True),

        ('admin', 'classify', True),
        ('investigator', 'classify', True),
        ('analyst', 'classify', False),

        ('admin', 'detect_anomalies', True),
        ('investigator', 'detect_anomalies', True),
        ('analyst', 'detect_anomalies', False),

        ('admin', 'generate_report', True),
        ('investigator', 'generate_report', True),
        ('analyst', 'generate_report', False),

        # evidence suggestions also requires investigator/admin
        ('admin', 'evidence_suggestions', True),
        ('investigator', 'evidence_suggestions', True),
        ('analyst', 'evidence_suggestions', False),

        # system_execute admin-only
        ('admin', 'system_execute', True),
        ('investigator', 'system_execute', False),
        ('analyst', 'system_execute', False),

        # train_model admin-only
        ('admin', 'train_model', True),
        ('investigator', 'train_model', False),
        ('analyst', 'train_model', False),

        # predict_recoverability investigator/admin allowed
        ('admin', 'predict_recoverability', True),
        ('investigator', 'predict_recoverability', True),
        ('analyst', 'predict_recoverability', False),
    ],
)
def test_analysis_action_level_rbac(role, action, expected):
    user = MockUser(role=role)
    request = MockRequest(user=user, method='POST')
    assert _perm_for_action(action, request) is expected


def test_analysis_action_level_rbac_unauthenticated():
    request = MockRequest(user=None, method='POST')
    assert _perm_for_action('chat', request) is False
    assert _perm_for_action('system_execute', request) is False


