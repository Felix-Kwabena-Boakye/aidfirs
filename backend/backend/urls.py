from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({"message": "AI Digital Forensics API is running"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_root),
    path('api/accounts/', include('accounts.urls')),
    path('api/cases/', include('cases.urls')),
    path('api/evidence/', include('evidence.urls')),
    path('api/analysis/', include('analysis.urls')),
    path('api/devices/', include('devices.urls')),
]
