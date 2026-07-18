import os
import platform

# The URL of the AIDFIRS Cloud Backend Django REST API
BACKEND_URL = os.getenv("AIDFIRS_BACKEND_URL", "http://localhost:8000")

# Identity settings
AGENT_NAME = os.getenv("AIDFIRS_AGENT_NAME", platform.node())
AGENT_OS = platform.system()

# Intervals (in seconds)
USB_SCAN_INTERVAL = 3
JOB_POLL_INTERVAL = 5

# Local paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

# Security credentials storage file
CREDENTIALS_FILE = os.path.join(BASE_DIR, ".agent_credentials")
