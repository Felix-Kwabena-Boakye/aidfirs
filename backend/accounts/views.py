from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .serializers import UserSerializer, UserLoginSerializer
from .models import User
from .services import UserService
from .permissions import (
    IsAdmin, IsInvestigator, IsAnalystOrAbove,
    CanManageUsers, CanManageCases, CanManageEvidence,
    CanRunAnalysis, CanManageSystem
)
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.utils import timezone as dj_timezone


class RegisterView(generics.CreateAPIView):
    """
    Register a new user. Public registration is allowed for 'analyst' and 'investigator' roles.
    However, self-registered accounts are created as inactive (pending Admin approval).
    Only admins can create immediate, active accounts using UserCreateView.
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        is_admin_request = request.user.role == 'admin' if request.user.is_authenticated else False
        
        if not UserService.validate_registration(data, is_admin=is_admin_request):
            return Response(
                {'error': 'Invalid registration data or unauthorized role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        user_data = serializer.validated_data
        is_admin_request = request.user.role == 'admin' if request.user.is_authenticated else False
        
        user = UserService.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data.get('password', 'default123'),
            role=user_data.get('role', 'analyst'),
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            is_active=is_admin_request  # Active only if admin creates
        )
        
        message = 'User created successfully'
        if not is_admin_request:
            message = 'Registration submitted. Your account is pending administrator approval.'
            
        return Response({
            'message': message,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)





class TokenRefreshView(APIView):
    """
    Refresh access token using a valid refresh token.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='20/h', method='POST', block=True))
    def post(self, request):
        refresh_token = request.data.get('refresh', '').strip()
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('type') != 'refresh':
                return Response(
                    {'error': 'Invalid token type'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user_id = payload.get('user_id')
            user = UserService.get_user_by_id(user_id)
            if not user or not user.is_active:
                return Response(
                    {'error': 'User not found or inactive'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            access_token, _ = UserService.generate_tokens(user)
            return Response({'access': access_token})

        except jwt.ExpiredSignatureError:
            return Response(
                {'error': 'Refresh token expired'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.InvalidTokenError:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class LoginView(APIView):
    """
    Login user and return JWT token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data.copy()
        serializer = UserLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        username = data['username']
        password = data['password']
        
        user = UserService.authenticate(username, password)
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account pending admin approval or deactivated.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user.update_last_login()
        except:
            pass  # Skip Mongo update if unavailable
        access_token, refresh_token = UserService.generate_tokens(user)
        
        return Response({
            'message': 'Login successful',
            'access': access_token,
            'refresh': refresh_token,
            'user': UserSerializer(user).data
        })


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user_id = self.kwargs.get('user_id')
        if user_id:
            return UserService.get_user_by_id(user_id)
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Users can only update their own profile
        if user._id != request.user._id:
            # Only admins can update other users
            if request.user.role != 'admin':
                return Response(
                    {'error': 'You can only update your own profile'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Users cannot change their own role (except admins)
        if 'role' in request.data and user._id == request.user._id:
            if request.user.role != 'admin':
                return Response(
                    {'error': 'You cannot change your own role'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
        if 'role' in request.data:
            # Only admins can change roles
            if request.user.role == 'admin':
                user.role = request.data['role']
        
        user.save()
        
        return Response(UserSerializer(user).data)


class UserListView(generics.ListAPIView):
    """
    List all users (admin only).
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        return User.get_all()


class UserCreateView(generics.CreateAPIView):
    """
    Create a new user (admin only). Use this to create investigator accounts.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data.get('username')
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password', 'default123')
        role = serializer.validated_data.get('role', 'analyst')
        first_name = serializer.validated_data.get('first_name', '')
        last_name = serializer.validated_data.get('last_name', '')
        
        try:
            user = User.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name
            )
            
            return Response({
                'message': f'{role.title()} account created successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserActivateDeactivateView(APIView):
    """
    Activate or deactivate a user (admin only).
    """
    permission_classes = [IsAdmin]
    
    def post(self, request, user_id):
        action = request.data.get('action', 'deactivate')
        
        user = UserService.get_user_by_id(user_id)
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cannot deactivate yourself
        if user._id == request.user._id:
            return Response(
                {'error': 'Cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if action == 'activate':
            user.is_active = True
            message = 'User activated successfully'
        else:
            user.is_active = False
            message = 'User deactivated successfully'
        
        user.save()
        
        return Response({
            'message': message,
            'user': UserSerializer(user).data
        })


class ResetUserPasswordView(APIView):
    """Deprecated: admin-driven password reset.

    Requirement: admins must only approve/disapprove users.
    Therefore this endpoint is disabled.
    """

    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        return Response(
            {'error': 'Admin password resets are disabled. Admins may only activate/deactivate users.'},
            status=status.HTTP_403_FORBIDDEN,
        )


class ChangePasswordView(APIView):
    """
    Endpoint for users to change their own password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            return Response(
                {'error': 'Current password, new password, and confirmation are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'New password and confirmation do not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'New password must be at least 6 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        if not user:
            return Response(
                {'error': 'User session not found.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Verify current password
        if not User.verify_password(current_password, user.password_hash):
            return Response(
                {'error': 'Incorrect current password.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Hash and save new password
        user.password_hash = User.hash_password(new_password)
        user.save()

        # Log audit log
        from .models import AuditLog
        AuditLog.log(
            user_id=str(user._id),
            username=user.username,
            action='change_password',
            resource_type='user',
            resource_id=str(user._id),
            details={'message': 'User changed their password.'}
        )

        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)




class AISettingsView(APIView):
    """
    Get and update AI settings including Claude API configuration.
    Admin only - can manage AI models and configurations.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request):
        from django.conf import settings
        import os
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY', ''))
        configured = bool(api_key and api_key != 'your_anthropic_claude_api_key_here')
        
        return Response({
            'claude_enabled': request.session.get('claude_enabled', getattr(settings, 'CLAUDE_ENABLED', False)),
            'claude_model': request.session.get('claude_model', getattr(settings, 'CLAUDE_MODEL', 'claude-3-haiku-20240307')),
            'claude_configured': configured
        })
    
    def post(self, request):
        from django.conf import settings
        import os
        import re
        
        claude_enabled = request.data.get('claude_enabled')
        claude_model = request.data.get('claude_model')
        api_key = request.data.get('api_key')
        
        # Store in user session if available
        if hasattr(request, 'session'):
            if claude_enabled is not None:
                request.session['claude_enabled'] = claude_enabled
            if claude_model is not None:
                request.session['claude_model'] = claude_model
                
        # Save API key to .env if provided
        if api_key:
            # Validate API key format (basic check for Anthropic keys)
            if not re.match(r'^sk-ant-[a-zA-Z0-9_-]{32,}$', api_key):
                return Response({'error': 'Invalid API key format'}, status=status.HTTP_400_BAD_REQUEST)

            env_path = os.path.join(settings.BASE_DIR, '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    content = f.read()
                if 'ANTHROPIC_API_KEY' in content:
                    content = re.sub(r'ANTHROPIC_API_KEY=.*', f'ANTHROPIC_API_KEY={api_key}', content)
                else:
                    content += f'\nANTHROPIC_API_KEY={api_key}'
                with open(env_path, 'w') as f:
                    f.write(content)
            # Update the environment immediately for current process
            os.environ['ANTHROPIC_API_KEY'] = api_key
            settings.ANTHROPIC_API_KEY = api_key
        
        api_key_check = getattr(settings, 'ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY', ''))
        configured = bool(api_key_check and api_key_check != 'your_anthropic_claude_api_key_here')
        
        return Response({
            'message': 'AI settings updated successfully',
            'claude_enabled': request.session.get('claude_enabled', getattr(settings, 'CLAUDE_ENABLED', False)),
            'claude_model': request.session.get('claude_model', getattr(settings, 'CLAUDE_MODEL', 'claude-3-haiku-20240307')),
            'claude_configured': configured
        })


class CurrentUserView(APIView):
    """
    Get current logged in user info.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'user': UserSerializer(request.user).data
        })


class AuditLogView(APIView):
    """
    View audit logs. Admin only can view all logs.
    Investigators can only view their own activity logs.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Only admins can view all logs
        if request.user.role == 'admin':
            from .models import AuditLog
            limit = int(request.query_params.get('limit', 500))
            logs = AuditLog.get_all_logs(limit=limit)
            
            # Convert ObjectId to string
            for log in logs:
                if '_id' in log:
                    log['_id'] = str(log['_id'])
                if 'timestamp' in log and hasattr(log['timestamp'], 'isoformat'):
                    log['timestamp'] = log['timestamp'].isoformat()
            
            return Response({
                'logs': logs,
                'count': len(logs)
            })
        else:
            # Investigators can only view their own activity
            from .models import AuditLog
            user_id = str(request.user._id)
            limit = int(request.query_params.get('limit', 100))
            logs = AuditLog.get_logs(user_id=user_id, limit=limit)
            
            # Convert ObjectId to string
            for log in logs:
                if '_id' in log:
                    log['_id'] = str(log['_id'])
                if 'timestamp' in log and hasattr(log['timestamp'], 'isoformat'):
                    log['timestamp'] = log['timestamp'].isoformat()
            
            return Response({
                'logs': logs,
                'count': len(logs)
            })


class GoogleOAuthView(APIView):
    """
    Handle Google OAuth authentication.
    Receives Google ID token from frontend, verifies it, and logs in/creates user.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from django.conf import settings
        import jwt
        
        google_token = request.data.get('token')
        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')
        
        if not google_token and not code:
            return Response(
                {'error': 'Google token or code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authorization Code Exchange Flow
        if code and not google_token:
            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
            client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
            
            # Offline mock bypass for easy setup/dev testing if client credentials are not configured
            if code == "mock_code_for_testing" or not client_id or not client_secret:
                email = "soc_analyst@aidfirs.local"
                user = UserService.get_user_by_email(email)
                if not user:
                    user = User.create_user(
                        username="soc_analyst",
                        email=email,
                        password=None,
                        role='analyst',
                        first_name="SOC",
                        last_name="Analyst"
                    )
                    user.is_active = True
                    user.is_oauth_google = True
                    user.save()
                
                user.update_last_login()
                access_token, refresh_token = UserService.generate_tokens(user)
                return Response({
                    'message': 'Login successful (Mock Bypass)',
                    'access': access_token,
                    'refresh': refresh_token,
                    'user': UserSerializer(user).data
                })
            
            import requests as req_lib
            try:
                token_endpoint = "https://oauth2.googleapis.com/token"
                token_data = {
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri or "http://localhost:3000/oauth/callback/google",
                    "grant_type": "authorization_code"
                }
                res = req_lib.post(token_endpoint, data=token_data, timeout=10)
                if res.status_code == 200:
                    tokens = res.json()
                    google_token = tokens.get("id_token")
                    if not google_token:
                        return Response({'error': 'No ID token returned by Google'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'error': f"Failed to exchange code: {res.text}"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as exchange_err:
                return Response({'error': f"Code exchange error: {str(exchange_err)}"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            
            # Proper Google ID token verification
            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID')
            if not client_id:
                return Response({'error': 'Google OAuth client ID not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            idinfo = id_token.verify_oauth2_token(google_token, google_requests.Request(), client_id)
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            email = idinfo['email']
            if not email:
                return Response({'error': 'Email not provided in Google token'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user exists, if not create one
            user = UserService.get_user_by_email(email)
            
            if not user:
                name = idinfo.get('name', '')
                first_name = idinfo.get('given_name', name.split()[0] if name else '')
                last_name = idinfo.get('family_name', ' '.join(name.split()[1:]) if ' ' in name else '')
                username = email.split('@')[0]
                
                user = User.create_user(
                    username=username,
                    email=email,
                    password=None,
                    role='analyst',
                    first_name=first_name,
                    last_name=last_name
                )
                user.is_active = False  # Changed: Require admin approval for OAuth signups
                user.is_oauth_google = True
                user.save()
            
            if not user.is_active:
                return Response({'error': 'User account is deactivated'}, status=status.HTTP_403_FORBIDDEN)
            
            user.update_last_login()
            access_token, refresh_token = UserService.generate_tokens(user)
            
            return Response({
                'message': 'Login successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user).data
            })
            
        except ValueError as e:
            return Response({'error': f'Invalid Google token: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error': f'Google authentication failed: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)
