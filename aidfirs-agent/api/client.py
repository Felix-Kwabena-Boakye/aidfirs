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

    def get_device_details(self, device_id: str) -> Optional[Dict]:
        """Fetch registered device details from backend by ID."""
        res = self._request("GET", f"/api/devices/{device_id}/")
        if res and res.status_code == 200:
            return res.json().get("device")
        return None


    def get_pending_jobs(self) -> List[Dict]:
        """Fetch pending recovery jobs from backend."""
        res = self._request("GET", "/api/recovery/jobs/pending/")
        if res and res.status_code == 200:
            return res.json().get("jobs", [])
        return []

    def update_job_status(self, job_id: str, status_str: str, progress: int = None, files_found: int = None, stage: str = None, error_message: str = None) -> bool:
        """Update job status, progress, stage and error details on the backend."""
        payload = {"status": status_str}
        if progress is not None:
            payload["progress"] = progress
        if files_found is not None:
            payload["files_found"] = files_found
        if stage is not None:
            payload["stage"] = stage
        if error_message is not None:
            payload["error_message"] = error_message

        res = self._request("PATCH", f"/api/recovery/jobs/{job_id}/", json=payload)
        if res and res.status_code == 200:
            return True
        return False

    def upload_recovered_file(self, job_id: str, filename: str, filepath: str, hash_sha256: str, hash_sha512: str, hash_md5: str = None, hash_sha1: str = None, original_path: str = None, recovery_method: str = None, recovery_status: str = None, created_time: str = None, modified_time: str = None, accessed_time: str = None, deleted_time: str = None, device_id: str = None, examiner: str = None, carve_offset: int = None, description: str = None) -> bool:
        """Upload a carved/recovered file binary and its complete forensic metadata to the server."""
        if not os.path.exists(filepath):
            return False

        payload = {
            "filename": filename,
            "hash_sha256": hash_sha256,
            "hash_sha512": hash_sha512
        }
        if hash_md5: payload["hash_md5"] = hash_md5
        if hash_sha1: payload["hash_sha1"] = hash_sha1
        if original_path is not None: payload["original_path"] = original_path
        if recovery_method is not None: payload["recovery_method"] = recovery_method
        if recovery_status is not None: payload["recovery_status"] = recovery_status
        if created_time is not None: payload["created_time"] = created_time
        if modified_time is not None: payload["modified_time"] = modified_time
        if accessed_time is not None: payload["accessed_time"] = accessed_time
        if deleted_time is not None: payload["deleted_time"] = deleted_time
        if device_id is not None: payload["device_id"] = device_id
        if examiner is not None: payload["examiner"] = examiner
        if carve_offset is not None: payload["carve_offset"] = carve_offset
        if description is not None: payload["description"] = description

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

    def heartbeat(self) -> bool:
        """Send heartbeat ping to the cloud backend to confirm agent is alive."""
        res = self._request("GET", "/api/agents/heartbeat/")
        if res and res.status_code == 200:
            return True
        return False

    def register_image(self, job_id: str, image_path: str, sha256: str, md5: str = None, sha1: str = None, sha512: str = None, size_bytes: int = None, format: str = None) -> bool:
        """Register a forensic disk image with its metadata on the backend."""
        payload = {
            "image_path": image_path,
            "sha256": sha256,
        }
        if md5: payload["md5"] = md5
        if sha1: payload["sha1"] = sha1
        if sha512: payload["sha512"] = sha512
        if size_bytes is not None: payload["size_bytes"] = size_bytes
        if format: payload["format"] = format

        res = self._request("POST", f"/api/recovery/jobs/{job_id}/upload/", json=payload)
        if res and res.status_code in (200, 201):
            return True
        return False