"""
Test Role-Based Access Control
Tests the permission system for Admin, Investigator, and Analyst roles
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.permissions import (
    IsAdmin, IsInvestigator, IsAnalystOrAbove,
    CanManageUsers, CanManageCases, CanManageEvidence,
    CanRunAnalysis, CanManageSystem
)
from accounts.models import User


class MockRequest:
    """Mock request object for testing permissions."""
    def __init__(self, user=None, method='GET'):
        self.user = user
        self.method = method
        self.data = {}


class MockUser:
    """Mock user object for testing."""
    def __init__(self, role='analyst', is_authenticated=True):
        self.role = role
        self.is_authenticated = is_authenticated
        self._id = "test_user_id"


def test_is_admin_permission():
    """Test IsAdmin permission."""
    print("\n=== Testing IsAdmin Permission ===")
    try:
        permission = IsAdmin()
        
        # Test with admin user
        admin_user = MockUser(role='admin')
        request = MockRequest(user=admin_user)
        assert permission.has_permission(request, None) == True
        print("Admin user: GRANTED")
        
        # Test with investigator
        investigator_user = MockUser(role='investigator')
        request = MockRequest(user=investigator_user)
        assert permission.has_permission(request, None) == False
        print("Investigator user: DENIED")
        
        # Test with analyst
        analyst_user = MockUser(role='analyst')
        request = MockRequest(user=analyst_user)
        assert permission.has_permission(request, None) == False
        print("Analyst user: DENIED")
        
        # Test with unauthenticated user
        request = MockRequest(user=None)
        assert permission.has_permission(request, None) == False
        print("Unauthenticated user: DENIED")
        
        print("IsAdmin Permission: SUCCESS")
        return True
    except Exception as e:
        print(f"IsAdmin Permission: FAILED - {e}")
        return False


def test_is_investigator_permission():
    """Test IsInvestigator permission."""
    print("\n=== Testing IsInvestigator Permission ===")
    try:
        permission = IsInvestigator()
        
        # Test with admin user
        admin_user = MockUser(role='admin')
        request = MockRequest(user=admin_user)
        assert permission.has_permission(request, None) == True
        print("Admin user: GRANTED")
        
        # Test with investigator
        investigator_user = MockUser(role='investigator')
        request = MockRequest(user=investigator_user)
        assert permission.has_permission(request, None) == True
        print("Investigator user: GRANTED")
        
        # Test with analyst
        analyst_user = MockUser(role='analyst')
        request = MockRequest(user=analyst_user)
        assert permission.has_permission(request, None) == False
        print("Analyst user: DENIED")
        
        print("IsInvestigator Permission: SUCCESS")
        return True
    except Exception as e:
        print(f"IsInvestigator Permission: FAILED - {e}")
        return False


def test_is_analyst_or_above_permission():
    """Test IsAnalystOrAbove permission."""
    print("\n=== Testing IsAnalystOrAbove Permission ===")
    try:
        permission = IsAnalystOrAbove()
        
        # All authenticated users should have access
        for role in ['admin', 'investigator', 'analyst']:
            user = MockUser(role=role)
            request = MockRequest(user=user)
            assert permission.has_permission(request, None) == True
            print(f"{role} user: GRANTED")
        
        # Unauthenticated should be denied
        request = MockRequest(user=None)
        assert permission.has_permission(request, None) == False
        print("Unauthenticated user: DENIED")
        
        print("IsAnalystOrAbove Permission: SUCCESS")
        return True
    except Exception as e:
        print(f"IsAnalystOrAbove Permission: FAILED - {e}")
        return False


def test_can_manage_cases_permission():
    """Test CanManageCases permission."""
    print("\n=== Testing CanManageCases Permission ===")
    try:
        permission = CanManageCases()
        
        # Admin can do everything
        admin_user = MockUser(role='admin')
        request = MockRequest(user=admin_user, method='POST')
        assert permission.has_permission(request, None) == True
        print("Admin POST: GRANTED")
        
        # Investigator can create cases
        investigator_user = MockUser(role='investigator')
        request = MockRequest(user=investigator_user, method='POST')
        assert permission.has_permission(request, None) == True
        print("Investigator POST: GRANTED")
        
        # Analyst can only view (GET)
        analyst_user = MockUser(role='analyst')
        request = MockRequest(user=analyst_user, method='GET')
        assert permission.has_permission(request, None) == True
        print("Analyst GET: GRANTED")
        
        # Analyst cannot create
        request = MockRequest(user=analyst_user, method='POST')
        assert permission.has_permission(request, None) == False
        print("Analyst POST: DENIED")
        
        print("CanManageCases Permission: SUCCESS")
        return True
    except Exception as e:
        print(f"CanManageCases Permission: FAILED - {e}")
        return False


def test_can_manage_users_permission():
    """Test CanManageUsers permission."""
    print("\n=== Testing CanManageUsers Permission ===")
    try:
        permission = CanManageUsers()
        
        # Only admin can create users
        admin_user = MockUser(role='admin')
        request = MockRequest(user=admin_user, method='POST')
        assert permission.has_permission(request, None) == True
        print("Admin POST: GRANTED")
        
        # Investigator cannot create users
        investigator_user = MockUser(role='investigator')
        request = MockRequest(user=investigator_user, method='POST')
        assert permission.has_permission(request, None) == False
        print("Investigator POST: DENIED")
        
        # Analyst cannot create users
        analyst_user = MockUser(role='analyst')
        request = MockRequest(user=analyst_user, method='POST')
        assert permission.has_permission(request, None) == False
        print("Analyst POST: DENIED")
        
        print("CanManageUsers Permission: SUCCESS")
        return True
    except Exception as e:
        print(f"CanManageUsers Permission: FAILED - {e}")
        return False


def test_can_manage_system_permission():
    """Test CanManageSystem permission."""
    print("\n=== Testing CanManageSystem Permission ===")
    try:
        permission = CanManageSystem()
        
        # Only admin can manage system
        admin_user = MockUser(role='admin')
        request = MockRequest(user=admin_user)
        assert permission.has_permission(request, None) == True
        print("Admin: GRANTED")
        
        # Others cannot
        for role in ['investigator', 'analyst']:
            user = MockUser(role=role)
            request = MockRequest(user=user)
            assert permission.has_permission(request, None) == False
            print(f"{role}: DENIED")
        
        print("CanManageSystem Permission: SUCCESS")
        return True
    except Exception as e:
        print(f"CanManageSystem Permission: FAILED - {e}")
        return False


def test_role_definitions():
    """Test that role definitions match requirements."""
    print("\n=== Testing Role Definitions ===")
    try:
        # Check the ROLE_CHOICES in User model
        roles = [choice[0] for choice in User.ROLE_CHOICES]
        
        assert 'admin' in roles, "Admin role missing"
        assert 'investigator' in roles, "Investigator role missing"
        assert 'analyst' in roles, "Analyst role missing"
        
        print(f"Available roles: {roles}")
        
        # Test creating users with different roles
        test_username = f"role_test_user"
        
        # Create admin user
        admin = User.create_user(
            username=f"{test_username}_admin",
            email=f"{test_username}_admin@test.com",
            password="test123",
            role="admin"
        )
        assert admin.role == "admin"
        print(f"Admin user created: {admin.username}")
        
        # Create investigator user
        investigator = User.create_user(
            username=f"{test_username}_investigator",
            email=f"{test_username}_investigator@test.com",
            password="test123",
            role="investigator"
        )
        assert investigator.role == "investigator"
        print(f"Investigator user created: {investigator.username}")
        
        # Create analyst user
        analyst = User.create_user(
            username=f"{test_username}_analyst",
            email=f"{test_username}_analyst@test.com",
            password="test123",
            role="analyst"
        )
        assert analyst.role == "analyst"
        print(f"Analyst user created: {analyst.username}")
        
        # Clean up
        from mongo_connection import get_users_collection
        collection = get_users_collection()
        collection.delete_many({"username": {"$regex": f"^{test_username}"}})
        
        print("Role Definitions: SUCCESS")
        return True
    except Exception as e:
        print(f"Role Definitions: FAILED - {e}")
        return False


def run_all_tests():
    """Run all permission tests."""
    print("=" * 50)
    print("Running Role-Based Access Control Tests")
    print("=" * 50)
    
    results = {
        "IsAdmin Permission": test_is_admin_permission(),
        "IsInvestigator Permission": test_is_investigator_permission(),
        "IsAnalystOrAbove Permission": test_is_analyst_or_above_permission(),
        "CanManageCases Permission": test_can_manage_cases_permission(),
        "CanManageUsers Permission": test_can_manage_users_permission(),
        "CanManageSystem Permission": test_can_manage_system_permission(),
        "Role Definitions": test_role_definitions(),
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
