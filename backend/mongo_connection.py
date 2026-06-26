from pymongo import MongoClient, errors
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import certifi
import logging

# --------------------------------------------------
# Logging Configuration
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MongoDB")

# --------------------------------------------------
# Load Environment Variables from .env file
# --------------------------------------------------
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "ai_digital_forensics")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not configured.")

# --------------------------------------------------
# MongoDB Client Initialization (Dynamic Connection Mode)
# --------------------------------------------------
MONGO_AVAILABLE = False
client = None

try:
    # Read settings from environment
    allow_invalid_certs = os.getenv("MONGO_TLS_ALLOW_INVALID_CERTIFICATES", "true").lower() == "true"
    
    # Try first attempt (SSL/TLS with certificate validation)
    logger.info("Attempting MongoDB connection with SSL/TLS verification...")
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    MONGO_AVAILABLE = True
    logger.info("MongoDB connection established successfully with SSL/TLS verification.")
except Exception as e:
    logger.warning(f"MongoDB connection with SSL/TLS verification failed: {e}.")
    try:
        # Fallback 1: Lax TLS verification
        logger.info("Retrying MongoDB connection with lax verification (tlsAllowInvalidCertificates=True)...")
        client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        MONGO_AVAILABLE = True
        logger.info("MongoDB connection established successfully (SSL/TLS verification bypassed).")
    except Exception as e2:
        logger.warning(f"MongoDB connection with tlsAllowInvalidCertificates failed: {e2}.")
        try:
            # Fallback 2: Direct connection without SSL/TLS parameter
            logger.info("Retrying MongoDB connection without SSL/TLS...")
            client = MongoClient(MONGO_URI, ssl=False, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            MONGO_AVAILABLE = True
            logger.info("MongoDB connection established successfully without SSL/TLS.")
        except Exception as e3:
            MONGO_AVAILABLE = False
            client = None
            logger.error(f"All MongoDB connection attempts failed. Last error: {e3}. Entering hybrid-bypass mode.")

# --------------------------------------------------
# Database Reference
# --------------------------------------------------
if MONGO_AVAILABLE:
    db = client[DB_NAME]
else:
    db = None

# --------------------------------------------------
# Collection References
# --------------------------------------------------
# User authentication (replacing Django's User model)
users_collection = db["users"] if MONGO_AVAILABLE else None

# Cases collection
cases_collection = db["cases"] if MONGO_AVAILABLE else None

# Evidence collection
evidence_collection = db["evidence"] if MONGO_AVAILABLE else None

# Analysis results collection (already used by AI engine)
analysis_results_collection = db["analysis_results"] if MONGO_AVAILABLE else None

# Audit logs collection
audit_logs_collection = db["audit_logs"] if MONGO_AVAILABLE else None

# Chain of custody collection
chain_of_custody_collection = db["chain_of_custody"] if MONGO_AVAILABLE else None

# Timeline events collection
timeline_events_collection = db["timeline_events"] if MONGO_AVAILABLE else None

# AI Models collection for ML models
ai_models_collection = db["ai_models"] if MONGO_AVAILABLE else None

# New collections for AIDFIRS platform refactoring
recovered_files_collection = db["recovered_files"] if MONGO_AVAILABLE else None
metadata_collection = db["metadata"] if MONGO_AVAILABLE else None
ai_reports_collection = db["ai_reports"] if MONGO_AVAILABLE else None
system_settings_collection = db["system_settings"] if MONGO_AVAILABLE else None


# --------------------------------------------------
# Utility Functions
# --------------------------------------------------

def get_database():
    """
    Returns the active MongoDB database instance.
    """
    return db


def get_db():
    """
    Returns the database (alias for get_database).
    """
    return db


def get_collection(name):
    """
    Returns a MongoDB collection by name.
    """
    return db[name]


def get_users_collection():
    """
    Returns the users collection.
    """
    return users_collection


def get_cases_collection():
    """
    Returns the cases collection.
    """
    return cases_collection


def get_evidence_collection():
    """
    Returns the evidence collection.
    """
    return evidence_collection


def get_analysis_results_collection():
    """
    Returns the analysis results collection.
    """
    return analysis_results_collection


def get_audit_logs_collection():
    """
    Returns the audit logs collection.
    """
    return audit_logs_collection


def get_chain_of_custody_collection():
    """
    Returns the chain of custody collection.
    """
    return chain_of_custody_collection


def get_timeline_events_collection():
    """
    Returns the timeline events collection.
    """
    return timeline_events_collection


def get_ai_models_collection():
    """
    Returns the ai_models collection.
    """
    return ai_models_collection


def get_recovered_files_collection():
    """
    Returns the recovered_files collection.
    """
    return recovered_files_collection


def get_metadata_collection():
    """
    Returns the metadata collection.
    """
    return metadata_collection


def get_ai_reports_collection():
    """
    Returns the ai_reports collection.
    """
    return ai_reports_collection


def get_system_settings_collection():
    """
    Returns the system_settings collection.
    """
    return system_settings_collection



def health_check():
    """
    Checks if MongoDB is reachable.
    """
    try:
        client.admin.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def close_connection():
    """
    Gracefully closes MongoDB connection.
    """
    client.close()
    logger.info("MongoDB connection closed")


# --------------------------------------------------
# Index Creation for Performance
# --------------------------------------------------
def setup_indexes():
    """
    Create indexes for better query performance.
    """
    if not MONGO_AVAILABLE or users_collection is None:
        return
    # Users indexes - use unique index names to avoid conflicts
    try:
        users_collection.create_index("email", unique=True, name="user_email_idx")
    except Exception as e:
        logger.debug(f"Users email index note: {e}")
    
    try:
        users_collection.create_index("username", unique=True, name="user_username_idx")
    except Exception as e:
        logger.debug(f"Users username index note: {e}")
    
    try:
        # Cases indexes
        cases_collection.create_index("case_number", unique=True, name="case_number_idx")
    except Exception as e:
        logger.debug(f"Cases index note: {e}")
    
    try:
        cases_collection.create_index("investigator_id", name="case_investigator_idx")
    except Exception as e:
        logger.debug(f"Cases investigator index note: {e}")
    
    try:
        cases_collection.create_index("status", name="case_status_idx")
    except Exception as e:
        logger.debug(f"Cases status index note: {e}")
    
    try:
        # Evidence indexes
        evidence_collection.create_index("case_id", name="evidence_case_idx")
    except Exception as e:
        logger.debug(f"Evidence case index note: {e}")
    
    try:
        evidence_collection.create_index("hash_sha256", name="evidence_hash_idx")
    except Exception as e:
        logger.debug(f"Evidence hash index note: {e}")
    
    try:
        evidence_collection.create_index("status", name="evidence_status_idx")
    except Exception as e:
        logger.debug(f"Evidence status index note: {e}")
    
    try:
        # Analysis indexes
        analysis_results_collection.create_index("case_id", name="analysis_case_idx")
    except Exception as e:
        logger.debug(f"Analysis case index note: {e}")
    
    try:
        analysis_results_collection.create_index("evidence_id", name="analysis_evidence_idx")
    except Exception as e:
        logger.debug(f"Analysis evidence index note: {e}")
    
    try:
        analysis_results_collection.create_index("status", name="analysis_status_idx")
    except Exception as e:
        logger.debug(f"Analysis status index note: {e}")
    
    try:
        if ai_models_collection is not None:
            ai_models_collection.create_index("model_name", unique=True, name="model_name_idx")
    except Exception as e:
        logger.debug(f"AI Models index note: {e}")
    
    try:
        if chain_of_custody_collection is not None:
            chain_of_custody_collection.create_index("case_id", name="coc_case_idx")
            chain_of_custody_collection.create_index("evidence_id", name="coc_evidence_idx")
    except Exception as e:
        logger.debug(f"Chain of Custody index note: {e}")
    
    try:
        if timeline_events_collection is not None:
            timeline_events_collection.create_index("case_id", name="timeline_case_idx")
            timeline_events_collection.create_index("timestamp", name="timeline_timestamp_idx")
    except Exception as e:
        logger.debug(f"Timeline events index note: {e}")
        
    logger.info("Database indexes configured")

# Create indexes on startup
try:
    setup_indexes()
except Exception as e:
    logger.warning(f"Index setup note: {e}")

