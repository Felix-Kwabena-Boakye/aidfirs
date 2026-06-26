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

from cases.views import CaseViewSet
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.request import Request


class MockUser:
    def __init__(self, _id='test_user_id', username='investigator_bob', role='investigator', is_authenticated=True):
        self._id = _id
        self.username = username
        self.role = role
        self.is_authenticated = is_authenticated


def test_global_search_success():
    # 1. Setup Request Factory
    factory = APIRequestFactory()
    request = factory.get('/api/cases/search/?q=NTFS', format='json')
    
    user = MockUser(role='investigator')
    request.user = user
    force_authenticate(request, user=user)

    # 2. Setup mock data
    class MockCase:
        def __init__(self, _id, case_number, title, description, investigator_id, assigned_to=None):
            self._id = _id
            self.case_number = case_number
            self.title = title
            self.description = description
            self.investigator_id = investigator_id
            self.assigned_to = assigned_to or []
            self.tags = ["NTFS", "recovered"]
        
        def to_dict(self):
            return {
                "_id": str(self._id),
                "case_number": self.case_number,
                "title": self.title,
                "description": self.description,
                "investigator_id": str(self.investigator_id),
                "status": "open",
                "priority": "medium",
                "case_type": "",
                "created_at": "2026-06-25T00:00:00Z",
                "updated_at": "2026-06-25T00:00:00Z",
                "closed_at": None,
                "evidence_ids": [],
                "tags": self.tags,
                "assigned_to": self.assigned_to
            }

    class MockEvidence:
        def __init__(self, _id, case_id, file_name, file_path, description):
            self._id = _id
            self.case_id = case_id
            self.evidence_type = "disk_image"
            self.file_name = file_name
            self.file_path = file_path
            self.description = description
            self.file_size = 1000
            self.hash_md5 = "md5hash123"
            self.hash_sha1 = "sha1hash123"
            self.hash_sha256 = "sha256hash123"
            self.status = "collected"
            self.collected_at = "2026-06-25T00:00:00Z"
            self.analyzed_at = None
            self.tags = ["USB", "NTFS"]
            
        def to_dict(self):
            return {
                "_id": str(self._id),
                "case_id": str(self.case_id),
                "evidence_type": self.evidence_type,
                "file_name": self.file_name,
                "file_path": self.file_path,
                "file_size": self.file_size,
                "hash_md5": self.hash_md5,
                "hash_sha1": self.hash_sha1,
                "hash_sha256": self.hash_sha256,
                "description": self.description,
                "status": self.status,
                "collected_at": self.collected_at,
                "analyzed_at": self.analyzed_at,
                "tags": self.tags
            }

    class MockAnalysisResult:
        def __init__(self, _id, case_id, evidence_id, analysis_type, findings):
            self._id = _id
            self.case_id = case_id
            self.evidence_id = evidence_id
            self.analysis_type = analysis_type
            self.findings = findings
            self.severity = "medium"
            self.status = "completed"
            self.analyzed_by = "investigator_bob"
            self.analyzed_at = "2026-06-25T00:00:00Z"
            self.completed_at = "2026-06-25T00:00:00Z"
            self.indicators = [{"type": "file", "value": "malware.exe"}]
            self.summaries = ["Found carved NTFS elements"]
            self.recommendations = ["Analyze logs"]
            self.metadata = {}
            
        def to_dict(self):
            return {
                "_id": str(self._id),
                "case_id": str(self.case_id),
                "evidence_id": str(self.evidence_id),
                "analysis_type": self.analysis_type,
                "findings": self.findings,
                "severity": self.severity,
                "status": self.status,
                "analyzed_by": self.analyzed_by,
                "analyzed_at": self.analyzed_at,
                "completed_at": self.completed_at,
                "indicators": self.indicators,
                "summaries": self.summaries,
                "recommendations": self.recommendations,
                "metadata": self.metadata
            }

    case1 = MockCase(_id="case_1_id", case_number="CASE-001", title="USBDrive Search", description="Investigating NTFS filesystem anomalies", investigator_id="test_user_id")
    case2 = MockCase(_id="case_2_id", case_number="CASE-002", title="Unassigned Case", description="No NTFS matching", investigator_id="other_user_id")
    
    evidence1 = MockEvidence(_id="ev_1_id", case_id="case_1_id", file_name="usb_carve.img", file_path="D:\\usb_carve.img", description="NTFS partitioned usb image")
    evidence2 = MockEvidence(_id="ev_2_id", case_id="case_2_id", file_name="secret.jpg", file_path="C:\\secret.jpg", description="Secret file")
    
    analysis1 = MockAnalysisResult(_id="ar_1_id", case_id="case_1_id", evidence_id="ev_1_id", analysis_type="disk", findings={"summary": "NTFS directory index recovery"})
    analysis2 = MockAnalysisResult(_id="ar_2_id", case_id="case_2_id", evidence_id="ev_2_id", analysis_type="file", findings={"summary": "Unrelated analysis"})

    # 3. Patch Case, Evidence, and AnalysisResult methods
    with patch('cases.models.Case.get_all', return_value=[case1, case2]), \
         patch('evidence.models.Evidence.get_all', return_value=[evidence1, evidence2]), \
         patch('analysis.models.AnalysisResult.get_all', return_value=[analysis1, analysis2]):
         
        view = CaseViewSet()
        view.action = 'search'
        request = Request(request)
        
        response = view.search(request)
        
        assert response.status_code == 200
        data = response.data
        
        # Verify filtering restricts to case1's related items (since investigator user is only assigned/investigator on case1)
        assert len(data["cases"]) == 1
        assert data["cases"][0]["case_number"] == "CASE-001"
        
        assert len(data["evidence"]) == 1
        assert data["evidence"][0]["file_name"] == "usb_carve.img"
        
        assert len(data["analysis_results"]) == 1
        assert data["analysis_results"][0]["analysis_type"] == "disk"


def test_global_search_admin_sees_all():
    # Admin role should bypass assignments and search all cases
    factory = APIRequestFactory()
    request = factory.get('/api/cases/search/?q=NTFS', format='json')
    
    user = MockUser(role='admin', _id='admin_id')
    request.user = user
    force_authenticate(request, user=user)
    
    # Mock cases
    class MockCase:
        def __init__(self, _id, case_number, title, investigator_id):
            self._id = _id
            self.case_number = case_number
            self.title = title
            self.description = "NTFS case"
            self.investigator_id = investigator_id
            self.tags = []
            
        def to_dict(self):
            return {
                "_id": str(self._id),
                "case_number": self.case_number,
                "title": self.title,
                "description": self.description,
                "investigator_id": str(self.investigator_id),
                "status": "open",
                "priority": "medium",
                "case_type": "",
                "created_at": "2026-06-25T00:00:00Z",
                "updated_at": "2026-06-25T00:00:00Z",
                "closed_at": None,
                "evidence_ids": [],
                "tags": []
            }
            
    case1 = MockCase(_id="case_1_id", case_number="CASE-001", title="Case 1", investigator_id="other_user_1")
    case2 = MockCase(_id="case_2_id", case_number="CASE-002", title="Case 2", investigator_id="other_user_2")
    
    with patch('cases.models.Case.get_all', return_value=[case1, case2]), \
         patch('evidence.models.Evidence.get_all', return_value=[]), \
         patch('analysis.models.AnalysisResult.get_all', return_value=[]):
         
        view = CaseViewSet()
        view.action = 'search'
        request = Request(request)
        
        response = view.search(request)
        
        assert response.status_code == 200
        data = response.data
        
        # Admin should see both cases since query "NTFS" matches description of both
        assert len(data["cases"]) == 2
