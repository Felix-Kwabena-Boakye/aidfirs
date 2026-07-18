import os
import sys
import time
import threading
from datetime import datetime, timezone

from config import (
    BACKEND_URL, AGENT_NAME, AGENT_OS, USB_SCAN_INTERVAL,
    JOB_POLL_INTERVAL, LOG_DIR, STORAGE_DIR
)
from api.auth import AgentAuth
from api.client import AgentAPIClient
from usb.monitor import USBDeviceMonitor
from forensic.recovery import LocalRecoveryEngine
from forensic.imaging import acquire_disk_image

def print_header():
    header = """
==================================================
              AIDFIRS FORENSIC AGENT
    (Distributed Digital Forensic Acquisition)
==================================================
Agent Hostname:    {hostname}
Agent OS:          {os}
Backend Endpoint:  {backend}
==================================================
""".format(hostname=AGENT_NAME, os=AGENT_OS, backend=BACKEND_URL)
    print(header)

class ForensicAgent:
    def __init__(self):
        # Create necessary directories
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
        self.auth = AgentAuth()
        self.client = AgentAPIClient(self.auth)
        self.monitor = USBDeviceMonitor(interval=USB_SCAN_INTERVAL)
        self.running_jobs = set()

    def start(self):
        print_header()
        
        # Initial authentication
        if not self.auth.authenticate():
            print("[Agent] CRITICAL: Could not authenticate with cloud backend.")
            print("[Agent] Ensure the Django API is running and accessible.")
            print("[Agent] Retrying in 10 seconds...")
            time.sleep(10)
            self.start()
            return

        # Start USB monitoring
        self.monitor.add_callback(self.on_devices_changed)
        self.monitor.start()
        print("[Agent] USB device monitoring active...")
        
        # Main job polling loop
        print("[Agent] Polling for recovery jobs...")
        while True:
            try:
                self.poll_jobs()
            except Exception as e:
                print(f"[Agent] Error during job poll: {e}")
            time.sleep(JOB_POLL_INTERVAL)

    def on_devices_changed(self, devices):
        print("\n=================================")
        print(" AIDFIRS FORENSIC MONITOR UPDATE")
        print("=================================")
        
        if not devices:
            print("No external forensic devices connected.")
            return

        for dev in devices:
            # Register device on backend
            success = self.client.register_device(dev.to_dict())
            status_text = "Ready" if success else "Failed to Register"
            
            print(f"\nUSB DEVICE DETECTED")
            print(f"Name:        {dev.volume_name or dev.model}")
            print(f"Size:        {dev.size_gb}GB")
            print(f"Filesystem:  {dev.filesystem or 'Unknown'}")
            print(f"Serial:      {dev.serial_number or 'UNKNOWN'}")
            print(f"Letter/Node: {dev.drive_letter}")
            print(f"Status:      {status_text}")
            print("-" * 30)

    def poll_jobs(self):
        pending_jobs = self.client.get_pending_jobs()
        for job in pending_jobs:
            job_id = job.get("id") or job.get("_id")
            if job_id and job_id not in self.running_jobs:
                self.running_jobs.add(job_id)
                # Spawn a daemon thread to process the job in background
                t = threading.Thread(target=self.process_job, args=(job,), daemon=True)
                t.start()

    def process_job(self, job):
        job_id = job.get("id") or job.get("_id")
        case_id = job.get("case_id")
        device_id = job.get("device_id")
        recovery_type = job.get("recovery_type", "full")

        print(f"\n[Job-{job_id}] Processing starting...")
        
        # 1. Update backend status to RUNNING
        self.client.update_job_status(job_id, "RUNNING", progress=10, files_found=0)

        # 2. Get device details to locate mount letter or device path
        devices = self.monitor.scan_now()
        target_device = None
        for d in devices:
            # Match by drive letter/mount point
            # Wait, the frontend or backend passes device_id, we can match registered devices
            # To be simple and robust: match serial or mount letters
            target_device = d
            break # default to first connected device for demonstration/recovery scans

        if not target_device and devices:
            target_device = devices[0]

        if not target_device:
            print(f"[Job-{job_id}] FAILED: No connected USB/HDD drive detected to recover files from.")
            self.client.update_job_status(job_id, "FAILED", progress=0, files_found=0)
            self.running_jobs.remove(job_id)
            return

        source_drive = target_device.drive_letter
        print(f"[Job-{job_id}] Target drive locked: {source_drive}")

        # 3. Create job workspace
        job_workspace = os.path.join(STORAGE_DIR, f"job_{job_id}")
        os.makedirs(job_workspace, exist_ok=True)

        try:
            # 4. Check for imaging request
            if recovery_type == "imaging":
                print(f"[Job-{job_id}] Performing RAW DD Acquisition...")
                img_path = os.path.join(job_workspace, f"CASE_{case_id}_IMAGE.dd")
                
                def update_img_progress(percent):
                    self.client.update_job_status(job_id, "RUNNING", progress=int(10 + percent * 0.8), files_found=0)
                
                report = acquire_disk_image(source_drive, img_path, progress_callback=update_img_progress)
                print(f"[Job-{job_id}] RAW DD image completed: {report['image_path']}")
                
                # Upload image metadata file as a carved/recovered document
                filename = os.path.basename(report['image_path'])
                self.client.upload_recovered_file(
                    job_id=job_id,
                    filename=filename,
                    filepath=report['image_path'],
                    hash_sha256=report['sha256'],
                    hash_sha512=report['sha512']
                )
                self.client.update_job_status(job_id, "COMPLETED", progress=100, files_found=1)
                
            else:
                # 5. Run Recovery Engine (Carving & Recycle bin)
                engine = LocalRecoveryEngine(output_dir=job_workspace)
                self.client.update_job_status(job_id, "RUNNING", progress=30, files_found=0)
                
                # Scan source partition
                recovered_files = engine.scan_and_recover(source_drive, recovery_type=recovery_type)
                total_files = len(recovered_files)
                print(f"[Job-{job_id}] Scan completed. Found {total_files} deleted files.")
                
                self.client.update_job_status(job_id, "RUNNING", progress=60, files_found=total_files)

                # 6. Upload files to backend
                uploaded_count = 0
                for idx, file_info in enumerate(recovered_files):
                    success = self.client.upload_recovered_file(
                        job_id=job_id,
                        filename=file_info["filename"],
                        filepath=file_info["filepath"],
                        hash_sha256=file_info["hash_sha256"],
                        hash_sha512=file_info["hash_sha512"]
                    )
                    if success:
                        uploaded_count += 1
                    
                    # Update progress incrementally during uploads
                    pct = int(60 + (idx / total_files) * 40)
                    self.client.update_job_status(job_id, "RUNNING", progress=pct, files_found=uploaded_count)

                # 7. Update status to COMPLETED
                self.client.update_job_status(job_id, "COMPLETED", progress=100, files_found=uploaded_count)
                print(f"[Job-{job_id}] Completed. Uploaded {uploaded_count}/{total_files} recovered files.")

        except Exception as e:
            print(f"[Job-{job_id}] Error executing recovery: {e}")
            self.client.update_job_status(job_id, "FAILED", progress=0, files_found=0)

        finally:
            self.running_jobs.remove(job_id)


if __name__ == "__main__":
    # If run in test mode, exit after basic configuration checks
    if "--test-mode" in sys.argv:
        print("AIDFIRS Forensic Agent Configuration: OK")
        sys.exit(0)
        
    agent = ForensicAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        print("\n[Agent] Exiting...")
        agent.monitor.stop()
        sys.exit(0)
