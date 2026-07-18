import os
import requests
from typing import List, Dict, Optional
from config import BACKEND_URL
from .auth import AgentAuth

class AgentAPIClient:
    """Handles API requests between local agent and cloud backend."""
    def __init__(self, auth: AgentAuth):
        self.auth = auth

    def _request(self, method: str, path: str, **kwargs) -> Optional[requests.Response]:
        url = f"{BACKEND_URL}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self.auth.get_auth_header())
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                # Token might have expired, try re-authenticating
                if self.auth.authenticate():
                    headers.update(self.auth.get_auth_header())
                    response = requests.request(method, url, headers=headers, **kwargs)
            return response
        except Exception as e:
            print(f"[API] Request failed for {path}: {e}")
            return None

    def register_device(self, device_data: Dict) -> bool:
        """Register a connected device with the cloud backend."""
        res = self._request("POST", "/api/devices/register/", json=device_data)
        if res and res.status_code in (200, 201):
            return True
        return False

    def get_pending_jobs(self) -> List[Dict]:
        """Fetch pending recovery jobs from backend."""
        res = self._request("GET", "/api/recovery/jobs/pending/")
        if res and res.status_code == 200:
            return res.json().get("jobs", [])
        return []

    def update_job_status(self, job_id: str, status_str: str, progress: int = None, files_found: int = None) -> bool:
        """Update job status and progress details on the backend."""
        payload = {"status": status_str}
        if progress is not None:
            payload["progress"] = progress
        if files_found is not None:
            payload["files_found"] = files_found

        res = self._request("PATCH", f"/api/recovery/jobs/{job_id}/", json=payload)
        if res and res.status_code == 200:
            return True
        return False

    def upload_recovered_file(self, job_id: str, filename: str, filepath: str, hash_sha256: str, hash_sha512: str) -> bool:
        """Upload a carved file binary and its hashes to the server."""
        if not os.path.exists(filepath):
            return False

        payload = {
            "filename": filename,
            "hash_sha256": hash_sha256,
            "hash_sha512": hash_sha512
        }

        try:
            with open(filepath, 'rb') as f:
                files = {'file': (os.path.basename(filepath), f, 'application/octet-stream')}
                url = f"{BACKEND_URL}/api/recovery/jobs/{job_id}/upload/"
                headers = self.auth.get_auth_header()
                
                response = requests.post(url, headers=headers, data=payload, files=files, timeout=600)
                if response.status_code == 401:
                    if self.auth.authenticate():
                        headers = self.auth.get_auth_header()
                        f.seek(0)
                        response = requests.post(url, headers=headers, data=payload, files=files, timeout=600)

                if response.status_code in (200, 201):
                    return True
                else:
                    print(f"[API] File upload failed for {filename}: {response.text}")
                    return False
        except Exception as e:
            print(f"[API] Connection error uploading file {filename}: {e}")
            return False
