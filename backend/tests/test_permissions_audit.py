"""
Test Permissions Audit & Error Handlers
Tests Django REST Framework exception handler, AuditTrailMiddleware, and access denial logging.
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.exceptions import custom_exception_handler
from accounts.middleware import AuditTrailMiddleware
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework import status
from django.http import HttpResponse


class MockUser:
    def __init__(self, username='test_user', role='analyst', is_authenticated=True):
        self.username = username
        self.role = role
        self.is_authenticated = is_authenticated
        self._id = 'test_user_id'


def test_exception_handler_analyst_permission_denied():
    """Verify exception handler customizes message for read-only analyst role."""
    exc = PermissionDenied("You do not have permission.")
    
    # Mock DRF context
    request = MagicMock()
    request.path = '/api/evidence/carve/'
    request.method = 'POST'
    request.user = MockUser(role='analyst')
    context = {'request': request}
    
    with patch('accounts.models.AuditLog.log', return_value=True):
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 403
        assert response.data["code"] == "permission_denied"
        assert "Security Analyst role is Read-Only" in response.data["message"]
        assert "POST /api/evidence/carve/" in response.data["message"]


def test_exception_handler_session_expired():
    """Verify exception handler flags token expired messages with session_expired code."""
    exc = NotAuthenticated("Token has expired. Please log in again.")
    
    request = MagicMock()
    request.path = '/api/cases/'
    request.method = 'GET'
    request.user.is_authenticated = False
    context = {'request': request}
    
    with patch('accounts.models.AuditLog.log', return_value=True):
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 401
        assert response.data["code"] == "session_expired"
        assert "Session Expired" in response.data["message"]


def test_middleware_resolves_user_post_view():
    """Verify AuditTrailMiddleware logs correct user details after request processing."""
    # Mock request and response
    request = MagicMock()
    request.path = '/api/cases/create/'
    request.method = 'POST'
    request.META = {'HTTP_USER_AGENT': 'Mozilla/5.0', 'REMOTE_ADDR': '127.0.0.1'}
    
    # Emulate request.user being populated after get_response runs (view execution)
    user = MockUser(username='investigator_bob', role='investigator')
    
    def mock_get_response(req):
        req.user = user
        return HttpResponse("Created", status=201)
        
    middleware = AuditTrailMiddleware(mock_get_response)
    
    with patch.object(middleware, 'save_audit_log') as mock_save:
        response = middleware(request)
        
        assert response.status_code == 201
        assert mock_save.called
        
        # Verify the logged dictionary contains corrected resolved info
        logged_data = mock_save.call_args[0][0]
        assert logged_data["username"] == 'investigator_bob'
        assert logged_data["role"] == 'investigator'
        assert logged_data["permission_check_result"] == "Success"
        assert logged_data["is_authenticated"] is True


def test_middleware_intercepts_html_csrf_error():
    """Verify AuditTrailMiddleware translates raw HTML CSRF errors to structured JSON."""
    request = MagicMock()
    request.path = '/api/cases/'
    request.method = 'POST'
    request.META = {'HTTP_USER_AGENT': 'Mozilla/5.0', 'REMOTE_ADDR': '127.0.0.1'}
    
    # Mocking standard Django CSRF error page (status 403, HTML content)
    html_response = HttpResponse("<h1>Forbidden (403)</h1><p>CSRF verification failed.</p>", status=403)
    html_response['Content-Type'] = 'text/html'
    
    middleware = AuditTrailMiddleware(lambda req: html_response)
    
    with patch.object(middleware, 'save_audit_log'):
        response = middleware(request)
        
        assert response.status_code == 403
        assert response.headers['Content-Type'] == 'application/json'
        
        # Verify response content is JSON
        data = json.loads(response.content.decode('utf-8'))
        assert data["code"] == "csrf_error"
        assert "CSRF Error" in data["message"]


def test_evidence_viewset_rbac_permissions():
    """Verify that EvidenceViewSet actions require correct role permissions."""
    from evidence.views import EvidenceViewSet
    
    # Actions that require IsInvestigator (Investigator or Admin)
    investigator_actions = [
        'create', 'update', 'destroy', 'mark_analyzed',
        'recover_and_analyze', 'restore_files', 'photorec_carve',
        'testdisk_scan', 'autopsy_ingest', 'verify_integrity'
    ]
    
    # Actions that only require IsAuthenticated (Analyst, Investigator, or Admin)
    authenticated_actions = [
        'list', 'retrieve', 'exiftool', 'download_file'
    ]
    
    view = EvidenceViewSet()
    
    # Test for Analyst (should fail investigator actions, pass authenticated ones)
    analyst_user = MockUser(role='analyst')
    request_analyst = MagicMock()
    request_analyst.user = analyst_user
    
    for action_name in investigator_actions:
        view.action = action_name
        perms = view.get_permissions()
        has_investigator_perm = any(perm.__class__.__name__ == 'IsInvestigator' for perm in perms)
        assert has_investigator_perm, f"Action {action_name} should require IsInvestigator"
        
        allowed = all(perm.has_permission(request_analyst, view) for perm in perms)
        assert not allowed, f"Action {action_name} should be denied for analyst role"

    for action_name in authenticated_actions:
        view.action = action_name
        perms = view.get_permissions()
        has_investigator_perm = any(perm.__class__.__name__ == 'IsInvestigator' for perm in perms)
        assert not has_investigator_perm, f"Action {action_name} should not require IsInvestigator"
        
        allowed = all(perm.has_permission(request_analyst, view) for perm in perms)
        assert allowed, f"Action {action_name} should be allowed for analyst role"


def test_sector_aligned_file():
    """Verify SectorAlignedFile wrapper seeking and reading behaves correctly on standard files."""
    from forensic_engine.file_carver import SectorAlignedFile
    import tempfile
    import os
    
    # Create a temp file with known content
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Hello World. Sector alignment test content for raw drive reading.")
        tmp_name = tmp.name
        
    try:
        with SectorAlignedFile(tmp_name, sector_size=4) as f:
            assert f.seek(0) == 0
            assert f.read(5) == b"Hello"
            assert f.read(7) == b" World."
            assert f.seek(13) == 13
            assert f.read(6) == b"Sector"
            assert f.tell() == 19
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


if __name__ == "__main__":
    pytest.main([__file__])
