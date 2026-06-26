#!/usr/bin/env python
"""
AIDFIRS Database Initialization Script
Configures MongoDB Atlas collections, default settings, and performance indexes (including full-text search indexes).
"""

import os
import sys
import logging
from pymongo import MongoClient, TEXT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DBInit")

# Set paths and environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mongo_connection import MONGO_URI, DB_NAME, MONGO_AVAILABLE

def safe_create_index(collection, keys, **kwargs):
    try:
        name = collection.create_index(keys, **kwargs)
        logger.info(f"Configured index '{name}' on '{collection.name}'.")
    except Exception as e:
        logger.warning(f"Note: Index skipped on '{collection.name}' for keys {keys}: {e}")

def main():
    logger.info("Initializing AIDFIRS Database...")
    logger.info(f"Target Database Name: {DB_NAME}")
    
    if not MONGO_AVAILABLE:
        logger.error("MongoDB is not available. Please verify your connection configuration in .env.")
        sys.exit(1)
        
    try:
        # Establish connection
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # List of required collections
        required_collections = [
            "users", "cases", "evidence", "analysis_results", 
            "audit_logs", "chain_of_custody", "timeline_events",
            "recovered_files", "metadata", "ai_reports", "system_settings"
        ]
        
        existing_cols = db.list_collection_names()
        logger.info(f"Existing collections: {existing_cols}")
        
        # Verify and create missing collections
        for col_name in required_collections:
            if col_name not in existing_cols:
                db.create_collection(col_name)
                logger.info(f"Created collection: '{col_name}'")
            else:
                logger.info(f"Collection '{col_name}' already exists.")
                
        # ----------------------------------------------------
        # Configure Core Performance Indexes
        # ----------------------------------------------------
        
        # 1. Users Indexes
        users = db["users"]
        safe_create_index(users, "email", unique=True, name="user_email_unique")
        safe_create_index(users, "username", unique=True, name="user_username_unique")
        safe_create_index(users, "role", name="user_role_index")
        
        # 2. Cases Indexes & Text Index for Search
        cases = db["cases"]
        safe_create_index(cases, "case_number", unique=True, name="case_number_unique")
        safe_create_index(cases, "investigator_id", name="case_investigator_idx")
        safe_create_index(cases, "status", name="case_status_idx")
        safe_create_index(cases, [
            ("title", TEXT),
            ("case_number", TEXT),
            ("description", TEXT),
            ("tags", TEXT)
        ], name="case_text_search_idx", weights={"title": 10, "case_number": 5, "description": 2, "tags": 1})
        
        # 3. Evidence Indexes & Text Index for Search
        evidence = db["evidence"]
        safe_create_index(evidence, "case_id", name="evidence_case_idx")
        safe_create_index(evidence, "hash_sha256", name="evidence_hash_idx")
        safe_create_index(evidence, "status", name="evidence_status_idx")
        safe_create_index(evidence, [
            ("file_name", TEXT),
            ("file_path", TEXT),
            ("description", TEXT),
            ("tags", TEXT)
        ], name="evidence_text_search_idx", weights={"file_name": 10, "file_path": 5, "description": 2, "tags": 1})
        
        # 4. Analysis Results Indexes
        analysis = db["analysis_results"]
        safe_create_index(analysis, "case_id", name="analysis_case_idx")
        safe_create_index(analysis, "evidence_id", name="analysis_evidence_idx")
        safe_create_index(analysis, "status", name="analysis_status_idx")
        safe_create_index(analysis, [
            ("analysis_type", TEXT),
            ("findings", TEXT),
            ("severity", TEXT),
            ("summaries", TEXT),
            ("recommendations", TEXT)
        ], name="analysis_text_search_idx", weights={"findings": 5, "summaries": 3, "recommendations": 2})
        
        # 5. Audit Logs Indexes
        audit_logs = db["audit_logs"]
        safe_create_index(audit_logs, "user_id", name="audit_user_idx")
        safe_create_index(audit_logs, "timestamp", name="audit_timestamp_idx")
        safe_create_index(audit_logs, "timestamp", expireAfterSeconds=90*24*60*60, name="audit_logs_ttl")
        
        # 6. Chain of Custody & Timeline Events
        safe_create_index(db["chain_of_custody"], "case_id", name="coc_case_idx")
        safe_create_index(db["chain_of_custody"], "evidence_id", name="coc_evidence_idx")
        safe_create_index(db["timeline_events"], "case_id", name="timeline_case_idx")
        safe_create_index(db["timeline_events"], "timestamp", name="timeline_timestamp_idx")
        
        logger.info("AIDFIRS database initialization completed successfully.")
        
    except Exception as e:
        logger.error(f"Error initializing AIDFIRS database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
