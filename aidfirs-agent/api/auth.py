import os
import json
import requests
from config import BACKEND_URL, AGENT_NAME, AGENT_OS, CREDENTIALS_FILE

class AgentAuth:
    """Manages Agent identity and JWT authentication with AIDFIRS cloud backend."""
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.agent_id = None
        self.load_cached_credentials()

    def load_cached_credentials(self):
        if os.path.exists(CREDENTIALS_FILE):
            try:
                with open(CREDENTIALS_FILE, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get("access")
                    self.refresh_token = data.get("refresh")
                    self.agent_id = data.get("agent_id")
            except Exception:
                pass

    def cache_credentials(self):
        try:
            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump({
                    "access": self.access_token,
                    "refresh": self.refresh_token,
                    "agent_id": self.agent_id
                }, f)
        except Exception as e:
            print(f"[Auth] Failed to cache credentials: {e}")

    def authenticate(self) -> bool:
        """Register/authenticate with cloud backend and get JWT token."""
        print(f"[Auth] Authenticating agent '{AGENT_NAME}' with cloud backend at {BACKEND_URL}...")
        url = f"{BACKEND_URL}/api/agents/register/"
        payload = {
            "hostname": AGENT_NAME,
            "os": AGENT_OS
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access")
                self.refresh_token = data.get("refresh")
                self.agent_id = data.get("agent_id")
                self.cache_credentials()
                print(f"[Auth] Authenticated successfully. Agent ID: {self.agent_id}")
                return True
            else:
                print(f"[Auth] Authentication failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[Auth] Connection error while authenticating: {e}")
            return False

    def get_auth_header(self) -> dict:
        if not self.access_token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.access_token}"}
