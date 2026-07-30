"""
MongoDB Migration Script: Fix Evidence hash_sha256 Index & Remove Null Hashes

This script:
1. Connects to MongoDB database.
2. Removes any existing null/empty hash_sha256 fields from the evidence collection.
3. Drops legacy non-partial unique indexes ("hash_sha256_1", "evidence_hash_idx").
4. Creates a partial unique index on hash_sha256 matching only string values.
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IndexMigration")

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def run_migration():
    from mongo_connection import evidence_collection, MONGO_AVAILABLE

    if not MONGO_AVAILABLE or evidence_collection is None:
        logger.error("MongoDB is not available. Please verify connection settings.")
        return False

    logger.info("Starting MongoDB Evidence Index Migration...")

    # Step 1: Remove null or empty string hash_sha256 fields
    result = evidence_collection.update_many(
        {"$or": [{"hash_sha256": None}, {"hash_sha256": ""}]},
        {"$unset": {"hash_sha256": ""}}
    )
    logger.info(f"Unset null/empty hash_sha256 fields in {result.modified_count} document(s).")

    # Step 2: Drop legacy indexes
    existing_indexes = evidence_collection.index_information()
    logger.info(f"Existing indexes: {list(existing_indexes.keys())}")

    indexes_to_drop = ["hash_sha256_1", "evidence_hash_idx"]
    for idx_name in indexes_to_drop:
        if idx_name in existing_indexes:
            try:
                evidence_collection.drop_index(idx_name)
                logger.info(f"Successfully dropped old index: '{idx_name}'")
            except Exception as e:
                logger.warning(f"Note dropping index '{idx_name}': {e}")

    # Step 3: Create partial unique index
    try:
        evidence_collection.create_index(
            [("hash_sha256", 1)],
            name="evidence_hash_sha256_partial_idx",
            unique=True,
            partialFilterExpression={"hash_sha256": {"$type": "string"}}
        )
        logger.info("Successfully created partial unique index on evidence.hash_sha256.")
    except Exception as e:
        logger.error(f"Failed to create partial unique index: {e}")
        return False

    updated_indexes = evidence_collection.index_information()
    logger.info(f"Updated indexes: {list(updated_indexes.keys())}")
    logger.info("Migration completed successfully.")
    return True

if __name__ == "__main__":
    run_migration()
