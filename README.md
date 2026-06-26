# AI Digital Forensics System

## Overview
**AI Digital Forensics System** is a professional forensic analysis platform designed to recover, restore, and analyze digital assets across every domain — from files and media to system log audits. It combines traditional forensic tooling with modern modular AI capabilities to deliver automated evidence analysis, anomaly detection, and comprehensive reports.

---

## Quick Start

### Option 1: Docker Compose (Recommended - Production Mode)
To run the entire system, including MongoDB database, Redis queue, Django backend, and Vite React frontend, execute:
```bash
docker-compose up --build -d
```
- **Frontend App:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000/api/](http://localhost:8000/api/)

### Option 2: Local Development Setup

#### 1. Setup Backend
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Migrate sqlite database (used for Django admin/sessions)
cd backend
python manage.py migrate

# Create initial admin account
python manage.py createsuperuser
```

#### 2. Setup Frontend
```bash
# Install dependencies and start Vite dev server
cd frontend/web
npm install
npm run dev
```

---

## Environment Variables (.env)
Copy `.env.example` to `.env` in the root or `backend/` directory and configure the variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django Secret Key | Generated on setup |
| `DEBUG` | Django Debug Mode | `False` |
| `MONGO_URI` | MongoDB Connection URI | `mongodb://localhost:27017` |
| `MONGO_DB_NAME` | MongoDB database name | `ai_digital_forensics` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | `None` |
| `OLLAMA_URL` | Local Ollama base URL | `http://127.0.0.1:11434` |
| `MONGO_TLS_ALLOW_INVALID_CERTIFICATES` | Bypass Mongo TLS cert validation | `true` |

---

## Role-Based Access Control (RBAC)
The platform enforces a strict security policy based on user roles:

| Role | Permissions |
|------|-------------|
| **Admin** | Full system configuration, user activation/deactivation, AI model training, view audit logs, run system commands. |
| **Investigator** | Case creation, evidence uploads, running AI analysis pipelines, recovering files. |
| **Analyst** | View-only access to cases, evidence, and completed AI reports. Cannot initiate analysis or view administrative screens. |

---

## Features
- **Role-Based Access Control:** Granular DRF permission policies covering all endpoints.
- **Forensic AI Assistant:** Intelligent chat, classification, anomaly detection, and report generation powered by Claude or local Ollama.
- **AI Oracle Model Training:** Scikit-Learn Random Forest Classifier that predicts recoverability of deleted files based on size, entropy, partition type, and file type. Accessible ONLY by Admins.
- **TSK Disk Carving:** Traditional file extraction and timeline creation with Sleuth Kit.
- **Real-time USB monitoring:** Daemon script to monitor USB connection events on forensic workstations.
- **Robust Security:** JWT authentication with token rotation, rate-limiting, custom CSP headers, and audit trails.

---

## Automated Tests
Execute the entire test suite (unit tests, integration tests, permission matrices):
```bash
cd backend
python tests/run_all_tests.py
```

---

## CI/CD Pipeline
GitHub Actions are configured under `.github/workflows/ci.yml` to automatically lint code with `flake8`, format check with `black`, run the test suites, and build Docker containers.

---

## License
MIT
