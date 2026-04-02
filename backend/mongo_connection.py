# mongo_connection.py

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

# You can temporarily set the URI here for testing (optional)
TEMP_MONGO_URI = "mongodb+srv://forensics_admin:StrongPassword123!@ai-forensics-cluster.osj874c.mongodb.net/?appName=ai-forensics-cluster"

MONGO_URI = os.getenv("MONGO_URI") or TEMP_MONGO_URI
DB_NAME = os.getenv("MONGO_DB_NAME", "ai_digital_forensics")

if not MONGO_URI:
    raise ValueError("MONGO_URI not found in environment variables or TEMP_MONGO_URI")

# --------------------------------------------------
# MongoDB Client Initialization
# --------------------------------------------------
try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        maxPoolSize=50,
        retryWrites=True
    )

    # Force connection check
    client.admin.command("ping")
    logger.info("Successfully connected to MongoDB Atlas")

except errors.ServerSelectionTimeoutError as err:
    logger.error("MongoDB connection timed out")
    raise err

except Exception as e:
    logger.error("MongoDB connection failed")
    raise e

# --------------------------------------------------
# Database Reference
# --------------------------------------------------
db = client[DB_NAME]

# --------------------------------------------------
# Collection References
# --------------------------------------------------
# User authentication (replacing Django's User model)
users_collection = db["users"]

# Cases collection
cases_collection = db["cases"]

# Evidence collection
evidence_collection = db["evidence"]

# Analysis results collection (already used by AI engine)
analysis_results_collection = db["analysis_results"]

# Audit logs collection
audit_logs_collection = db["audit_logs"]

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------

def get_database():
    """
    Returns the active MongoDB database instance.
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
    
    logger.info("Database indexes configured")

# Create indexes on startup
try:
    setup_indexes()
except Exception as e:
    logger.warning(f"Index setup note: {e}")
