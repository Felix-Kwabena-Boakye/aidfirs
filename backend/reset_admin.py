import os
import sys
import json
import hashlib
import uuid

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def hash_password(password):
    salt = str(uuid.uuid4())[:8]
    salted = f"{salt}{password}"
    return f"{salt}${hashlib.sha256(salted.encode()).hexdigest()}"

new_hash = hash_password("admin")

# 1. Update file
file_updated = False
try:
    with open("users.json", "r") as f:
        users = json.load(f)
    for u in users:
        if u.get("username") == "admin":
            u["password_hash"] = new_hash
            file_updated = True
    if file_updated:
        with open("users.json", "w") as f:
            json.dump(users, f, indent=2, default=str)
        print("Updated users.json successfully")
except Exception as e:
    print("Error updating users.json:", e)

# 2. Update Mongo
try:
    from mongo_connection import users_collection, MONGO_AVAILABLE
    if MONGO_AVAILABLE and users_collection is not None:
        result = users_collection.update_one(
            {"username": "admin"},
            {"$set": {"password_hash": new_hash}}
        )
        if result.matched_count > 0:
            print("Updated admin in MongoDB successfully")
        else:
            # Create it
            from accounts.models import User
            User.create_user(
                username='admin',
                email='admin@example.com',
                password='admin',
                role='admin',
                first_name='Admin',
                last_name='User',
                is_active=True
            )
            print("Created admin in MongoDB successfully")
    else:
        print("MongoDB not available")
except Exception as e:
    print("Error updating MongoDB:", e)

print("Admin password has been set to 'admin'.")
