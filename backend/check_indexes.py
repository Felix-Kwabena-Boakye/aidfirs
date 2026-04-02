from mongo_connection import evidence_collection
import json

def check_indexes():
    print("Checking indexes on 'evidence' collection...")
    try:
        indexes = list(evidence_collection.list_indexes())
        for idx in indexes:
            print(json.dumps(idx, indent=2))
    except Exception as e:
        print(f"Failed to list indexes: {e}")

if __name__ == "__main__":
    check_indexes()
