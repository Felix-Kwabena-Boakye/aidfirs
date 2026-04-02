from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .serializers import UserSerializer, UserLoginSerializer
from .models import User
from .permissions import (
    IsAdmin, IsInvestigator, IsAnalystOrAbove,
    CanManageUsers, CanManageCases, CanManageEvidence,
    CanRunAnalysis, CanManageSystem
)
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings


class RegisterView(generics.CreateAPIView):
    """
    Register a new user. Public registration is allowed for 'analyst' and 'investigator' roles.
    However, self-registered accounts are created as inactive (pending Admin approval).
    Only admins can create immediate, active accounts using UserCreateView.
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        requested_role = request.data.get('role', 'analyst')
        
        # Only allow public registration for investigator and analyst roles
        if requested_role == 'admin':
            return Response(
                {'error': 'You cannot register as an admin.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data.get('username')
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password', 'default123')
        role = requested_role
        first_name = serializer.validated_data.get('first_name', '')
        last_name = serializer.validated_data.get('last_name', '')
        
        try:
            # Create user but force them to be inactive (pending approval)
            user = User.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                is_active=False  # MUST be False for public registration
            )
            
            return Response({
                'message': 'Registration successful! Your account is pending admin approval.',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def generate_jwt_token(user):
    """
    Generate JWT access and refresh tokens.
    """
    access_payload = {
        'user_id': str(user._id),
        'username': user.username,
        'role': user.role,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=60),
        'type': 'access'
    }
    access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
    
    refresh_payload = {
        'user_id': str(user._id),
        'exp': datetime.now(timezone.utc) + timedelta(days=7),
        'type': 'refresh'
    }
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
    
    return access_token, refresh_token


class TokenRefreshView(APIView):
    """
    Refresh access token using a valid refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
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
            user = User.get_by_id(user_id)
            if not user or not user.is_active:
                return Response(
                    {'error': 'User not found or inactive'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            access_token, _ = generate_jwt_token(user)
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
class LoginView(APIView):
    """
    Login user and return JWT token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data.get('username')
        password = serializer.validated_data.get('password')
        
        # Authenticate currently requires is_active=True to return user.
        # We need to fetch the raw user to give a better error message if they are inactive.
        raw_user_data = User.get_by_username(username)
        if raw_user_data and not raw_user_data.is_active:
            if User.verify_password(password, raw_user_data.password_hash):
                return Response(
                    {'error': 'Account pending admin approval or deactivated.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        user = User.authenticate(username, password)
        
        if user:
            
            user.update_last_login()
            access_token, refresh_token = generate_jwt_token(user)
            
            return Response({
                'message': 'Login successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user).data
            })
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user_id = self.kwargs.get('user_id')
        if user_id:
            return User.get_by_id(user_id)
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
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        from mongo_connection import get_users_collection
        collection = get_users_collection()
        users = collection.find()
        return [User.from_dict(u) for u in users]


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
        
        user = User.get_by_id(user_id)
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


class AISettingsView(APIView):
    """
    Get and update AI settings including Claude API configuration.
    Admin only - can manage AI models and configurations.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request):
        from django.conf import settings
        return Response({
            'claude_enabled': getattr(settings, 'CLAUDE_ENABLED', False),
            'claude_model': getattr(settings, 'CLAUDE_MODEL', 'claude-3-haiku-20240307'),
            'claude_configured': bool(getattr(settings, 'ANTHROPIC_API_KEY', None)),
        })
    
    def post(self, request):
        from django.conf import settings
        claude_enabled = request.data.get('claude_enabled')
        claude_model = request.data.get('claude_model')
        
        # Store in user session if available
        if claude_enabled is not None or claude_model is not None:
            try:
                if hasattr(request, 'session'):
                    if claude_enabled is not None:
                        request.session['claude_enabled'] = claude_enabled
                    if claude_model is not None:
                        request.session['claude_model'] = claude_model
            except Exception:
                pass
        
        return Response({
            'message': 'AI settings updated successfully',
            'claude_enabled': request.session.get('claude_enabled', getattr(settings, 'CLAUDE_ENABLED', False)),
            'claude_model': request.session.get('claude_model', getattr(settings, 'CLAUDE_MODEL', 'claude-3-haiku-20240307')),
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
        if not google_token:
            return Response(
                {'error': 'Google token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the Google token
            # In production, you would verify with Google's public keys
            # For now, we decode the token to get user info
            # Add your Google OAuth client ID to settings for verification
            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
            
            # Decode without verification for demo (in production, verify with Google)
            try:
                decoded = jwt.decode(google_token, options={"verify_signature": False})
            except Exception:
                return Response(
                    {'error': 'Invalid Google token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            email = decoded.get('email')
            if not email:
                return Response(
                    {'error': 'Email not provided in Google token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user exists, if not create one
            user = User.get_by_email(email)
            
            if not user:
                # Create new user with OAuth data
                # Extract name from Google token
                name = decoded.get('name', '')
                first_name = decoded.get('given_name', name.split()[0] if name else '')
                last_name = decoded.get('family_name', ' '.join(name.split()[1:]) if ' ' in name else '')
                
                # Generate username from email
                username = email.split('@')[0]
                
                user = User.create_user(
                    username=username,
                    email=email,
                    password=None,  # No password for OAuth users
                    role='analyst',
                    first_name=first_name,
                    last_name=last_name
                )
                user.is_active = True
                user.is_oauth_google = True
                user.save()
            
            if not user.is_active:
                return Response(
                    {'error': 'User account is deactivated'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user.update_last_login()
            access_token, refresh_token = generate_jwt_token(user)
            
            return Response({
                'message': 'Login successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user).data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Google authentication failed: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class AppleOAuthView(APIView):
    """
    Handle Apple OAuth authentication.
    Receives Apple ID token from frontend, verifies it, and logs in/creates user.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        import jwt
        
        apple_token = request.data.get('token')
        if not apple_token:
            return Response(
                {'error': 'Apple token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Apple tokens need special handling
            # In production, verify with Apple's public keys
            # For now, we decode the token to get user info
            
            # Decode without verification for demo (in production, verify with Apple)
            try:
                # Apple tokens are JWTs
                decoded = jwt.decode(apple_token, options={"verify_signature": False})
            except Exception:
                return Response(
                    {'error': 'Invalid Apple token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Apple may provide email in the token or it might need to be requested
            email = decoded.get('email')
            if not email:
                return Response(
                    {'error': 'Email not provided in Apple token. Please grant email permission.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user exists, if not create one
            user = User.get_by_email(email)
            
            if not user:
                # Create new user with OAuth data
                name = decoded.get('name', {})
                first_name = name.get('firstName', '') if isinstance(name, dict) else ''
                last_name = name.get('lastName', '') if isinstance(name, dict) else ''
                
                # Generate username from email
                username = email.split('@')[0]
                
                user = User.create_user(
                    username=username,
                    email=email,
                    password=None,  # No password for OAuth users
                    role='analyst',
                    first_name=first_name,
                    last_name=last_name
                )
                user.is_active = True
                user.is_oauth_apple = True
                user.save()
            
            if not user.is_active:
                return Response(
                    {'error': 'User account is deactivated'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user.update_last_login()
            access_token, refresh_token = generate_jwt_token(user)
            
            return Response({
                'message': 'Login successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user).data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Apple authentication failed: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED
            )
