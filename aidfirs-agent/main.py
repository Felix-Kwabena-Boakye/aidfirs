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
        
        # 1. Update status to RUNNING / DEVICE_DETECTION
        self.client.update_job_status(
            job_id, "RUNNING", progress=5, stage="DEVICE_DETECTION",
            files_found=0
        )

        # Fetch device details from backend
        db_device = self.client.get_device_details(device_id)
        if db_device:
            print(f"[Job-{job_id}] Fetched backend device details: {db_device.get('device_name')} (Serial: {db_device.get('serial_number')})")

        # 2. Match device locally
        devices = self.monitor.scan_now()
        target_device = None

        if db_device:
            db_serial = str(db_device.get("serial_number", "")).strip().upper()
            db_letter = str(db_device.get("drive_letter", "")).strip().upper()
            db_model = str(db_device.get("model", "")).strip().lower()

            for d in devices:
                local_serial = str(d.serial_number or "").strip().upper()
                local_letter = str(d.drive_letter or "").strip().upper()
                local_model = str(d.model or "").strip().lower()

                # Match by serial number first
                if db_serial and db_serial != "UNKNOWN" and db_serial == local_serial:
                    target_device = d
                    print(f"[Job-{job_id}] Device matched by Serial Number: {local_serial}")
                    break
                # Match by drive letter
                elif db_letter and db_letter == local_letter:
                    target_device = d
                    print(f"[Job-{job_id}] Device matched by Drive Letter: {local_letter}")
                    break
                # Match by model
                elif db_model and db_model in local_model:
                    target_device = d
                    print(f"[Job-{job_id}] Device matched by Model: {d.model}")
                    break

        if not target_device and db_device:
            # Fallback to direct letter usage if drive letter exists on local machine
            db_letter = str(db_device.get("drive_letter", "")).strip()
            if db_letter and (os.path.exists(db_letter + ":\\") or os.path.exists(db_letter)):
                # Mock a target device
                from usb.detector import USBDevice
                target_device = USBDevice(
                    drive_letter=db_letter,
                    volume_name=db_device.get("device_name", ""),
                    drive_type=db_device.get("drive_type", "USB Drive"),
                    size_gb=db_device.get("size_gb", 0.0),
                    serial_number=db_device.get("serial_number", ""),
                    filesystem=db_device.get("filesystem", ""),
                    model=db_device.get("model", "")
                )
                print(f"[Job-{job_id}] Fell back to direct drive path: {db_letter}")

        if not target_device:
            err_msg = "No connected USB/HDD drive detected to perform forensic operations."
            print(f"[Job-{job_id}] FAILED: {err_msg}")
            self.client.update_job_status(job_id, "FAILED", progress=0, stage="FAILED", error_message=err_msg)
            self.running_jobs.remove(job_id)
            return

        source_drive = target_device.drive_letter
        print(f"[Job-{job_id}] Target drive locked: {source_drive}")

        # Create job workspace
        job_workspace = os.path.join(STORAGE_DIR, f"job_{job_id}")
        os.makedirs(job_workspace, exist_ok=True)

        try:
            # Under forensic guidelines, we ALWAYS image first before recovery.
            # 3. Create Forensic Image (Disk Imaging Stage)
            self.client.update_job_status(job_id, "RUNNING", progress=10, stage="DISK_IMAGING")
            
            img_format = "dd"
            img_ext = ".dd"
            img_path = os.path.join(job_workspace, f"CASE_{case_id}_DEVICE_{device_id}{img_ext}")
            
            print(f"[Job-{job_id}] Creating forensic image: {img_path}...")
            
            def update_img_progress(percent):
                # Scale imaging progress from 10% to 50%
                scaled_pct = int(10 + percent * 0.4)
                self.client.update_job_status(job_id, "RUNNING", progress=scaled_pct, stage="DISK_IMAGING")
            
            # Acquire image
            report = acquire_disk_image(
                source=source_drive,
                destination=img_path,
                progress_callback=update_img_progress,
                case_id=case_id,
                examiner=AGENT_NAME,
                device_id=device_id
            )
            print(f"[Job-{job_id}] Forensic disk image completed: {report['image_path']}")
            
            # 4. Hash Calculation Stage (computed on-the-fly, register/upload image)
            self.client.update_job_status(job_id, "RUNNING", progress=55, stage="HASH_CALCULATION")
            
            image_filename = os.path.basename(report['image_path'])
            image_upload_success = self.client.upload_recovered_file(
                job_id=job_id,
                filename=image_filename,
                filepath=report['image_path'],
                hash_sha256=report['sha256'],
                hash_sha512=report['sha512'],
                hash_md5=report.get('md5'),
                original_path=source_drive,
                recovery_method="forensic_imaging",
                recovery_status="completed",
                device_id=device_id,
                examiner=AGENT_NAME,
                description=f"Forensic Disk Image of device {device_id}"
            )

            # Upload the acquisition text report as well
            if os.path.exists(report['report_path']):
                rep_name = os.path.basename(report['report_path'])
                from forensic.hashing import compute_all_hashes
                rep_hashes = compute_all_hashes(report['report_path'])
                self.client.upload_recovered_file(
                    job_id=job_id,
                    filename=rep_name,
                    filepath=report['report_path'],
                    hash_sha256=rep_hashes['sha256'],
                    hash_sha512=rep_hashes['sha512'],
                    hash_md5=rep_hashes['md5'],
                    original_path=source_drive,
                    recovery_method="forensic_report",
                    recovery_status="completed",
                    device_id=device_id,
                    examiner=AGENT_NAME,
                    description=f"Forensic Disk Imaging Acquisition Report"
                )

            if recovery_type == "imaging":
                # If only imaging was requested, complete job now
                self.client.update_job_status(job_id, "COMPLETED", progress=100, stage="COMPLETED", files_found=1)
                print(f"[Job-{job_id}] Completed. Uploaded forensic image.")
            else:
                # 5. Recovery Stages (Scanning, Carving, File Recovery)
                # We perform the recovery ON the newly created forensic image, NEVER the original device!
                self.client.update_job_status(job_id, "RUNNING", progress=60, stage="SCANNING")
                
                engine = LocalRecoveryEngine(
                    output_dir=job_workspace,
                    examiner=AGENT_NAME,
                    case_id=case_id,
                    device_id=device_id
                )
                
                # Scan partition image file
                recovered_files = engine.scan_and_recover(source_drive, recovery_type=recovery_type, image_path=img_path)
                total_files = len(recovered_files)
                print(f"[Job-{job_id}] Forensic recovery completed. Found {total_files} deleted files.")
                
                self.client.update_job_status(job_id, "RUNNING", progress=75, stage="SAVING", files_found=total_files)

                # 6. Upload recovered files and metadata to backend
                self.client.update_job_status(job_id, "RUNNING", progress=80, stage="UPLOADING_METADATA")
                uploaded_count = 0
                for idx, file_info in enumerate(recovered_files):
                    success = self.client.upload_recovered_file(
                        job_id=job_id,
                        filename=file_info["filename"],
                        filepath=file_info["filepath"],
                        hash_sha256=file_info["hash_sha256"],
                        hash_sha512=file_info["hash_sha512"],
                        hash_md5=file_info.get("hash_md5"),
                        hash_sha1=file_info.get("hash_sha1"),
                        original_path=file_info.get("original_path", ""),
                        recovery_method=file_info.get("recovery_method", "signature_carving"),
                        recovery_status="recovered" if file_info.get("recoverable") else "damaged",
                        created_time=file_info.get("created_time"),
                        modified_time=file_info.get("modified_time"),
                        accessed_time=file_info.get("accessed_time"),
                        deleted_time=file_info.get("deleted_time"),
                        device_id=device_id,
                        examiner=AGENT_NAME,
                        carve_offset=file_info.get("carve_offset"),
                        description=file_info.get("description", "")
                    )
                    if success:
                        uploaded_count += 1
                    
                    # Update progress incrementally during uploads (scale from 80% to 98%)
                    pct = int(80 + (idx / total_files) * 18) if total_files > 0 else 98
                    self.client.update_job_status(job_id, "RUNNING", progress=pct, stage="UPLOADING_METADATA", files_found=uploaded_count)

                # 7. Update status to COMPLETED
                self.client.update_job_status(job_id, "COMPLETED", progress=100, stage="COMPLETED", files_found=uploaded_count)
                print(f"[Job-{job_id}] Completed. Uploaded {uploaded_count}/{total_files} recovered files.")

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = f"Forensic execution error: {str(e)}"
            print(f"[Job-{job_id}] Failed with error: {err_msg}")
            self.client.update_job_status(job_id, "FAILED", progress=0, stage="FAILED", error_message=err_msg)

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
