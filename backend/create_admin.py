#!/usr/bin/env python
"""
Create admin user script for Forensic AI Assistant.
Provides in-memory fallback when MongoDB is unavailable.
"""
import os
import sys
import json
import hashlib
import uuid
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

# Set SECRET_KEY if not set
if not os.getenv('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'rQidvr-pRou5_INRez1Lz4rvBmYG56g9FVl1BHkaeCj_a7ldaqbsrD4czjIfePsVHP0'

# In-memory user storage (fallback when MongoDB unavailable)
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')

def load_users():
    """Load users from file or return empty list."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_users(users):
    """Save users to file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, default=str)

def hash_password(password):
    """Hash password using SHA256 with salt."""
    salt = str(uuid.uuid4())[:8]
    salted = f"{salt}{password}"
    return f"{salt}${hashlib.sha256(salted.encode()).hexdigest()}"

def verify_password(password, password_hash):
    """Verify password against hash."""
    try:
        salt, hashed = password_hash.split('$')
        salted = f"{salt}{password}"
        return hashed == hashlib.sha256(salted.encode()).hexdigest()
    except:
        return False

# Try importing MongoDB User model
try:
    from mongo_connection import users_collection, MONGO_AVAILABLE
    
    if MONGO_AVAILABLE and users_collection is not None:
        from accounts.models import User
        
        # Try to create using MongoDB
        try:
            existing_admin = User.get_by_username('admin')
            if existing_admin:
                print(f'Admin user already exists: {existing_admin.username} ({existing_admin.role})')
                print(f'User ID: {existing_admin._id}')
            else:
                admin = User.create_user(
                    username='admin',
                    email='admin@example.com',
                    password='admin',
                    role='admin',
                    first_name='Admin',
                    last_name='User',
                    is_active=True
                )
                print(f'Successfully created admin user in MongoDB')
                print(f'Login: admin / admin')
        except Exception as e:
            print(f'MongoDB error: {e}')
            MONGO_AVAILABLE = False
    else:
        MONGO_AVAILABLE = False
except Exception as e:
    print(f'Import error: {e}')
    MONGO_AVAILABLE = False

# Fallback to file-based storage
if not MONGO_AVAILABLE or users_collection is None:
    print('Using file-based user storage (fallback mode)')
    
    # Load existing users
    users = load_users()
    
    # Check if admin exists
    existing = next((u for u in users if u.get('username') == 'admin'), None)
    
    if existing:
        print(f'Admin user already exists: {existing.get("username")} ({existing.get("role")})')
        print(f'User ID: {existing.get("_id")}')
    else:
        # Create new admin user
        new_user = {
            '_id': str(uuid.uuid4()),
            'username': 'admin',
            'email': 'admin@example.com',
            'password_hash': hash_password('admin'),
            'role': 'admin',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_active': True,
            'is_staff': True,
            'date_joined': datetime.now(timezone.utc).isoformat()
        }
        users.append(new_user)
        save_users(users)
        
        print(f'Successfully created admin user (file-based)')
        print(f'User ID: {new_user["_id"]}')
        print(f'Role: {new_user["role"]}')
        print('')
        print('Login credentials: admin / admin')
