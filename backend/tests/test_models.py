"""
Test MongoDB Models
Tests the MongoDB connection and data models
"""
import os
import sys
import django

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from mongo_connection import get_users_collection, get_cases_collection, get_evidence_collection, get_analysis_results_collection
from accounts.models import User
from cases.models import Case
from evidence.models import Evidence
from analysis.models import AnalysisResult
from bson import ObjectId
import uuid


def test_mongodb_connection():
    """Test MongoDB connection."""
    print("\n=== Testing MongoDB Connection ===")
    try:
        collection = get_users_collection()
        # Ping the database
        result = collection.database.command('ping')
        print(f"MongoDB Connection: SUCCESS")
        print(f"Database response: {result}")
        return True
    except Exception as e:
        print(f"MongoDB Connection: FAILED")
        print(f"Error: {e}")
        return False


def test_user_model():
    """Test User model."""
    print("\n=== Testing User Model ===")
    try:
        # Create a test user
        test_username = f"testuser_{ObjectId()}"
        user = User.create_user(
            username=test_username,
            email=f"{test_username}@test.com",
            password="testpass123",
            role="analyst"
        )
        print(f"User created: {user.username}")
        
        # Verify user exists
        retrieved_user = User.get_by_username(test_username)
        assert retrieved_user is not None
        assert retrieved_user.username == test_username
        print(f"User retrieval: SUCCESS")
        
        # Clean up
        users_collection = get_users_collection()
        users_collection.delete_one({"_id": user._id})
        print(f"User cleanup: SUCCESS")
        
        return True
    except Exception as e:
        print(f"User Model Test: FAILED")
        print(f"Error: {e}")
        return False


def test_case_model():
    """Test Case model."""
    print("\n=== Testing Case Model ===")
    try:
        test_case = Case.create(
            case_number=f"TEST_{ObjectId()}",
            title="Test Case",
            description="Test Description",
            investigator_id="test_investigator"
        )
        print(f"Case created: {test_case.title}")
        
        # Verify case exists
        retrieved_case = Case.get_by_id(test_case._id)
        assert retrieved_case is not None
        assert retrieved_case.title == "Test Case"
        print(f"Case retrieval: SUCCESS")
        
        # Clean up
        cases_collection = get_cases_collection()
        cases_collection.delete_one({"_id": test_case._id})
        print(f"Case cleanup: SUCCESS")
        
        return True
    except Exception as e:
        print(f"Case Model Test: FAILED")
        print(f"Error: {e}")
        return False


def test_evidence_model():
    """Test Evidence model."""
    print("\n=== Testing Evidence Model ===")
    try:
        # First create a case
        unique_id = str(ObjectId())
        test_case = Case.create(
            case_number=f"EVID_{unique_id}",
            title="Evidence Test Case",
            description="Test",
            investigator_id="test"
        )
        
        # Create evidence with unique file path to get unique hash
        evidence = Evidence.create(
            case_id=str(test_case._id),
            evidence_type="file",
            file_name=f"test_{unique_id}.txt",
            file_path=f"/tmp/test_{unique_id}.txt",
            description="Test Evidence",
            file_size=1024
        )
        print(f"Evidence created: {evidence.file_name}")
        
        # Verify evidence exists
        retrieved_evidence = Evidence.get_by_id(evidence._id)
        assert retrieved_evidence is not None
        print(f"Evidence retrieval: SUCCESS")
        
        # Clean up
        evidence_collection = get_evidence_collection()
        evidence_collection.delete_one({"_id": evidence._id})
        cases_collection = get_cases_collection()
        cases_collection.delete_one({"_id": test_case._id})
        print(f"Evidence cleanup: SUCCESS")
        
        return True
    except Exception as e:
        print(f"Evidence Model Test: FAILED")
        print(f"Error: {e}")
        return False


def test_analysis_result_model():
    """Test AnalysisResult model."""
    print("\n=== Testing Analysis Result Model ===")
    try:
        # First create a case and evidence
        unique_id = str(ObjectId())
        test_case = Case.create(
            case_number=f"ANALYSIS_{unique_id}",
            title="Analysis Test Case",
            description="Test",
            investigator_id="test"
        )
        
        evidence = Evidence.create(
            case_id=str(test_case._id),
            evidence_type="file",
            file_name=f"test_{unique_id}.exe",
            file_path=f"/tmp/test_{unique_id}.exe",
            description="Test Evidence",
            file_size=2048
        )
        
        # Create analysis result
        analysis = AnalysisResult.create(
            case_id=str(test_case._id),
            evidence_id=str(evidence._id),
            analysis_type="static",
            findings={"findings": "test finding"},
            severity="medium"
        )
        print(f"Analysis created: {analysis.analysis_type}")
        
        # Verify analysis exists
        retrieved_analysis = AnalysisResult.get_by_id(analysis._id)
        assert retrieved_analysis is not None
        print(f"Analysis retrieval: SUCCESS")
        
        # Clean up
        analysis_collection = get_analysis_results_collection()
        analysis_collection.delete_one({"_id": analysis._id})
        evidence_collection = get_evidence_collection()
        evidence_collection.delete_one({"_id": evidence._id})
        cases_collection = get_cases_collection()
        cases_collection.delete_one({"_id": test_case._id})
        print(f"Analysis cleanup: SUCCESS")
        
        return True
    except Exception as e:
        print(f"Analysis Result Model Test: FAILED")
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Run all model tests."""
    print("=" * 50)
    print("Running MongoDB Model Tests")
    print("=" * 50)
    
    results = {
        "MongoDB Connection": test_mongodb_connection(),
        "User Model": test_user_model(),
        "Case Model": test_case_model(),
        "Evidence Model": test_evidence_model(),
        "Analysis Result Model": test_analysis_result_model(),
    }
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
