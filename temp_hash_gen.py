import hashlib
import uuid
salt = str(uuid.uuid4())[:8]
salted = f"{salt}admin"
h = hashlib.sha256(salted.encode()).hexdigest()
print(f"New hash for admin/admin: {salt}${h}")
print(f"Copy the full hash: {salt}${h}")
