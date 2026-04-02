import jwt
from datetime import datetime, timezone
from django.conf import settings
from rest_framework import authentication, exceptions
from accounts.models import User


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT Authentication class.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request and return a tuple of (user, token).
        """
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None  # No authentication attempted
        
        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            return None
        
        return self.authenticate_token(token)
    
    def authenticate_token(self, token):
        """
        Verify the JWT token and return the user.
        """
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            
            # Check token type
            if payload.get('type') != 'access':
                raise exceptions.AuthenticationFailed('Invalid token type')
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                raise exceptions.AuthenticationFailed('Token has expired')
            
            # Get user from database
            user_id = payload.get('user_id')
            user = User.get_by_id(user_id)
            
            if not user:
                raise exceptions.AuthenticationFailed('User not found')
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')
