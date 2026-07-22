from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from accounts.views import AgentRegisterView

def api_root(request):
    return JsonResponse({
        "message": "AIDFIRS — AI Digital Forensics API is running",
        "version": "2.0",
        "status": "operational"
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_root),
    path('api/accounts/', include('accounts.urls')),
    path('api/agents/register/', AgentRegisterView.as_view(), name='agent-register'),
    path('api/cases/', include('cases.urls')),
    path('api/evidence/', include('evidence.urls')),
    path('api/analysis/', include('analysis.urls')),
    path('api/devices/', include('devices.urls')),
    path('api/recovery/', include('recovery.urls')),
    path('api/reports/', include('reports.urls')),
]
