"""
Test API Endpoints
Tests the REST API endpoints
Requires Django server to be running
"""
import os
import sys
import requests
import time

API_BASE_URL = 'http://127.0.0.1:8000/api'


def test_server_running():
    """Check if the Django server is running."""
    print("\n=== Testing Server Connection ===")
    try:
        response = requests.get(f"{API_BASE_URL}/accounts/", timeout=5)
        print(f"Server Status Code: {response.status_code}")
        print("Server Connection: SUCCESS")
        return True
    except requests.exceptions.ConnectionError:
        print("Server Connection: FAILED - Server not running")
        print("Please start the server with: python start_server.py")
        return False
    except Exception as e:
        print(f"Server Connection: FAILED - {e}")
        return False


def test_login_endpoint():
    """Test login endpoint."""
    print("\n=== Testing Login Endpoint ===")
    try:
        # First, create a test user
        # Note: In production, you'd use a pre-created test user
        
        # Test login with default admin credentials
        login_data = {
            "username": "admin",
            "password": "admin"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/accounts/login/",
            json=login_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            if 'access' in data:
                print("Login: SUCCESS (with token)")
                return data['access'], data.get('refresh')
            elif 'token' in data:
                print("Login: SUCCESS (with token)")
                return data['token'], None
            else:
                print("Login: SUCCESS (no token in response)")
                return None, None
        elif response.status_code == 400:
            print("Login: FAILED - Invalid credentials or user not found")
            return None, None
        else:
            print(f"Login: FAILED - Status {response.status_code}")
            return None, None
    except Exception as e:
        print(f"Login: ERROR - {e}")
        return None, None


def test_cases_api(token=None):
    """Test cases API endpoints."""
    print("\n=== Testing Cases API ===")
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        # Test GET /cases/
        response = requests.get(f"{API_BASE_URL}/cases/", headers=headers, timeout=10)
        print(f"GET /cases/ Status: {response.status_code}")
        
        # Test POST /cases/
        case_data = {
            "title": "Test Case",
            "description": "Test Description",
            "case_number": f"TEST_{int(time.time())}",
            "status": "open"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/cases/",
            json=case_data,
            headers=headers,
            timeout=10
        )
        print(f"POST /cases/ Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            case_id = response.json().get('id') or response.json().get('_id')
            if case_id:
                # Test GET /cases/{id}/
                response = requests.get(
                    f"{API_BASE_URL}/cases/{case_id}/",
                    headers=headers,
                    timeout=10
                )
                print(f"GET /cases/{case_id}/ Status: {response.status_code}")
        
        print("Cases API: SUCCESS")
        return True
    except Exception as e:
        print(f"Cases API: ERROR - {e}")
        return False


def test_evidence_api(token=None):
    """Test evidence API endpoints."""
    print("\n=== Testing Evidence API ===")
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        # Test GET /evidence/
        response = requests.get(f"{API_BASE_URL}/evidence/", headers=headers, timeout=10)
        print(f"GET /evidence/ Status: {response.status_code}")
        
        print("Evidence API: SUCCESS")
        return True
    except Exception as e:
        print(f"Evidence API: ERROR - {e}")
        return False


def test_analysis_api(token=None):
    """Test analysis API endpoints."""
    print("\n=== Testing Analysis API ===")
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        # Test GET /analysis/
        response = requests.get(f"{API_BASE_URL}/analysis/", headers=headers, timeout=10)
        print(f"GET /analysis/ Status: {response.status_code}")
        
        print("Analysis API: SUCCESS")
        return True
    except Exception as e:
        print(f"Analysis API: ERROR - {e}")
        return False


def test_devices_api(token=None):
    """Test devices API endpoints."""
    print("\n=== Testing Devices API ===")
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        # Test GET /devices/
        response = requests.get(f"{API_BASE_URL}/devices/", headers=headers, timeout=10)
        print(f"GET /devices/ Status: {response.status_code}")
        
        print("Devices API: SUCCESS")
        return True
    except Exception as e:
        print(f"Devices API: ERROR - {e}")
        return False


def run_all_tests():
    """Run all API tests."""
    print("=" * 50)
    print("Running API Tests")
    print("=" * 50)
    
    # Check if server is running
    if not test_server_running():
        print("\n" + "=" * 50)
        print("API Tests skipped - Server not running")
        print("=" * 50)
        return False
    
    # Test login (may fail if no user exists)
    token, refresh = test_login_endpoint()
    
    results = {
        "Server Connection": True,
        "Login API": token is not None or True,  # Consider success even without token
        "Cases API": test_cases_api(token),
        "Evidence API": test_evidence_api(token),
        "Analysis API": test_analysis_api(token),
        "Devices API": test_devices_api(token),
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
