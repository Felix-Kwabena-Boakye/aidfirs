"""
Custom JWT Authentication for MongoDB-backed User model.

The app issues tokens with PyJWT (not djangorestframework-simplejwt),
so we need a custom authentication class that:
  1. Reads the Bearer token from the Authorization header
  2. Decodes it with PyJWT using SECRET_KEY
  3. Looks up the user in MongoDB by user_id from the payload
  4. Returns (user, token) so DRF permissions work correctly

This replaces simplejwt.authentication.JWTAuthentication in settings.py.
"""

import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import User


class MongoJWTAuthentication(BaseAuthentication):
    """
    Authenticate requests using the custom PyJWT tokens issued by LoginView.
    Token format: Authorization: Bearer <token>
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None  # No token — let DRF fall through to anonymous

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired. Please log in again.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token.')

        # Only accept access tokens, not refresh tokens
        if payload.get('type') != 'access':
            raise AuthenticationFailed('Invalid token type.')

        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Token payload missing user_id.')

        user = User.get_by_id(user_id)
        if not user:
            raise AuthenticationFailed('User not found.')

        if not user.is_active:
            raise AuthenticationFailed('User account is inactive.')

        return (user, token)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
