# AIDFIRS Forensic Agent

AIDFIRS Forensic Agent is a secure local client application written in Python. It runs directly on the investigator's local workstation, granting physical access to local disk controllers, block storage, and USB interfaces.

## Features

- **USB / External Disk Detection**: Automatically monitors block storage insertion and registers drive properties with the cloud API.
- **Physical Disk Imaging**: Acquires bit-stream raw disk images (.dd/.img) and generates cryptographic SHA-256 and SHA-512 report files.
- **Deleted File Recovery**: Restores deleted files from NTFS, FAT32, exFAT, and EXT4 filesystems.
- **File Carving**: Extracts file candidates from raw disk sectors using headers and footers signatures.
- **JWT Auth Integration**: Authenticates securely with the AIDFIRS cloud backend.
- **File Transmission**: Safely transmits recovered forensic evidence metadata and file binaries back to the secure cloud repository.

## Installation

1. Install Python 3.8+ on the investigator workstation.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the agent (requires administrator/root privileges to access physical disk devices):
   ```bash
   # Windows (Run as Administrator)
   python main.py

   # Linux
   sudo python main.py
   ```

## Configuration

Settings can be edited inside `config.py` or overridden using environment variables:

- `AIDFIRS_BACKEND_URL`: URL of the cloud backend (default: `http://localhost:8000`)
- `AIDFIRS_AGENT_NAME`: Custodian name / node hostname
