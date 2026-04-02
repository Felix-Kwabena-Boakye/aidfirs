import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from accounts.models import User

# Check if admin exists
existing = User.get_by_username('admin')
if existing:
    print('Admin user already exists')
else:
    # Create admin user
    user = User.create_user(
        username='admin',
        email='admin@example.com',
        password='admin',
        role='admin',
        first_name='Admin',
        last_name='User'
    )
    user.is_staff = True
    user.save()
    print('Admin user created successfully')
