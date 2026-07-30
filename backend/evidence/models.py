from mongo_connection import evidence_collection
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import errors as pymongo_errors
import hashlib
import uuid
import json
import os
import logging

logger = logging.getLogger("evidence.models")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_FILE = os.path.join(BASE_DIR, 'evidence.json')

class Evidence:
    """
    MongoDB-based Evidence model for digital forensics.
    """
    
    STATUS_CHOICES = [
        ('collected', 'Collected'),
        ('pending_hash', 'Pending Hash'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('archived', 'Archived'),
        ('duplicate', 'Duplicate Evidence'),
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
        Compute real MD5, SHA1, SHA256 cryptographic hashes for a file.
        Returns hashes only for files that actually exist on disk.
        Returns None for all three if the file cannot be read.
        """
        if not file_path or not os.path.isfile(file_path):
            return {'md5': None, 'sha1': None, 'sha256': None}

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
        except Exception:
            return {'md5': None, 'sha1': None, 'sha256': None}
    
    @staticmethod
    def create(case_id, evidence_type, file_name, file_path,
               collector_id='', description='', file_size=0):
        """
        Create new evidence in MongoDB.

        Hash-safe insertion flow:
        - Hashes are computed only when the file already exists on disk.
        - If hashes are unavailable (file pending acquisition / not yet on disk),
          hash fields are OMITTED entirely from the document (not set to null).
          This prevents the partial unique index from rejecting null duplicates.
        - If a recovered file already has a matching SHA-256 in the collection
          (E11000), the existing record is returned and tagged as a duplicate
          instead of crashing the examination pipeline.
        """
        hashes = Evidence.compute_hashes(file_path) if file_path else {'md5': None, 'sha1': None, 'sha256': None}

        # Status: if hashes are available the record is 'collected'; otherwise mark
        # as 'pending_hash' so the pipeline knows to update hashes later.
        hashes_available = bool(hashes.get('sha256'))
        initial_status = "collected" if hashes_available else "pending_hash"

        evidence_doc = {
            "case_id": case_id,
            "evidence_type": evidence_type,
            "file_name": file_name,
            "file_path": file_path,
            "file_size": file_size,
            "description": description,
            "collector_id": collector_id,
            "status": initial_status,
            "collected_at": datetime.now(timezone.utc),
            "analyzed_at": None,
            "tags": [],
            "metadata": {}
        }

        # Only include hash fields when they contain real values (never insert null).
        if hashes.get('md5'):
            evidence_doc["hash_md5"] = hashes['md5']
        if hashes.get('sha1'):
            evidence_doc["hash_sha1"] = hashes['sha1']
        if hashes.get('sha256'):
            evidence_doc["hash_sha256"] = hashes['sha256']

        if evidence_collection is not None:
            try:
                result = evidence_collection.insert_one(evidence_doc)
                evidence_doc["_id"] = result.inserted_id
            except pymongo_errors.DuplicateKeyError as dup_err:
                # E11000: a record with this SHA-256 already exists.
                # Return the existing record and flag it as duplicate — do not crash.
                sha256 = hashes.get('sha256')
                logger.warning(
                    f"Duplicate evidence detected (SHA-256: {sha256}). "
                    "Returning existing record and marking as duplicate."
                )
                existing = evidence_collection.find_one({"hash_sha256": sha256})
                if existing:
                    existing_evidence = Evidence.from_dict(existing)
                    # Tag the existing record so investigators know it's a duplicate hit.
                    evidence_collection.update_one(
                        {"_id": existing["_id"]},
                        {"$addToSet": {"tags": "duplicate"}}
                    )
                    existing_evidence.tags = list(set(existing_evidence.tags + ["duplicate"]))
                    return existing_evidence
                # Fallback: return a transient in-memory doc if lookup fails.
                evidence_doc["_id"] = str(uuid.uuid4())
                evidence_doc["tags"] = ["duplicate"]
                return Evidence.from_dict(evidence_doc)
        else:
            evidence_doc["_id"] = str(uuid.uuid4())
            evidence_data = []
            if os.path.exists(EVIDENCE_FILE):
                try:
                    with open(EVIDENCE_FILE, 'r') as f:
                        evidence_data = json.load(f)
                except Exception:
                    pass
            evidence_data.append(evidence_doc)
            with open(EVIDENCE_FILE, 'w') as f:
                json.dump(evidence_data, f, indent=2, default=str)

        return Evidence.from_dict(evidence_doc)

    @staticmethod
    def update_hashes(evidence_id, file_path):
        """
        Compute and persist cryptographic hashes after a file has been fully
        recovered/written to disk.  Updates status from 'pending_hash' to
        'collected' and stamps the hash fields.

        Returns a dict with keys: success, sha256, duplicate, existing_id.
        """
        hashes = Evidence.compute_hashes(file_path)
        if not hashes.get('sha256'):
            return {"success": False, "reason": "File unreadable or not found"}

        if evidence_collection is not None:
            try:
                evidence_collection.update_one(
                    {"_id": ObjectId(evidence_id)},
                    {"$set": {
                        "hash_md5": hashes['md5'],
                        "hash_sha1": hashes['sha1'],
                        "hash_sha256": hashes['sha256'],
                        "status": "collected",
                    }}
                )
                return {"success": True, "sha256": hashes['sha256'], "duplicate": False}
            except pymongo_errors.DuplicateKeyError:
                # Another document already owns this SHA-256 hash.
                sha256 = hashes['sha256']
                existing = evidence_collection.find_one({"hash_sha256": sha256})
                existing_id = str(existing["_id"]) if existing else None
                logger.warning(
                    f"Hash update collision: SHA-256 {sha256} belongs to evidence {existing_id}. "
                    f"Marking evidence {evidence_id} as duplicate."
                )
                evidence_collection.update_one(
                    {"_id": ObjectId(evidence_id)},
                    {"$set": {"status": "duplicate"}, "$addToSet": {"tags": "duplicate"}}
                )
                return {"success": True, "sha256": sha256, "duplicate": True, "existing_id": existing_id}
        return {"success": False, "reason": "MongoDB not available"}
    
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
