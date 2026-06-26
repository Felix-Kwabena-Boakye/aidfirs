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


def test_recover_and_analyze_streaming():
    # Create request factory
    factory = APIRequestFactory()
    
    # Mock evidence item with a real file path (itself) so open() succeeds
    class MockEvidence:
        def __init__(self):
            self._id = "test_evidence_id"
            self.file_name = "test_device.img"
            self.file_path = __file__
            self.case_id = "test_case_id"
            self.file_size = 1024
            self.hash_sha256 = "12345"
            
    mock_ev = MockEvidence()
    
    from unittest.mock import patch
    
    with patch.object(Evidence, 'get_by_id', return_value=mock_ev):
        # Create request
        request = factory.post('/api/evidence/test_evidence_id/recover-and-analyze/', format='json')
        
        # Authenticate user
        user = MockUser(role='admin')
        request.user = user
        force_authenticate(request, user=user)
        
        # Instantiate view set and call action
        view = EvidenceViewSet()
        view.action = 'recover_and_analyze'
        
        # Mock _check_evidence_access to return True
        with patch.object(view, '_check_evidence_access', return_value=True):
            # Mock the sub-methods in windows_recovery/metadata_recovery/file_carver/etc.
            with patch('forensic_engine.windows_recovery.scan_recycle_bin', return_value=[]), \
                 patch('forensic_engine.windows_recovery.recover_files_from_recycle_bin', return_value=[]), \
                 patch('forensic_api.tsk_wrapper.get_partitions', return_value={'success': True}), \
                 patch('forensic_api.tsk_wrapper.get_timeline', return_value={'success': True}), \
                 patch('forensic_engine.file_carver.FileCarver.carve_disk_image', return_value=[]), \
                 patch('forensic_engine.file_carver.FileCarver.extract_carved_bytes', return_value=[]), \
                 patch('forensic_engine.metadata_recovery.DiskImageAnalyzer.full_analysis', return_value={'recovered_files': [], 'timestamps': []}), \
                 patch('analysis.assistant.ForensicAIAssistant.generate_report', return_value={'report': 'AI investigation completed successfully'}), \
                 patch('cases.coc_models.ChainOfCustody.create', return_value=None), \
                 patch('cases.coc_models.TimelineEvent.create', return_value=None), \
                 patch('evidence.views.EvidenceViewSet._get_real_file_metadata', return_value={'created_date': '2026-06-24', 'modified_date': '2026-06-24'}), \
                 patch('mongo_connection.MONGO_AVAILABLE', False):
                
                response = view.recover_and_analyze(request, pk="test_evidence_id")
                
                # Assertions
                assert response is not None
                assert isinstance(response, StreamingHttpResponse)
                assert response.status_code == 200
                assert response['Content-Type'] == 'text/event-stream'
                
                # Consume stream
                content = b"".join(response.streaming_content).decode('utf-8')
                print("RAW CONTENT:", content)
                lines = content.strip().split('\n\n')
                
                # Verify we get the expected SSE events
                assert len(lines) > 0
                events = []
                for line in lines:
                    if line.strip().startswith('data: '):
                        data_str = line.strip()[6:]
                        events.append(json.loads(data_str))
                
                print("PARSED EVENTS:", events)
                
                # Assert at least one processing and one completed event
                assert any(e['status'] == 'processing' for e in events), "No processing events found!"
                assert any(e['status'] == 'completed' for e in events), "No completed event found!"
                
                # Check completed event content
                completed_event = next(e for e in events if e['status'] == 'completed')
                assert completed_event['recovered_files'] is not None
                assert len(completed_event['recovered_files']) > 0
                assert completed_event['recovered_files'][0]['file_name'] == "test_device.img"


def test_restore_files():
    factory = APIRequestFactory()
    
    class MockEvidence:
        def __init__(self):
            self._id = "test_evidence_id"
            self.file_name = "test_device.img"
            self.file_path = __file__
            self.case_id = "test_case_id"
            self.file_size = 1024
            self.hash_sha256 = "12345"
            
    mock_ev = MockEvidence()
    
    from unittest.mock import patch
    
    with patch.object(Evidence, 'get_by_id', return_value=mock_ev):
        payload = {
            'files': [
                {
                    'file_name': 'restored_test.txt',
                    'original_location': __file__
                }
            ],
            'destination': 'download_local'
        }
        request = factory.post('/api/evidence/test_evidence_id/restore-files/', payload, format='json')
        # Manually set request.data and request.user to emulate Django REST Framework Request parsing
        request.data = payload
        user = MockUser(role='admin')
        request.user = user
        force_authenticate(request, user=user)
        
        view = EvidenceViewSet()
        view.action = 'restore_files'
        
        with patch.object(view, '_check_evidence_access', return_value=True):
            with patch('cases.coc_models.ChainOfCustody.create', return_value=None), \
                 patch('cases.coc_models.TimelineEvent.create', return_value=None):
                
                response = view.restore_files(request, pk="test_evidence_id")
                
                assert response is not None
                assert response.status_code == 200
                assert response.data['success'] is True
                assert response.data['restored_count'] == 1


