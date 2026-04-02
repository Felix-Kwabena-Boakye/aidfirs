from django.urls import path
from .views import (
    RegisterView, LoginView, UserProfileView, UserListView,
    AISettingsView, UserCreateView, UserActivateDeactivateView, CurrentUserView,
    AuditLogView, GoogleOAuthView, AppleOAuthView, TokenRefreshView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('oauth/google/', GoogleOAuthView.as_view(), name='google_oauth'),
    path('oauth/apple/', AppleOAuthView.as_view(), name='apple_oauth'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/<str:user_id>/', UserProfileView.as_view(), name='user_profile_detail'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('users/<str:user_id>/activate/', UserActivateDeactivateView.as_view(), name='user_activate'),
    path('users/<str:user_id>/deactivate/', UserActivateDeactivateView.as_view(), name='user_deactivate'),
    path('ai-settings/', AISettingsView.as_view(), name='ai_settings'),
    path('audit-logs/', AuditLogView.as_view(), name='audit_logs'),
]
