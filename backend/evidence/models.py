from mongo_connection import evidence_collection
from datetime import datetime, timezone
from bson import ObjectId
import hashlib
import uuid
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_FILE = os.path.join(BASE_DIR, 'evidence.json')

class Evidence:
    """
    MongoDB-based Evidence model for digital forensics.
    """
    
    STATUS_CHOICES = [
        ('collected', 'Collected'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('archived', 'Archived')
    ]
    
    EVIDENCE_TYPE_CHOICES = [
        ('file', 'File'),
        ('disk_image', 'Disk Image'),
        ('memory_dump', 'Memory Dump'),
        ('network_capture', 'Network Capture'),
        ('log_file', 'Log File'),
        ('registry', 'Registry'),
        ('email', 'Email'),
        ('other', 'Other')
    ]
    
    def __init__(self, case_id, evidence_type, file_name, file_path,
                 file_size=0, hash_md5='', hash_sha1='', hash_sha256='',
                 description='', collector_id='', status='collected',
                 collected_at=None, analyzed_at=None, tags=None, metadata=None, _id=None):
        self._id = _id
        self.case_id = case_id
        self.evidence_type = evidence_type
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size
        self.hash_md5 = hash_md5
        self.hash_sha1 = hash_sha1
        self.hash_sha256 = hash_sha256
        self.description = description
        self.collector_id = collector_id
        self.status = status
        self.collected_at = collected_at or datetime.now(timezone.utc)
        self.analyzed_at = analyzed_at
        self.tags = tags or []
        self.metadata = metadata or {}
    
    @property
    def EvidenceID(self):
        """Alias for _id as per ER diagram."""
        return str(self._id) if self._id else None

    @property
    def hash(self):
        """Alias for hash_sha256 as per ER diagram."""
        return self.hash_sha256

    @hash.setter
    def hash(self, value):
        self.hash_sha256 = value
    
    @staticmethod
    def compute_hashes(file_path):
        """
        Compute MD5, SHA1, SHA256 hashes for a file.
        """
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
                    sha1_hash.update(chunk)
                    sha256_hash.update(chunk)
            
            return {
                'md5': md5_hash.hexdigest(),
                'sha1': sha1_hash.hexdigest(),
                'sha256': sha256_hash.hexdigest()
            }
        except Exception as e:
            # Generate unique placeholder hashes when file doesn't exist
            unique_id = str(uuid.uuid4())
            return {
                'md5': f'placeholder_{unique_id}',
                'sha1': f'placeholder_{unique_id}',
                'sha256': f'placeholder_{unique_id}'
            }
    
    @staticmethod
    def create(case_id, evidence_type, file_name, file_path,
               collector_id='', description='', file_size=0):
        """
        Create new evidence in MongoDB.
        """
        # Compute hashes or generate unique placeholders
        if file_path:
            hashes = Evidence.compute_hashes(file_path)
        else:
            # Generate unique placeholder hashes for manual entries without files
            unique_id = str(uuid.uuid4())
            hashes = {
                'md5': f'manual_md5_{unique_id}',
                'sha1': f'manual_sha1_{unique_id}',
                'sha256': f'manual_sha256_{unique_id}'
            }
        
        evidence_doc = {
            "case_id": case_id,
            "evidence_type": evidence_type,
            "file_name": file_name,
            "file_path": file_path,
            "file_size": file_size,
            "hash_md5": hashes['md5'],
            "hash_sha1": hashes['sha1'],
            "hash_sha256": hashes['sha256'],
            "description": description,
            "collector_id": collector_id,
            "status": "collected",
            "collected_at": datetime.now(timezone.utc),
            "analyzed_at": None,
            "tags": [],
            "metadata": {}
        }
        
        if evidence_collection is not None:
            result = evidence_collection.insert_one(evidence_doc)
            evidence_doc["_id"] = result.inserted_id
        else:

            evidence_doc["_id"] = str(uuid.uuid4())
            evidence_data = []
            if os.path.exists(EVIDENCE_FILE):
                try:
                    with open(EVIDENCE_FILE, 'r') as f:
                        evidence_data = json.load(f)
                except:
                    pass
            evidence_data.append(evidence_doc)
            with open(EVIDENCE_FILE, 'w') as f:
                json.dump(evidence_data, f, indent=2, default=str)
        
        return Evidence.from_dict(evidence_doc)
    
    @staticmethod
    def get_by_id(evidence_id):
        """
        Get evidence by ID.
        """
        if evidence_collection is not None:
            try:
                evidence_data = evidence_collection.find_one({"_id": ObjectId(evidence_id)})
                if evidence_data:
                    return Evidence.from_dict(evidence_data)
            except Exception:
                pass
                
        if os.path.exists(EVIDENCE_FILE):
            try:
                with open(EVIDENCE_FILE, 'r') as f:
                    evidence_data = json.load(f)
                    for e in evidence_data:
                        if str(e.get('_id')) == str(evidence_id):
                            return Evidence.from_dict(e)
            except:
                pass
        return None
    
    @staticmethod
    def get_all():
        """
        Get all evidence.
        """
        if evidence_collection is not None:
            try:
                evidence_list = evidence_collection.find().sort("collected_at", -1)
                return [Evidence.from_dict(e) for e in evidence_list]
            except:
                pass
                
        if os.path.exists(EVIDENCE_FILE):
            try:
                with open(EVIDENCE_FILE, 'r') as f:
                    evidence_data = json.load(f)
                    evidence_data.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
                    return [Evidence.from_dict(e) for e in evidence_data]
            except:
                pass
        return []
    
    @staticmethod
    def get_by_case(case_id):
        """
        Get all evidence for a specific case.
        """
        if evidence_collection is not None:
            try:
                evidence_list = evidence_collection.find({"case_id": case_id}).sort("collected_at", -1)
                return [Evidence.from_dict(e) for e in evidence_list]
            except:
                pass
                
        if os.path.exists(EVIDENCE_FILE):
            try:
                with open(EVIDENCE_FILE, 'r') as f:
                    evidence_data = json.load(f)
                    filtered = [e for e in evidence_data if str(e.get('case_id')) == str(case_id)]
                    filtered.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
                    return [Evidence.from_dict(e) for e in filtered]
            except:
                pass
        return []
    
    @staticmethod
    def get_by_hash(hash_value):
        """
        Find evidence by any hash value.
        """
        if evidence_collection is not None:
            try:
                evidence_data = evidence_collection.find_one({
                    "$or": [
                        {"hash_md5": hash_value},
                        {"hash_sha1": hash_value},
                        {"hash_sha256": hash_value}
                    ]
                })
                if evidence_data:
                    return Evidence.from_dict(evidence_data)
            except:
                pass
                
        if os.path.exists(EVIDENCE_FILE):
            try:
                with open(EVIDENCE_FILE, 'r') as f:
                    evidence_data = json.load(f)
                    for e in evidence_data:
                        if hash_value in (e.get('hash_md5'), e.get('hash_sha1'), e.get('hash_sha256')):
                            return Evidence.from_dict(e)
            except:
                pass
        return None
    
    def update(self, **kwargs):
        """
        Update evidence fields.
        """
        # Don't update _id
        update_data = {k: v for k, v in kwargs.items() if k != '_id'}
        
        if evidence_collection is not None:
            try:
                evidence_collection.update_one(
                    {"_id": self._id},
                    {"$set": update_data}
                )
            except:
                pass
        else:
            if os.path.exists(EVIDENCE_FILE):
                try:
                    with open(EVIDENCE_FILE, 'r') as f:
                        evidence_data = json.load(f)
                    for e in evidence_data:
                        if str(e.get('_id')) == str(self._id):
                            for k, v in update_data.items():
                                e[k] = v.isoformat() if isinstance(v, datetime) else v
                            break
                    with open(EVIDENCE_FILE, 'w') as f:
                        json.dump(evidence_data, f, indent=2, default=str)
                except:
                    pass
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        return self

    def save(self):
        """
        Save current evidence state to MongoDB.
        """
        update_data = self.to_dict()
        if '_id' in update_data:
            del update_data['_id']
        
        if evidence_collection is not None:
            try:
                evidence_collection.update_one(
                    {"_id": self._id},
                    {"$set": update_data}
                )
            except:
                pass
        else:
            if os.path.exists(EVIDENCE_FILE):
                try:
                    with open(EVIDENCE_FILE, 'r') as f:
                        evidence_data = json.load(f)
                    for i, e in enumerate(evidence_data):
                        if str(e.get('_id')) == str(self._id):
                            updated = self.to_dict()
                            updated['_id'] = str(self._id)
                            evidence_data[i] = updated
                            break
                    with open(EVIDENCE_FILE, 'w') as f:
                        json.dump(evidence_data, f, indent=2, default=str)
                except:
                    pass
        return self
    
    def mark_analyzed(self):
        """
        Mark evidence as analyzed.
        """
        return self.update(status='analyzed', analyzed_at=datetime.now(timezone.utc))
    
    def add_tag(self, tag):
        """
        Add a tag to evidence.
        """
        if evidence_collection is not None:
            try:
                evidence_collection.update_one(
                    {"_id": self._id},
                    {"$addToSet": {"tags": tag}}
                )
            except:
                pass
        else:
            if tag not in self.tags:
                self.tags.append(tag)
                self.save()
                return self
        
        if tag not in self.tags:
            self.tags.append(tag)
        return self
    
    def add_metadata(self, key, value):
        """
        Add metadata to evidence.
        """
        if evidence_collection is not None:
            try:
                evidence_collection.update_one(
                    {"_id": self._id},
                    {"$set": {f"metadata.{key}": value}}
                )
            except:
                pass
        
        self.metadata[key] = value
        if evidence_collection is None:
            self.save()
        return self
    
    def delete(self):
        """
        Delete evidence from MongoDB.
        """
        if evidence_collection is not None:
            try:
                evidence_collection.delete_one({"_id": self._id})
            except:
                pass
        else:
            if os.path.exists(EVIDENCE_FILE):
                try:
                    with open(EVIDENCE_FILE, 'r') as f:
                        evidence_data = json.load(f)
                    evidence_data = [e for e in evidence_data if str(e.get('_id')) != str(self._id)]
                    with open(EVIDENCE_FILE, 'w') as f:
                        json.dump(evidence_data, f, indent=2, default=str)
                except:
                    pass
    
    @staticmethod
    def from_dict(data):
        """
        Create Evidence instance from dictionary.
        """
        collected_at = data.get('collected_at')
        if isinstance(collected_at, str):
            try:
                collected_at = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
            except:
                pass
                
        analyzed_at = data.get('analyzed_at')
        if isinstance(analyzed_at, str):
            try:
                analyzed_at = datetime.fromisoformat(analyzed_at.replace('Z', '+00:00'))
            except:
                pass

        return Evidence(
            _id=data.get('_id'),
            case_id=data.get('case_id'),
            evidence_type=data.get('evidence_type'),
            file_name=data.get('file_name'),
            file_path=data.get('file_path'),
            file_size=data.get('file_size', 0),
            hash_md5=data.get('hash_md5', ''),
            hash_sha1=data.get('hash_sha1', ''),
            hash_sha256=data.get('hash_sha256', ''),
            description=data.get('description', ''),
            collector_id=data.get('collector_id', ''),
            status=data.get('status', 'collected'),
            collected_at=collected_at,
            analyzed_at=analyzed_at,
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )
    
    def to_dict(self):
        """
        Convert Evidence to dictionary.
        """
        return {
            "_id": str(self._id) if self._id else None,
            "case_id": self.case_id,
            "evidence_type": self.evidence_type,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "hash_md5": self.hash_md5,
            "hash_sha1": self.hash_sha1,
            "hash_sha256": self.hash_sha256,
            "description": self.description,
            "collector_id": self.collector_id,
            "status": self.status,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    def __str__(self):
        return f"{self.file_name} ({self.evidence_type})"
