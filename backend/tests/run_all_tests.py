"""
Run All Tests
Executes all test suites for the AI Digital Forensics System
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_model_tests():
    """Run MongoDB model tests."""
    print("\n" + "=" * 60)
    print("STEP 1: Running Model Tests")
    print("=" * 60)
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    import django
    django.setup()
    
    from tests.test_models import run_all_tests as run_models
    return run_models()

def run_ai_engine_tests():
    """Run AI engine tests."""
    print("\n" + "=" * 60)
    print("STEP 2: Running AI Engine Tests")
    print("=" * 60)
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    import django
    django.setup()
    
    from tests.test_ai_engine import run_all_tests as run_ai
    return run_ai()

def run_api_tests():
    """Run API tests (requires server to be running)."""
    print("\n" + "=" * 60)
    print("STEP 3: Running API Tests")
    print("=" * 60)
    print("Note: API tests require the Django server to be running")
    print("Start server with: python start_server.py")
    print("-" * 60)
    
    from tests.test_api import run_all_tests as run_api
    return run_api()

def main():
    """Run all tests and display summary."""
    print("\n" + "=" * 60)
    print("AI DIGITAL FORENSICS SYSTEM - TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Run model tests
    results["Model Tests"] = run_model_tests()
    
    # Run AI engine tests
    results["AI Engine Tests"] = run_ai_engine_tests()
    
    # Run API tests (may be skipped if server not running)
    results["API Tests"] = run_api_tests()
    
    # Print final summary
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED/SKIPPED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nOverall: {total_passed}/{total_tests} test suites passed")
    print("=" * 60)
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
