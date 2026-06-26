import os
import django
import sys
import json

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from evidence.serializers import EvidenceSerializer
from cases.serializers import CaseSerializer

def test():
    case_data = {
        'case_number': 'AI-FOR-123456',
        'title': 'Forensic Examination: General UDisk',
        'description': 'Comprehensive AI-driven forensic...',
        'priority': 'high',
        'case_type': 'Digital Forensics'
    }
    case_ser = CaseSerializer(data=case_data)
    if not case_ser.is_valid():
        print("Case validation failed:", case_ser.errors)
    else:
        print("Case valid!")
        
    evidence_data = {
        'case_id': 'dummy_id',
        'evidence_type': 'disk_image',
        'file_name': 'General UDisk_Forensic_Image',
        'file_path': 'D:\\',
        'file_size': 31460590387,
        'description': 'Source Device: General UDisk...',
        'status': 'collected'
    }
    evi_ser = EvidenceSerializer(data=evidence_data)
    if not evi_ser.is_valid():
        print("Evidence validation failed:", evi_ser.errors)
    else:
        print("Evidence valid!")

if __name__ == "__main__":
    test()
