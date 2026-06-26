import os
import subprocess

# Change to the unified frontend directory
os.chdir('c:/Users/HomePC/Downloads/ai-digital-forensics-system-complete/frontend/web')

# Run the frontend dev server on port 3000
result = subprocess.run(['npm', 'run', 'dev'], shell=True)

