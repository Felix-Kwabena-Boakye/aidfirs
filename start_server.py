import os
import sys
import subprocess

# Change to backend directory
os.chdir('c:/Users/HomePC/Downloads/ai-digital-forensics-system-complete/backend')

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

# Add backend to path
sys.path.insert(0, 'c:/Users/HomePC/Downloads/ai-digital-forensics-system-complete/backend')

# Run the Django server
os.system('python manage.py runserver')
