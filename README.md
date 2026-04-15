# AI Digital Forensics System - Dual Dashboard Edition

## Quick Start

1. Start backend:
   ```
   python start_server.py
   ```

2. Start Admin Dashboard (port 3001):
   ```
   python start_admin.py
   ```
   Open: http://localhost:3001

3. Start Investigator Dashboard (port 3002):
   ```
   python start_investigator.py
   ```
   Open: http://localhost:3002

## Features

- **Admin**: Full access (users, audit, all)
- **Investigator**: Forensic tools (devices, evidence recovery, analysis)
- **Metadata Recovery**: Evidence → 'Recover Deleted Metadata' button for deleted files from drives/USB.
- Role auto-redirect on login.

## Core: Deleted Metadata Recovery
- Upload disk image/USB
- Evidence list → Recover Deleted → TSK recovers metadata/table (inode, name, size, delete time)
- AI analysis & report.

npm install complete. Ready!
