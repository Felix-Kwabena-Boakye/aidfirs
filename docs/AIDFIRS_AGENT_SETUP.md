# AIDFIRS Forensic Agent Setup Guide

This guide details how to install, configure, run, and verify the local **AIDFIRS Forensic Agent** on an investigator workstation.

## Overview

The **AIDFIRS Forensic Agent** is a lightweight local Python application designed to run on the investigator's computer. It performs forensic disk acquisition (RAW DD), deleted file carving/recovery, and USB monitoring, sending findings and status updates securely via HTTPS to the cloud backend.

```
+---------------------------+        HTTPS API        +-----------------------+
|  Investigator Workstation | <---------------------> | AIDFIRS Cloud Backend |
| (AIDFIRS Forensic Agent)  |         (JWT)           | (Django REST API)     |
+---------------------------+                         +-----------------------+
              |                                                   |
              v                                                   v
      USB/HDD Devices                                       MongoDB Atlas
```

---

## Installation

### Prerequisites

1. **Python 3.10+**: Ensure Python is installed on your workstation.
2. **Administrator/Root Privileges**: High-level block device access is required for raw drive imaging and file carving.

### Step 1: Install Dependencies

Navigate to the agent directory and install the required Python packages:

```bash
cd aidfirs-agent
pip install -r requirements.txt
```

The key dependencies are:
- `requests`: Secure REST API communication.
- `psutil`: Physical and logical volume discovery.
- `pyjwt`: Authenticating requests using JSON Web Tokens.

---

## Configuration

The agent is configured using environment variables or settings inside `config.py`.

### Identity Settings
- `AIDFIRS_BACKEND_URL`: URL of the cloud backend (defaults to `http://localhost:8000`).
- `AIDFIRS_AGENT_NAME`: Workstation identifier (defaults to your computer's hostname).

### Execution Intervals
- `USB_SCAN_INTERVAL`: Frequency of local hardware discovery (default: `3` seconds).
- `JOB_POLL_INTERVAL`: Frequency of polling the backend for new jobs (default: `5` seconds).

---

## Running the Agent

Start the agent with administrator/root privileges:

### Windows (cmd/PowerShell as Admin)
```powershell
python main.py
```

### Linux (sudo)
```bash
sudo python3 main.py
```

Upon startup, the agent will:
1. Contact the backend `POST /api/agents/register/` using the workstation's hostname.
2. Receive a JWT Access & Refresh Token pair, which is cached locally in `.agent_credentials`.
3. Start the background hardware listener.

---

## Workflows

### 1. USB Device Connection
- Connect an external flash drive or HDD to the workstation.
- The agent detects the drive's serial number, volume name, capacity, filesystem, and mount path.
- The device details are registered on the backend (`POST /api/devices/register/`).
- The device instantly displays on the **Connected Devices** screen of the web dashboard with `Source: AIDFIRS Agent`.

### 2. Forensic Disk Acquisition
- From the web dashboard, clicking **Examine** initializes a new case and recovery job.
- The agent polls the backend, locks the target mount point, and starts a bit-stream physical copy (RAW DD image).
- Hashes (SHA-256 / SHA-512) are computed on-the-fly to guarantee evidentiary integrity.
- The image is saved in the agent's local `storage/` workspace and logged to the backend.

### 3. File Carving & Recovery
- The agent performs two-stage recovery:
  1. **Recycle Bin Analysis**: Resolves original file paths, names, and deletion timestamps.
  2. **Raw Signature Carving**: Scans block-by-block for file header/footer patterns (JPEG, PNG, PDF, ZIP, DOCX, XLSX, MP4) when metadata is missing.
- Recovered files are hashed, matched against metadata extractors (like GPS coordinates for JPEGs), and uploaded securely via multi-part POST requests.

### 4. Evidence Download Process
- The investigator accesses the **Recovered Files** section of the case dashboard.
- Clicking **Download** requests the file binary from `/api/recovery/files/<id>/download/`.
- The Django server:
  1. Checks investigator access permissions.
  2. Re-calculates the SHA-256 checksum of the stored binary on the server to verify integrity against the database registration hash.
  3. Registers a `FILE_DOWNLOADED` event in the **Audit Logs** and updates the **Chain of Custody** ledger.
  4. Returns the file as a secure attachment.
