from datetime import datetime, timezone

from bson import ObjectId
import hashlib
import uuid
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, 'users.json')


class User:
    """
    MongoDB-based User model for authentication.
    """
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('investigator', 'Investigator'),
        ('analyst', 'Analyst'),
    ]
    
    def __init__(self, username, email, password_hash='', role='analyst',
                 first_name='', last_name='', is_active=True, is_staff=False,
                 date_joined=None, last_login=None, _id=None):
        self._id = _id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.is_active = is_active
        self.is_staff = is_staff
        self.date_joined = date_joined or datetime.now(timezone.utc)
        self.last_login = last_login
    
    @property
    def is_authenticated(self):
        """Required for Django REST Framework permissions."""
        return True
    
    @property
    def is_anonymous(self):
        """Required for Django REST Framework."""
        return False
    
    def get_username(self):
        """Required for Django auth."""
        return self.username
    
    @staticmethod
    def hash_password(password):
        """Hash password using SHA256 with salt."""
        salt = str(uuid.uuid4())[:8]
        salted = f"{salt}{password}"
        return f"{salt}${hashlib.sha256(salted.encode()).hexdigest()}"
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against hash."""
        try:
            salt, hashed = (password_hash or "").split('$')
            salted = f"{salt}{password}"
            return hashed == hashlib.sha256(salted.encode()).hexdigest()
        except Exception:
            return False

    
    @staticmethod
    def create_user(username, email, password, role='analyst', 
                    first_name='', last_name='', is_active=True):
        """
        Create a new user.
        """
        from mongo_connection import get_users_collection

        users_collection = get_users_collection()
        
        if users_collection is not None:

            if password is None:
                password_hash = ""
            else:
                password_hash = User.hash_password(password)

            existing = users_collection.find_one({



                "$or": [
                    {"username": username},
                    {"email": email}
                ]
            })
            
            if existing:
                raise ValueError("Username or email already exists")
            
            user_doc = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,

                "first_name": first_name,
                "last_name": last_name,
                "is_active": is_active,
                "is_staff": False,
                "date_joined": datetime.now(timezone.utc),
                "last_login": None
            }
            
            result = users_collection.insert_one(user_doc)
            user_doc["_id"] = result.inserted_id
            
            return User.from_dict(user_doc)
        else:
            # Fallback to local file-based storage
            users = []
            if os.path.exists(USERS_FILE):
                try:
                    with open(USERS_FILE, 'r') as f:
                        users = json.load(f)
                except Exception:
                    pass
            
            existing = any(u.get('username') == username or u.get('email') == email for u in users)
            if existing:
                raise ValueError("Username or email already exists")
            
            if password is None:
                password_hash = ""
            else:
                password_hash = User.hash_password(password)

            user_id = str(uuid.uuid4())
            user_doc = {
                "_id": user_id,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "first_name": first_name,
                "last_name": last_name,
                "is_active": is_active,
                "is_staff": False,
                "date_joined": datetime.now(timezone.utc).isoformat(),
                "last_login": None
            }
            
            users.append(user_doc)
            
            try:
                with open(USERS_FILE, 'w') as f:
                    json.dump(users, f, indent=2, default=str)
            except Exception as e:
                raise ValueError(f"Failed to write user database: {str(e)}")
            
            return User.from_dict(user_doc)
    
    @staticmethod
    def authenticate(username, password):
        """
        Authenticate user by username OR email and password.
        """
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        user_data = None
        if users_collection is not None:
            # Try username first, then email
            user_data = users_collection.find_one({"username": username})
            if not user_data:
                user_data = users_collection.find_one({"email": username})
        
        if not user_data and os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r') as f:
                    users = json.load(f)
                    # Try username match first, then email match
                    user_data = next((u for u in users if u.get('username') == username), None)
                    if not user_data:
                        user_data = next((u for u in users if u.get('email') == username), None)
            except Exception:
                pass

        if not user_data:
            return None
        
        user = User.from_dict(user_data)
        if not user.is_active:
            return None
        
        if User.verify_password(password, user.password_hash):
            return user
        
        return None
    
    @staticmethod
    def get_by_id(user_id):
        """
        Get user by ID with file-based fallback.
        """
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        if users_collection is not None:
            try:
                db_id = user_id
                if isinstance(db_id, str):
                    try:
                        db_id = ObjectId(db_id)
                    except Exception:
                        pass
                user_data = users_collection.find_one({"_id": db_id})
                if user_data:
                    return User.from_dict(user_data)
            except Exception:
                pass
        
        # Fallback to file
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r') as f:
                    users = json.load(f)
                    for u in users:
                        if str(u.get('_id')) == str(user_id):
                            return User.from_dict(u)
            except Exception:
                pass
        return None
    
    @staticmethod
    def get_by_username(username):
        """
        Get user by username with fallback to local file.
        """
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        user_data = None
        if users_collection is not None:
            try:
                user_data = users_collection.find_one({"username": username})
            except Exception:
                pass
        
        if not user_data and os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r') as f:
                    users = json.load(f)
                    user_data = next((u for u in users if u.get('username') == username), None)
            except Exception:
                pass

        if user_data:
            return User.from_dict(user_data)
        return None

    @staticmethod
    def get_by_email(email):
        """
        Get user by email with fallback to local file.
        """
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        user_data = None
        if users_collection is not None:
            try:
                user_data = users_collection.find_one({"email": email})
            except Exception:
                pass
        
        if not user_data and os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r') as f:
                    users = json.load(f)
                    user_data = next((u for u in users if u.get('email') == email), None)
            except Exception:
                pass

        if user_data:
            return User.from_dict(user_data)
        return None
    
    @staticmethod
    def get_all():
        """
        Get all users with fallback to local file.
        """
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        if users_collection is not None:
            try:
                users = list(users_collection.find())
                return [User.from_dict(u) for u in users]
            except Exception:
                pass
        
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r') as f:
                    users_data = json.load(f)
                    return [User.from_dict(u) for u in users_data]
            except Exception:
                pass
        return []
    
    def save(self):
        """
        Update user in MongoDB or local file.
        """
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        
        db_id = self._id
        if isinstance(db_id, str):
            try:
                db_id = ObjectId(db_id)
            except Exception:
                pass

        if users_collection is not None:
            try:
                result = users_collection.update_one(
                    {"_id": db_id},
                    {"$set": {
                        "username": self.username,
                        "email": self.email,
                        "password_hash": self.password_hash,
                        "role": self.role,
                        "first_name": self.first_name,
                        "last_name": self.last_name,
                        "is_active": self.is_active,
                        "is_staff": self.is_staff,
                        "date_joined": self.date_joined,
                        "last_login": self.last_login
                    }}
                )
                if result.matched_count == 0 and isinstance(db_id, ObjectId):
                    users_collection.update_one(
                        {"_id": str(self._id)},
                        {"$set": {
                            "username": self.username,
                            "email": self.email,
                            "password_hash": self.password_hash,
                            "role": self.role,
                            "first_name": self.first_name,
                            "last_name": self.last_name,
                            "is_active": self.is_active,
                            "is_staff": self.is_staff,
                            "date_joined": self.date_joined,
                            "last_login": self.last_login
                        }}
                    )
                return
            except Exception:
                pass
        
        # File fallback
        try:
            users = []
            if os.path.exists(USERS_FILE):
                try:
                    with open(USERS_FILE, 'r') as f:
                        users = json.load(f)
                except Exception:
                    pass
            
            found = False
            for i, u in enumerate(users):
                if str(u.get('_id')) == str(self._id):
                    users[i] = self.to_dict()
                    found = True
                    break
            
            if not found:
                users.append(self.to_dict())
            
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, indent=2, default=str)
        except Exception:
            pass
    
    def update_last_login(self):
        """
        Update last login timestamp in MongoDB or local file.
        """
        self.last_login = datetime.now(timezone.utc)
        from mongo_connection import get_users_collection
        users_collection = get_users_collection()
        
        db_id = self._id
        if isinstance(db_id, str):
            try:
                db_id = ObjectId(db_id)
            except Exception:
                pass

        if users_collection is not None:
            try:
                result = users_collection.update_one(
                    {"_id": db_id},
                    {"$set": {"last_login": self.last_login}}
                )
                if result.matched_count == 0 and isinstance(db_id, ObjectId):
                    users_collection.update_one(
                        {"_id": str(self._id)},
                        {"$set": {"last_login": self.last_login}}
                    )
                return
            except Exception:
                pass
        
        # File fallback
        self.save()
    
    @staticmethod
    def from_dict(data):
        """
        Create User instance from dictionary.
        """
        date_joined = data.get('date_joined')
        if isinstance(date_joined, str):
            try:
                date_joined = datetime.fromisoformat(date_joined.replace('Z', '+00:00'))
            except Exception:
                pass
                
        last_login = data.get('last_login')
        if isinstance(last_login, str):
            try:
                last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            except Exception:
                pass

        return User(
            _id=data.get('_id'),
            username=data.get('username'),
            email=data.get('email'),
            password_hash=data.get('password_hash', ''),
            role=data.get('role', 'analyst'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_active=data.get('is_active', True),
            is_staff=data.get('is_staff', False),
            date_joined=date_joined,
            last_login=last_login
        )
    
    def to_dict(self):
        """
        Convert User to dictionary.
        """
        date_joined_val = self.date_joined
        if isinstance(date_joined_val, datetime):
            date_joined_val = date_joined_val.isoformat()
        
        last_login_val = self.last_login
        if isinstance(last_login_val, datetime):
            last_login_val = last_login_val.isoformat()

        return {
            "_id": str(self._id) if self._id else None,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "is_staff": self.is_staff,
            "date_joined": date_joined_val,
            "last_login": last_login_val
        }
    
    def __str__(self):
        return f"{self.username} ({self.role})"


class AuditLog:
    """
    Audit log model for tracking user actions.
    """
    
    @staticmethod
    def log(user_id, username, action, resource_type, resource_id, details=None):
        """
        Log a user action.
        """
        try:
            from mongo_connection import get_audit_logs_collection
            audit_collection = get_audit_logs_collection()
            
            log_entry = {
                "user_id": user_id,
                "username": username,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "timestamp": datetime.now(timezone.utc),
                "ip_address": None
            }
            
            audit_collection.insert_one(log_entry)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_logs(user_id=None, limit=100):
        """
        Get audit logs, optionally filtered by user.
        """
        try:
            from mongo_connection import get_audit_logs_collection
            audit_collection = get_audit_logs_collection()
            
            query = {}
            if user_id:
                query["user_id"] = user_id
            
            logs = audit_collection.find(query).sort("timestamp", -1).limit(limit)
            return list(logs)
        except Exception:
            return []
    
    @staticmethod
    def get_all_logs(limit=500):
        """
        Get all audit logs (admin only).
        """
        try:
            from mongo_connection import get_audit_logs_collection
            audit_collection = get_audit_logs_collection()
            
            logs = audit_collection.find().sort("timestamp", -1).limit(limit)
            return list(logs)
        except Exception:
            return []
