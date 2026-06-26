import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from evidence.views import EvidenceViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

class MockUser:
    def __init__(self):
        self.role = 'admin'
        self.is_authenticated = True
        self._id = 'admin_user_id'
        self.username = 'admin_user'

def test_stream():
    factory = APIRequestFactory()
    request = factory.post('/api/evidence/6a309b5fc65b13025bcb1865/tsk_recover_deleted/', {'offset': '0'}, format='json')
    user = MockUser()
    request.user = user
    force_authenticate(request, user=user)
    
    view = EvidenceViewSet()
    view.action = 'tsk_recover_deleted'
    
    # Call the view directly
    response = view.tsk_recover_deleted(request, pk="6a309b5fc65b13025bcb1865")
    print("Response Status Code:", response.status_code)
    print("Content Type:", response.headers.get('Content-Type'))
    
    print("\nStreaming Content:")
    for content in response.streaming_content:
        print(content.decode('utf-8'))

if __name__ == '__main__':
    test_stream()
