from mongo_connection import users_collection
from datetime import datetime, timezone
from bson import ObjectId
import hashlib
import uuid


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
            salt, hashed = password_hash.split('$')
            salted = f"{salt}{password}"
            return hashed == hashlib.sha256(salted.encode()).hexdigest()
        except:
            return False
    
    @staticmethod
    def create_user(username, email, password, role='analyst', 
                    first_name='', last_name='', is_active=True):
        """
        Create a new user.
        """
        # Check if user already exists
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
            "password_hash": User.hash_password(password),
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
    
    @staticmethod
    def authenticate(username, password):
        """
        Authenticate user by username and password.
        """
        user_data = users_collection.find_one({"username": username})
        
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
        Get user by ID.
        """
        try:
            user_data = users_collection.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return User.from_dict(user_data)
        except:
            pass
        return None
    
    @staticmethod
    def get_by_username(username):
        """
        Get user by username.
        """
        user_data = users_collection.find_one({"username": username})
        if user_data:
            return User.from_dict(user_data)
        return None
    
    @staticmethod
    def get_all():
        """
        Get all users.
        """
        users = users_collection.find()
        return [User.from_dict(u) for u in users]
    
    def save(self):
        """
        Update user in MongoDB.
        """
        users_collection.update_one(
            {"_id": self._id},
            {"$set": {
                "username": self.username,
                "email": self.email,
                "role": self.role,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "is_active": self.is_active,
                "is_staff": self.is_staff,
                "last_login": self.last_login
            }}
        )
    
    def update_last_login(self):
        """
        Update last login timestamp.
        """
        self.last_login = datetime.now(timezone.utc)
        users_collection.update_one(
            {"_id": self._id},
            {"$set": {"last_login": self.last_login}}
        )
    
    @staticmethod
    def from_dict(data):
        """
        Create User instance from dictionary.
        """
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
            date_joined=data.get('date_joined'),
            last_login=data.get('last_login')
        )
    
    def to_dict(self):
        """
        Convert User to dictionary.
        """
        return {
            "_id": str(self._id) if self._id else None,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "is_staff": self.is_staff,
            "date_joined": self.date_joined.isoformat() if self.date_joined else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
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
