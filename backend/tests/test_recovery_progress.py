import os
import sys
import json
import pytest
from django.http import StreamingHttpResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from evidence.views import EvidenceViewSet
from evidence.models import Evidence
from rest_framework.test import APIRequestFactory, force_authenticate


class MockUser:
    def __init__(self, role='admin', is_authenticated=True):
        self.role = role
        self.is_authenticated = is_authenticated
        self._id = 'admin_user_id'
        self.username = 'admin_user'


def test_tsk_recover_deleted_streaming():
    # Create request factory
    factory = APIRequestFactory()
    
    # Mock evidence item
    class MockEvidence:
        def __init__(self):
            self._id = "test_evidence_id"
            self.file_path = "mock_drive_path"
            self.case_id = "test_case_id"
            
    mock_ev = MockEvidence()
    
    from unittest.mock import patch
    
    with patch.object(Evidence, 'get_by_id', return_value=mock_ev):
        # Create request
        request = factory.post('/api/evidence/test_evidence_id/tsk_recover_deleted/', {'offset': '0'}, format='json')
        
        # Authenticate user
        user = MockUser(role='admin')
        force_authenticate(request, user=user)
        
        # Instantiate view set and call action
        view = EvidenceViewSet()
        view.action = 'tsk_recover_deleted'
        
        # Mock _check_evidence_access to return True
        with patch.object(view, '_check_evidence_access', return_value=True):
            # Mock the sub-methods in windows_recovery/metadata_recovery/file_carver
            with patch('forensic_engine.windows_recovery.scan_recycle_bin', return_value=[]), \
                 patch('forensic_engine.windows_recovery.recover_files_from_recycle_bin', return_value=[]), \
                 patch('forensic_engine.windows_recovery.scan_drive_signatures', return_value=[]), \
                 patch('forensic_api.tsk_wrapper.get_deleted_metadata', return_value={'mock': True, 'metadata': []}), \
                 patch('forensic_engine.file_carver.FileCarver.carve_disk_image', return_value=[]), \
                 patch('forensic_engine.file_carver.FileCarver.extract_carved_bytes', return_value=[]), \
                 patch('forensic_engine.metadata_recovery.DiskImageAnalyzer.full_analysis', return_value={'recovered_files': [], 'timestamps': []}):
                
                response = view.tsk_recover_deleted(request, pk="test_evidence_id")
                
                # Assertions
                assert response is not None
                assert isinstance(response, StreamingHttpResponse)
                assert response.status_code == 200
                assert response['Content-Type'] == 'text/event-stream'
                
                # Consume stream
                content = b"".join(response.streaming_content).decode('utf-8')
                lines = content.strip().split('\n\n')
                
                # Verify we get the expected SSE events
                assert len(lines) > 0
                events = []
                for line in lines:
                    if line.startswith('data: '):
                        data_str = line[6:]
                        events.append(json.loads(data_str))
                
                # Assert at least one processing and one completed event
                assert any(e['status'] == 'processing' for e in events)
                assert any(e['status'] == 'completed' for e in events)
                
                # Check completed event content
                completed_event = next(e for e in events if e['status'] == 'completed')
                assert completed_event['data']['success'] is True
