import os
import django
import sys
from bson import ObjectId

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from evidence.models import Evidence
from evidence.serializers import EvidenceSerializer

def test_serialization():
    print("Testing Evidence serialization with file_path=None...")
    try:
        e = Evidence(
            case_id="123",
            evidence_type="file",
            file_name="test.txt",
            file_path=None,
            collector_id="user1",
            description="desc"
        )
        ser = EvidenceSerializer(e)
        # Accessing .data triggers the serialization process
        data = ser.data
        print("Serializer data success:", data)
    except Exception as ex:
        print(f"Serialization FAILED: {ex}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_serialization()
