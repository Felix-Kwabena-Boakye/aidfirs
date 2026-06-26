import os
import sys
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from accounts.views import GoogleOAuthView
from accounts.models import User

def test_google_oauth_mock_bypass():
    factory = APIRequestFactory()
    view = GoogleOAuthView.as_view()
    
    # Test with mock code
    request = factory.post('/api/accounts/oauth/google/', {'code': 'mock_code_for_testing'}, format='json')
    response = view(request)
    
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert response.data['user']['username'] == 'soc_analyst'
    assert response.data['user']['email'] == 'soc_analyst@aidfirs.local'

def test_google_oauth_missing_params():
    factory = APIRequestFactory()
    view = GoogleOAuthView.as_view()
    
    # Test with missing code and token
    request = factory.post('/api/accounts/oauth/google/', {}, format='json')
    response = view(request)
    
    assert response.status_code == 400
    assert 'error' in response.data
