import os
import subprocess

# Change to frontend directory
os.chdir('c:/Users/HomePC/Downloads/ai-digital-forensics-system-complete/frontend')

# Run the frontend dev server
result = subprocess.run(['npm', 'run', 'dev'], shell=True)
