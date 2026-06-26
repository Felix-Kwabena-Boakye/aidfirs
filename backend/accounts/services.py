from .models import User
from .serializers import UserPydantic, UserLoginPydantic
from typing import Optional, Tuple
import jwt
import json
import os
from datetime import datetime, timedelta, timezone
from django.conf import settings
from pydantic import ValidationError

# File-based user storage fallback
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, 'users.json')

def _get_users_from_file():
    """Load users from file."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def _save_users_to_file(users):
    """Save users to file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, default=str)

def _verify_password_file(password, password_hash):
    """Verify password from file-based storage."""
    import hashlib
    import uuid
    try:
        salt, hashed = password_hash.split('$')
        salted = f"{salt}{password}"
        return hashed == hashlib.sha256(salted.encode()).hexdigest()
    except:
        return False

def _get_user_by_email_file(email):
    """Get user by email from file."""
    users = _get_users_from_file()
    for u in users:
        if u.get('email') == email:
            return u
    return None

def _get_user_by_id_file(user_id):
    """Get user by id from file."""
    users = _get_users_from_file()
    for u in users:
        if str(u.get('_id')) == str(user_id):
            return User.from_dict(u)
    return None

class UserService:
    @staticmethod
    def create_user(
        username: str, 
        email: str, 
        password: str, 
        role: str = 'analyst',
        first_name: str = '',
        last_name: str = '',
        is_active: bool = True
    ) -> User:
        return User.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active
        )
    
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[User]:
        # First try MongoDB if available
        try:
            user = User.authenticate(username, password)
            if user:
                return user
        except Exception:
            # Mongo unavailable, continue to file fallback
            pass
        
        # Fallback to file-based storage
        users = _get_users_from_file()
        for u in users:
            # Match by username OR email
            if (u.get('username') == username or u.get('email') == username) and u.get('is_active', True):
                if _verify_password_file(password, u.get('password_hash', '')):
                    return User.from_dict(u)
        
        return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        # Try MongoDB first
        try:
            user = User.get_by_id(user_id) if hasattr(User, 'get_by_id') else None
        except Exception:
            user = None
        if user:
            return user
        # Fallback to file
        return _get_user_by_id_file(user_id)
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        # Try MongoDB first
        try:
            user = User.get_by_email(email) if hasattr(User, 'get_by_email') else None
        except Exception:
            user = None
        if user:
            return user
        # Fallback to file
        return _get_user_by_email_file(email)
    
    @staticmethod
    def generate_tokens(user: User) -> Tuple[str, str]:
        """Generate JWT access and refresh tokens."""
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
    
    @staticmethod
    def validate_registration(data: dict, is_admin: bool = False) -> bool:
        """Validate registration data using Pydantic."""
        try:
            # Create a copy to avoid mutating original data during validation
            validation_data = data.copy()
            user_data = UserPydantic(**validation_data)
            
            # Non-admins cannot register as admins
            if not is_admin and user_data.role == 'admin':
                return False
            return True
        except Exception as e:
            print(f"Registration validation error: {e}")
            return False
