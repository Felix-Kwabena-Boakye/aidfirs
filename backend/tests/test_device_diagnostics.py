"""
Test Device Diagnostics
Tests Docker detection, path mapping, existence/permission checks, and API endpoints
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from devices.diagnostics import detect_docker, resolve_mapped_path, run_diagnostics
from devices.views import DeviceDiagnosticsView
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status


class MockUser:
    def __init__(self, role='admin', is_authenticated=True):
        self.role = role
        self.is_authenticated = is_authenticated
        self._id = 'admin_user_id'
        self.username = 'admin_user'


def test_detect_docker():
    """Test Docker container detection."""
    # Scenario A: /.dockerenv exists
    with patch('os.path.exists', return_value=True):
        assert detect_docker() is True

    # Scenario B: /.dockerenv does not exist, check cgroup containing docker
    with patch('os.path.exists', return_value=False), \
         patch('builtins.open', mock_open(read_data="1:name=systemd:/docker/123456abcdef\n")):
        assert detect_docker() is True

    # Scenario C: Not running inside container
    with patch('os.path.exists', return_value=False), \
         patch('builtins.open', side_effect=FileNotFoundError):
        assert detect_docker() is False


def test_resolve_mapped_path():
    """Test path mapping translation logic."""
    # Scenario A: On Windows, should keep original path
    with patch('platform.system', return_value='Windows'):
        assert resolve_mapped_path('D:\\') == 'D:\\'
        assert resolve_mapped_path('E:\\forensics\\img.raw') == 'E:\\forensics\\img.raw'

    # Scenario B: On Linux/Docker, maps drive letters
    with patch('platform.system', return_value='Linux'):
        # Mock os.path.exists so that the mapped mount exists
        def mock_exists(p):
            return p == '/mnt/d'
        
        with patch('os.path.exists', side_effect=mock_exists):
            assert resolve_mapped_path('D:\\') == '/mnt/d'
            assert resolve_mapped_path('d:') == '/mnt/d'
            assert resolve_mapped_path('D:') == '/mnt/d'

        # Default fallback when no candidate path exists
        with patch('os.path.exists', return_value=False):
            assert resolve_mapped_path('E:') == '/mnt/e'


def test_run_diagnostics_no_path():
    """Test run_diagnostics when path is empty."""
    report = run_diagnostics("")
    assert report["success"] is False
    assert report["checks"]["drive_existence"]["status"] == "failed"
    assert "No drive path" in report["checks"]["drive_existence"]["message"]


def test_run_diagnostics_not_found():
    """Test run_diagnostics when resolved path does not exist."""
    with patch('os.path.exists', return_value=False):
        report = run_diagnostics("D:\\")
        assert report["success"] is False
        assert report["checks"]["drive_existence"]["status"] == "failed"
        assert "not found" in report["checks"]["drive_existence"]["message"].lower()


def test_run_diagnostics_permission_denied():
    """Test run_diagnostics when path exists but raising PermissionError."""
    with patch('os.path.exists', return_value=True), \
         patch('os.path.isdir', return_value=True), \
         patch('os.listdir', side_effect=PermissionError("Mock Permission Error")):
        report = run_diagnostics("D:\\")
        assert report["success"] is False
        assert report["checks"]["read_permissions"]["status"] == "failed"
        assert "mock permission error" in report["checks"]["read_permissions"]["message"].lower()


def test_run_diagnostics_success_with_warnings():
    """Test run_diagnostics passes, mocking tool checks."""
    # Mocking tool paths check and directory listing
    def side_effect_exists(p):
        p_clean = str(p).replace('\\', '/').rstrip('/')
        if p_clean in ["D:", "D:/"]:
            return True
        return False

    with patch('os.path.exists', side_effect=side_effect_exists), \
         patch('os.path.isdir', return_value=True), \
         patch('os.listdir', return_value=[]), \
         patch('shutil.which', return_value=None):  # Tools missing
        report = run_diagnostics("D:\\")
        assert report["success"] is True
        assert report["checks"]["drive_existence"]["status"] == "success"
        assert report["checks"]["read_permissions"]["status"] == "success"
        assert report["checks"]["forensic_tools"]["status"] == "warning"


def test_diagnostics_endpoint_unauthenticated():
    """Test diagnostics endpoint rejects unauthenticated request."""
    factory = APIRequestFactory()
    request = factory.post('/api/devices/diagnostics/', {"device_path": "D:\\"}, format='json')
    request.user = None
    
    view = DeviceDiagnosticsView.as_view()
    response = view(request)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_diagnostics_endpoint_empty_path():
    """Test diagnostics endpoint requires device_path parameter."""
    factory = APIRequestFactory()
    request = factory.post('/api/devices/diagnostics/', {}, format='json')
    user = MockUser()
    request.user = user
    force_authenticate(request, user=user)
    
    view = DeviceDiagnosticsView.as_view()
    response = view(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "No device path provided" in response.data["error"]


def test_diagnostics_endpoint_success():
    """Test diagnostics endpoint succeeds and returns report structure."""
    factory = APIRequestFactory()
    request = factory.post('/api/devices/diagnostics/', {"device_path": "D:\\"}, format='json')
    # Manually populate request.data for Django REST Framework compat
    request.data = {"device_path": "D:\\"}
    user = MockUser()
    request.user = user
    force_authenticate(request, user=user)
    
    view = DeviceDiagnosticsView.as_view()
    
    # Mock run_diagnostics to avoid relying on actual host drive letters/tools
    mock_report = {
        "device_path": "D:\\",
        "resolved_path": "D:\\",
        "is_docker": False,
        "checks": {
            "docker_environment": {"status": "success", "label": "Containerized check", "message": "N/A"},
            "drive_existence": {"status": "success", "label": "Drive Existence", "message": "Drive detected"},
            "read_permissions": {"status": "success", "label": "Read Permissions", "message": "Read access granted"},
            "forensic_tools": {"status": "success", "label": "Forensic Tools", "message": "All tools available"}
        },
        "success": True,
        "logs": ["Done"],
        "recommended_action": ""
    }
    
    with patch('devices.views.run_diagnostics', return_value=mock_report):
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["device_path"] == "D:\\"
        assert "drive_existence" in response.data["checks"]


# Helper function to mock builtins.open
def mock_open(read_data=""):
    import io
    def open_mock(filename, *args, **kwargs):
        return io.StringIO(read_data)
    return open_mock


if __name__ == "__main__":
    pytest.main([__file__])
