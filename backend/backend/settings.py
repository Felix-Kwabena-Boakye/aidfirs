import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


# =========================
# SECURITY
# =========================

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is not set."
    )

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0,aidfirs.onrender.com"
).split(",")


# =========================
# APPLICATIONS
# =========================

INSTALLED_APPS = [

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",

    "corsheaders",

    "accounts",
    "cases",
    "evidence",
    "analysis",
    "devices",
    "recovery.apps.RecoveryConfig",
    "reports.apps.ReportsConfig",
]


# =========================
# MIDDLEWARE
# =========================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "accounts.middleware.AuditTrailMiddleware",
]


ROOT_URLCONF = "backend.urls"


# =========================
# TEMPLATES
# =========================

TEMPLATES = [

    {
        "BACKEND":
        "django.template.backends.django.DjangoTemplates",

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {

            "context_processors": [

                "django.template.context_processors.debug",

                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",

            ],

        },
    },
]


WSGI_APPLICATION = "backend.wsgi.application"



# =========================
# DATABASE
# =========================
# Django internal database
# MongoDB is handled separately through pymongo

DATABASES = {

    "default": {

        "ENGINE":
        "django.db.backends.sqlite3",

        "NAME":
        BASE_DIR / "db.sqlite3",

    }
}



# =========================
# STATIC FILES
# =========================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


STORAGES = {

    "default": {

        "BACKEND":
        "django.core.files.storage.FileSystemStorage",

    },

    "staticfiles": {

        "BACKEND":
        "whitenoise.storage.CompressedStaticFilesStorage",

    },

}



# =========================
# REST FRAMEWORK
# =========================

REST_FRAMEWORK = {


    "DEFAULT_AUTHENTICATION_CLASSES": (

        "accounts.authentication.MongoJWTAuthentication",

    ),


    "DEFAULT_PERMISSION_CLASSES": (

        "rest_framework.permissions.IsAuthenticated",

    ),


    "EXCEPTION_HANDLER":

        "backend.exceptions.custom_exception_handler",

}



# =========================
# CORS
# =========================

CORS_ALLOWED_ORIGINS = os.getenv(

    "CORS_ALLOWED_ORIGINS",

    "https://aidfirs.netlify.app,http://localhost:5173,http://127.0.0.1:5173"

).split(",")


CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_CREDENTIALS = True



CSRF_TRUSTED_ORIGINS = [

    "https://aidfirs.netlify.app",

    "https://aidfirs.onrender.com",

    "http://localhost:5173",

    "http://127.0.0.1:5173",

]



# =========================
# CELERY
# =========================

CELERY_BROKER_URL = os.getenv(
    "REDIS_URL",
    ""
)


CELERY_RESULT_BACKEND = os.getenv(
    "REDIS_URL",
    ""
)


CELERY_ACCEPT_CONTENT = [
    "json"
]


CELERY_TASK_SERIALIZER = "json"


CELERY_RESULT_SERIALIZER = "json"


CELERY_TIMEZONE = "UTC"



# =========================
# SECURITY HEADERS
# =========================

SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG


SECURE_SSL_REDIRECT = False


SECURE_REFERRER_POLICY = "same-origin"


SECURE_CONTENT_TYPE_NOSNIFF = True


X_FRAME_OPTIONS = "DENY"



SECURE_HSTS_SECONDS = (

    31536000 if not DEBUG else 0

)


SECURE_HSTS_INCLUDE_SUBDOMAINS = True


SECURE_HSTS_PRELOAD = True



# =========================
# CONTENT SECURITY POLICY
# =========================

CSP_DEFAULT_SRC = (
    "'self'",
)


CSP_SCRIPT_SRC = (
    "'self'",
)


CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
)


CSP_IMG_SRC = (

    "'self'",

    "data:",

    "https:",

)


CSP_FONT_SRC = (

    "'self'",

)


CSP_CONNECT_SRC = (

    "'self'",

    "https://aidfirs.onrender.com",

    "http://localhost:8000",

    "http://127.0.0.1:8000",

)



CSP_FRAME_ANCESTORS = (

    "'none'",

)



CSP_BASE_URI = (

    "'self'",

)



CSP_FORM_ACTION = (

    "'self'",

)



# =========================
# CLAUDE AI
# =========================

ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY"
)


CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-3-5-sonnet-20240620"
)


CLAUDE_ENABLED = os.getenv(
    "CLAUDE_ENABLED",
    "true"
).lower() == "true"




# =========================
# GOOGLE OAUTH
# =========================

GOOGLE_OAUTH_CLIENT_ID = os.getenv(
    "GOOGLE_OAUTH_CLIENT_ID",
    ""
)


GOOGLE_OAUTH_CLIENT_SECRET = os.getenv(
    "GOOGLE_OAUTH_CLIENT_SECRET",
    ""
)


GOOGLE_OAUTH_REDIRECT_URI = os.getenv(

    "GOOGLE_OAUTH_REDIRECT_URI",

    "https://aidfirs.onrender.com/accounts/google/login/callback/"

)




# =========================
# EMAIL SETTINGS
# =========================

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "smtp.gmail.com"
)


EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "587"
    )
)


EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    ""
)


EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    ""
)


DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER
)



EMAIL_RESET_URL_BASE = os.getenv(

    "EMAIL_RESET_URL_BASE",

    "https://aidfirs.netlify.app/reset-password"

)


# =========================
# FILE STORAGE SETTINGS
# =========================

# Maximum upload size: 2GB for forensic images
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024

# Storage paths
RECOVERY_STORAGE_ROOT = os.path.join(BASE_DIR, 'storage', 'recoveries')
REPORTS_STORAGE_ROOT = os.path.join(BASE_DIR, 'storage', 'reports')

# Ensure storage directories exist
os.makedirs(RECOVERY_STORAGE_ROOT, exist_ok=True)
os.makedirs(REPORTS_STORAGE_ROOT, exist_ok=True)
