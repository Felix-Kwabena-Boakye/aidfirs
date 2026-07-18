from mongo_connection import get_db, MONGO_AVAILABLE
from bson import ObjectId
import json
import os
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERY_JOBS_FILE = os.path.join(BASE_DIR, 'recovery_jobs.json')
RECOVERED_FILES_FILE = os.path.join(BASE_DIR, 'recovered_files.json')

class RecoveryJob:
    """
    Model representing a digital forensic recovery task.
    """
    def __init__(self, device_id, case_id, recovery_type="full", status="PENDING",
                 progress=0, files_found=0, start_time=None, completion_time=None, _id=None):
        self._id = _id
        self.device_id = str(device_id)
        self.case_id = str(case_id)
        self.recovery_type = recovery_type
        self.status = status
        self.progress = int(progress)
        self.files_found = int(files_found)
        self.start_time = start_time or datetime.now(timezone.utc)
        self.completion_time = completion_time

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['recovery_jobs']
        return None

    @staticmethod
    def create(device_id, case_id, recovery_type="full"):
        col = RecoveryJob.get_collection()
        doc = {
            "device_id": str(device_id),
            "case_id": str(case_id),
            "recovery_type": recovery_type,
            "status": "PENDING",
            "progress": 0,
            "files_found": 0,
            "start_time": datetime.now(timezone.utc),
            "completion_time": None
        }

        if col is not None:
            result = col.insert_one(doc)
            doc["_id"] = result.inserted_id
        else:
            doc["_id"] = str(uuid.uuid4())
            jobs = []
            if os.path.exists(RECOVERY_JOBS_FILE):
                try:
                    with open(RECOVERY_JOBS_FILE, 'r') as f:
                        jobs = json.load(f)
                except:
                    pass
            jobs.append(doc)
            with open(RECOVERY_JOBS_FILE, 'w') as f:
                json.dump(jobs, f, indent=2, default=str)

        return RecoveryJob.from_dict(doc)

    @staticmethod
    def get_all():
        col = RecoveryJob.get_collection()
        if col is not None:
            try:
                cursor = col.find().sort("start_time", -1)
                return [RecoveryJob.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(RECOVERY_JOBS_FILE):
            try:
                with open(RECOVERY_JOBS_FILE, 'r') as f:
                    jobs = json.load(f)
                jobs.sort(key=lambda x: x.get('start_time', ''), reverse=True)
                return [RecoveryJob.from_dict(d) for d in jobs]
            except:
                pass
        return []

    @staticmethod
    def get_by_id(job_id):
        col = RecoveryJob.get_collection()
        if col is not None:
            try:
                doc = col.find_one({"_id": ObjectId(job_id)})
                if doc:
                    return RecoveryJob.from_dict(doc)
            except:
                pass
        if os.path.exists(RECOVERY_JOBS_FILE):
            try:
                with open(RECOVERY_JOBS_FILE, 'r') as f:
                    jobs = json.load(f)
                for j in jobs:
                    if str(j.get('_id')) == str(job_id):
                        return RecoveryJob.from_dict(j)
            except:
                pass
        return None

    @staticmethod
    def get_pending():
        col = RecoveryJob.get_collection()
        if col is not None:
            try:
                cursor = col.find({"status": "PENDING"}).sort("start_time", 1)
                return [RecoveryJob.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(RECOVERY_JOBS_FILE):
            try:
                with open(RECOVERY_JOBS_FILE, 'r') as f:
                    jobs = json.load(f)
                pending = [j for j in jobs if j.get("status") == "PENDING"]
                pending.sort(key=lambda x: x.get('start_time', ''))
                return [RecoveryJob.from_dict(d) for d in pending]
            except:
                pass
        return []

    def update(self, **kwargs):
        col = RecoveryJob.get_collection()
        
        # Make sure start_time / completion_time conversion is handled
        for k, v in kwargs.items():
            setattr(self, k, v)
        
        update_data = {
            "status": self.status,
            "progress": int(self.progress),
            "files_found": int(self.files_found),
            "completion_time": self.completion_time
        }

        if col is not None:
            try:
                col.update_one({"_id": ObjectId(self._id)}, {"$set": update_data})
            except:
                pass
        else:
            if os.path.exists(RECOVERY_JOBS_FILE):
                try:
                    with open(RECOVERY_JOBS_FILE, 'r') as f:
                        jobs = json.load(f)
                    for i, j in enumerate(jobs):
                        if str(j.get('_id')) == str(self._id):
                            for k, val in update_data.items():
                                j[k] = val.isoformat() if isinstance(val, datetime) else val
                            break
                    with open(RECOVERY_JOBS_FILE, 'w') as f:
                        json.dump(jobs, f, indent=2, default=str)
                except:
                    pass
        return self

    @staticmethod
    def from_dict(data):
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                pass
        completion_time = data.get('completion_time')
        if isinstance(completion_time, str):
            try:
                completion_time = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
            except:
                pass
        return RecoveryJob(
            _id=data.get('_id'),
            device_id=data.get('device_id'),
            case_id=data.get('case_id'),
            recovery_type=data.get('recovery_type', 'full'),
            status=data.get('status', 'PENDING'),
            progress=data.get('progress', 0),
            files_found=data.get('files_found', 0),
            start_time=start_time,
            completion_time=completion_time
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "device_id": self.device_id,
            "case_id": self.case_id,
            "recovery_type": self.recovery_type,
            "status": self.status,
            "progress": self.progress,
            "files_found": self.files_found,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None
        }


class RecoveredFile:
    """
    Model representing a file carved or recovered from a physical drive.
    """
    def __init__(self, filename, storage_location, hash_sha256, hash_sha512, size, case_id, recovery_job_id, created_at=None, _id=None):
        self._id = _id
        self.filename = filename
        self.storage_location = storage_location
        self.hash_sha256 = hash_sha256
        self.hash_sha512 = hash_sha512
        self.size = int(size)
        self.case_id = str(case_id)
        self.recovery_job_id = str(recovery_job_id)
        self.created_at = created_at or datetime.now(timezone.utc)

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['recovered_files']
        return None

    @staticmethod
    def create(filename, storage_location, hash_sha256, hash_sha512, size, case_id, recovery_job_id):
        col = RecoveredFile.get_collection()
        doc = {
            "filename": filename,
            "storage_location": storage_location,
            "hash_sha256": hash_sha256,
            "hash_sha512": hash_sha512,
            "size": int(size),
            "case_id": str(case_id),
            "recovery_job_id": str(recovery_job_id),
            "created_at": datetime.now(timezone.utc)
        }

        if col is not None:
            result = col.insert_one(doc)
            doc["_id"] = result.inserted_id
        else:
            doc["_id"] = str(uuid.uuid4())
            files = []
            if os.path.exists(RECOVERED_FILES_FILE):
                try:
                    with open(RECOVERED_FILES_FILE, 'r') as f:
                        files = json.load(f)
                except:
                    pass
            files.append(doc)
            with open(RECOVERED_FILES_FILE, 'w') as f:
                json.dump(files, f, indent=2, default=str)

        return RecoveredFile.from_dict(doc)

    @staticmethod
    def get_by_case(case_id):
        col = RecoveredFile.get_collection()
        case_id_str = str(case_id)
        if col is not None:
            try:
                cursor = col.find({"case_id": case_id_str}).sort("created_at", -1)
                return [RecoveredFile.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(RECOVERED_FILES_FILE):
            try:
                with open(RECOVERED_FILES_FILE, 'r') as f:
                    files = json.load(f)
                filtered = [f for f in files if str(f.get("case_id")) == case_id_str]
                filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return [RecoveredFile.from_dict(d) for d in filtered]
            except:
                pass
        return []

    @staticmethod
    def get_by_id(file_id):
        col = RecoveredFile.get_collection()
        if col is not None:
            try:
                doc = col.find_one({"_id": ObjectId(file_id)})
                if doc:
                    return RecoveredFile.from_dict(doc)
            except:
                pass
        if os.path.exists(RECOVERED_FILES_FILE):
            try:
                with open(RECOVERED_FILES_FILE, 'r') as f:
                    files = json.load(f)
                for file_obj in files:
                    if str(file_obj.get('_id')) == str(file_id):
                        return RecoveredFile.from_dict(file_obj)
            except:
                pass
        return None

    @staticmethod
    def from_dict(data):
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                pass
        return RecoveredFile(
            _id=data.get('_id'),
            filename=data.get('filename'),
            storage_location=data.get('storage_location'),
            hash_sha256=data.get('hash_sha256'),
            hash_sha512=data.get('hash_sha512'),
            size=data.get('size', 0),
            case_id=data.get('case_id'),
            recovery_job_id=data.get('recovery_job_id'),
            created_at=created_at
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "filename": self.filename,
            "storage_location": self.storage_location,
            "hash_sha256": self.hash_sha256,
            "hash_sha512": self.hash_sha512,
            "size": self.size,
            "case_id": self.case_id,
            "recovery_job_id": self.recovery_job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
