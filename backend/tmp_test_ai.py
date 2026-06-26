import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from analysis.assistant import ForensicAIAssistant

client = ForensicAIAssistant()
print(client.chat('', '', 'hi', history=[{'role': 'assistant', 'content': 'Hello'}]))
