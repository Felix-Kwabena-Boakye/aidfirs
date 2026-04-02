# AI-Powered Digital Forensics System

A comprehensive AI-powered digital forensics platform for investigating cyber incidents, analyzing evidence, and managing forensic cases.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [License](#license)

---

## ✨ Features

### Core Forensic Features
- **Metadata Recovery** - Recover deleted files and metadata from hard drives/disk images
  - NTFS filesystem parsing (MFT, boot sector)
  - FAT filesystem parsing (boot sector, FAT table)
  - File signature detection
  - Timestamp extraction (Unix timestamps)
  - Deleted file entry recovery
- **Disk Image Analysis** - Analyze disk images for forensic evidence
- **Case Management** - Create, track, and manage forensic investigation cases
- **Evidence Tracking** - Upload and catalog digital evidence with hash verification (MD5, SHA1, SHA256)
- **AI-Powered Analysis** - Automated analysis using machine learning and NLP
  - Indicator extraction (IP addresses, URLs, file hashes, emails, domains)
  - Text summarization
  - Anomaly detection
  - Risk assessment
- **Device Detection** - USB device monitoring and detection
- **SMS/Text Analysis** - Twilio integration for SMS forensics
- **User Authentication** - JWT-based authentication with role-based access control

### User Roles

The system implements role-based access control (RBAC) with three user roles:

#### 👑 Admin Role
The Admin is the system controller with full access.

**Responsibilities:**
- Create investigator accounts
- Assign cases
- View all cases
- Manage AI models
- View system logs
- Activate/deactivate users
- Manage system configuration

**Permissions:**
- ✅ Full database access
- ✅ Can delete or archive cases
- ✅ Can manage AI model versions
- ✅ Can view audit logs
- ✅ Can create other admin/investigator accounts
- ✅ Can activate/deactivate user accounts
- ✅ Access to all API endpoints

#### 🕵️ Investigator Role
The Investigator is the forensic analyst who performs investigations.

**Responsibilities:**
- Create a new case
- Upload disk images
- Upload evidence
- Run AI metadata recovery
- View analysis results
- Generate forensic reports
- Maintain chain of custody

**Restrictions:**
- ❌ Cannot create other users
- ❌ Cannot modify AI models
- ❌ Cannot access system logs (except their own activity)
- ❌ Cannot delete system-level configurations
- ✅ Can view all cases
- ✅ Can manage cases and evidence they create

#### 📊 Analyst Role
The Analyst can view and analyze cases created by investigators.

**Responsibilities:**
- View cases they have access to
- View evidence
- View analysis results
- Generate reports

**Restrictions:**
- ❌ Cannot create cases
- ❌ Cannot upload evidence
- ❌ Cannot run analysis
- ❌ Cannot access system settings
- ❌ Cannot view other users' activity
- ✅ Read-only access to assigned cases

### Role-Based API Access

| Feature | Admin | Investigator | Analyst |
|---------|-------|--------------|---------|
| Create Users | ✅ | ❌ | ❌ |
| View All Users | ✅ | ❌ | ❌ |
| Activate/Deactivate Users | ✅ | ❌ | ❌ |
| Create Cases | ✅ | ✅ | ❌ |
| View All Cases | ✅ | ✅ | ❌ |
| View Assigned Cases | ✅ | ✅ | ✅ |
| Upload Evidence | ✅ | ✅ | ❌ |
| Run AI Analysis | ✅ | ✅ | ❌ |
| View Analysis Results | ✅ | ✅ | ✅ |
| Manage AI Settings | ✅ | ❌ | ❌ |
| View System Logs | ✅ | ❌ | ❌ |

---

## 🛠 Tech Stack

### Frontend
- **React** (Vite) - Modern frontend framework
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client
- **React Router** - Client-side routing

### Backend
- **Django** - Python web framework
- **Django REST Framework** - REST API
- **PyJWT** - JWT authentication
- **Celery** - Task queue
- **Redis** - Message broker

### Database
- **MongoDB** - NoSQL database for flexible document storage

### AI/ML
- **scikit-learn** - Machine learning library
- **Anthropic Claude** - AI integration (optional)

### External Services
- **Twilio** - SMS integration
- **Sleuth Kit** - Disk forensics (integration-ready)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│    http://localhost:5173 (Vite Dev Server)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/REST API
┌─────────────────────────▼───────────────────────────────────┐
│                     Backend (Django)                         │
│                   http://localhost:8000                      │
├─────────────────────────────────────────────────────────────┤
│  Accounts  │  Cases  │  Evidence  │  Analysis  │  Devices   │
│  (Auth)    │  (CRUD) │  (CRUD)    │  (AI)       │  (USB)    │
└────────────┴─────────┴─────────────┴─────────────┴──────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   MongoDB Atlas                               │
│              (Cloud Database)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📌 Prerequisites

Before installation, ensure you have:

1. **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
2. **Node.js 18+** - [Download Node.js](https://nodejs.org/)
3. **MongoDB Atlas Account** - [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
4. **Git** - For version control

### Optional Services
- **Twilio Account** - For SMS functionality
- **Anthropic API Key** - For Claude AI integration

---

## 💾 Installation

### 1. Clone the Repository

```
bash
git clone <repository-url>
cd ai-digital-forensics-system-complete
```

### 2. Backend Setup

```
bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
source venv/bin/activate

# Install Python dependencies
pip install -r backend/requirements.txt

# Configure environment variables
copy backend\.env.example backend\.env
# Edit .env with your MongoDB credentials
```

### 3. Frontend Setup

```
bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

---

## 🚀 Running the Application

### Option 1: Using the Start Scripts

#### Start Backend Server
```
bash
python start_server.py
```
The Django server will start at `http://localhost:8000`

#### Start Frontend
```
bash
python start_frontend.py
```
The React app will start at `http://localhost:5173`

### Option 2: Manual Startup

#### Backend
```
bash
cd backend
python manage.py migrate
python manage.py runserver
```

#### Frontend
```
bash
cd frontend
npm run dev
```

---

## 🧪 Testing

The system includes comprehensive tests covering models, AI engine, and API endpoints.

### Run All Tests

```
bash
cd backend
python tests/run_all_tests.py
```

This runs all three test suites:
- Model Tests (MongoDB connection, User, Case, Evidence, AnalysisResult)
- AI Engine Tests (Indicator Extraction, Summarization, Anomaly Detection, Integration)
- API Tests (Server Connection, Login, Cases, Evidence, Analysis, Devices)

### Run Individual Test Suites

#### Model & MongoDB Tests
```
bash
python tests/test_models.py
```
Tests MongoDB connection and data models (User, Case, Evidence, AnalysisResult)

#### AI Engine Tests
```
bash
python tests/test_ai_engine.py
```
Tests indicator extraction, summarization, anomaly detection, and the full AI engine

#### API Tests (Requires Running Server)
```
bash
# First start the server
python start_server.py

# Then run API tests in another terminal
python tests/test_api.py
```

### Test Results Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_models.py` | 5 tests (MongoDB, User, Case, Evidence, AnalysisResult) | ✅ PASSED |
| `test_ai_engine.py` | 4 tests (Indicator Extraction, Summarization, Anomaly Detection, Integration) | ✅ PASSED |
| `test_api.py` | 6 tests (Server, Login, Cases, Evidence, Analysis, Devices) | ✅ PASSED |
| `test_permissions.py` | 7 tests (Role definitions, Admin, Investigator, Analyst permissions) | ✅ PASSED |

**Total: 22/22 tests passed**

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/accounts/login/` | User login |
| POST | `/api/accounts/register/` | User registration |
| GET | `/api/accounts/profile/` | Get user profile |
| GET | `/api/accounts/users/` | List all users (admin) |
| GET/POST | `/api/accounts/ai-settings/` | AI settings |

### Cases
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cases/` | List all cases |
| POST | `/api/cases/` | Create new case |
| GET | `/api/cases/{id}/` | Get case details |
| PATCH | `/api/cases/{id}/` | Update case |
| DELETE | `/api/cases/{id}/` | Delete case |
| POST | `/api/cases/{id}/close/` | Close case |
| GET | `/api/cases/{id}/evidence/` | Get case evidence |

### Evidence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/evidence/` | List all evidence |
| POST | `/api/evidence/` | Upload evidence |
| GET | `/api/evidence/{id}/` | Get evidence details |
| PATCH | `/api/evidence/{id}/` | Update evidence |
| DELETE | `/api/evidence/{id}/` | Delete evidence |
| POST | `/api/evidence/{id}/mark_analyzed/` | Mark as analyzed |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis/` | List all analyses |
| POST | `/api/analysis/` | Create analysis |
| GET | `/api/analysis/{id}/` | Get analysis results |
| POST | `/api/analysis/{id}/complete/` | Mark complete |

### Devices
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/devices/` | List USB devices |
| POST | `/api/devices/scan/` | Start scanning |
| POST | `/api/devices/refresh/` | Force scan |

### Texting
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/texting/sms/` | List SMS logs |
| POST | `/api/texting/sms/` | Send SMS |
| GET | `/api/texting/sms/{id}/` | Get SMS details |
| GET | `/api/texting/sms/by-case/?case_id=` | Get SMS by case |

---

## 🔐 Environment Variables

Create a `.env` file in the `backend` directory:

```env
# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=ai-forensics-cluster
MONGO_DB_NAME=ai_digital_forensics

# JWT Secret Key
SECRET_KEY=your-secret-key-here

# Twilio Configuration (Optional)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Anthropic Claude API (Optional)
ANTHROPIC_API_KEY=your-api-key
CLAUDE_MODEL=claude-3-haiku-20240307
CLAUDE_ENABLED=true

# Redis (Optional - for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## 📁 Project Structure

```
ai-digital-forensics-system-complete/
├── backend/
│   ├── accounts/           # User authentication
│   │   ├── models.py       # User model (MongoDB)
│   │   ├── views.py        # Auth endpoints
│   │   ├── serializers.py  # DRF serializers
│   │   └── urls.py         # URL routing
│   ├── cases/              # Case management
│   ├── evidence/           # Evidence tracking
│   ├── analysis/           # AI analysis
│   │   ├── engine.py       # AI engine
│   │   ├── indicator_extractor.py
│   │   ├── summarizer.py
│   │   └── anomaly_detector.py
│   ├── devices/            # USB device detection
│   ├── texting/            # SMS functionality
│   ├── backend/            # Django configuration
│   ├── mongo_connection.py # MongoDB connection
│   ├── requirements.txt    # Python dependencies
│   └── tests/              # Test suite
│       ├── test_models.py
│       ├── test_ai_engine.py
│       ├── test_api.py
│       └── run_all_tests.py
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── api.js          # API client
│   │   ├── App.jsx         # Main app
│   │   └── index.css       # Styles
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite config
├── start_server.py         # Backend startup script
├── start_frontend.py       # Frontend startup script
└── README.md               # This file
```

---

## 🔧 Troubleshooting

### MongoDB Connection Issues

If you encounter MongoDB connection errors:

1. Check your MongoDB Atlas credentials
2. Ensure your IP is whitelisted in MongoDB Atlas
3. Verify the `MONGO_URI` in your `.env` file

### Frontend Not Loading

1. Ensure Node.js is installed: `node --version`
2. Clear npm cache: `npm cache clean --force`
3. Reinstall dependencies: `rm -rf node_modules && npm install`

### JWT Token Issues

If you get 401 errors:
1. Clear browser localStorage
2. Log in again to get fresh tokens

---

## 📄 License

This project is for educational and research purposes. Use responsibly.

---

## 🙏 Acknowledgments

- Django REST Framework
- MongoDB Atlas
- React Team
- Anthropic (Claude AI)
- Twilio
