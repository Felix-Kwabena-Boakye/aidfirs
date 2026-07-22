from mongo_connection import get_db, MONGO_AVAILABLE
from bson import ObjectId
import json
import os
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERY_JOBS_FILE = os.path.join(BASE_DIR, 'recovery_jobs.json')
RECOVERED_FILES_FILE = os.path.join(BASE_DIR, 'recovered_files.json')
TIMELINE_EVENTS_FILE = os.path.join(BASE_DIR, 'timeline_events.json')


class RecoveryJob:
    """
    Model representing a digital forensic recovery task.
    """
    VALID_STAGES = [
        "PENDING", "DEVICE_DETECTION", "DISK_IMAGING", "HASH_CALCULATION",
        "SCANNING", "FILE_CARVING", "RECOVERY", "SAVING",
        "UPLOADING_METADATA", "COMPLETED", "FAILED", "RUNNING"
    ]

    STAGE_OPERATIONS = {
        "PENDING": "Waiting for forensic agent assignment",
        "DEVICE_DETECTION": "Detecting connected forensic device",
        "DISK_IMAGING": "Creating bit-by-bit forensic disk image",
        "HASH_CALCULATION": "Computing SHA256/MD5 integrity hashes",
        "SCANNING": "Scanning forensic image for recoverable data",
        "FILE_CARVING": "Carving file signatures from image",
        "RECOVERY": "Recovering deleted files from image",
        "SAVING": "Saving recovered artifacts to case storage",
        "UPLOADING_METADATA": "Uploading evidence and metadata to backend",
        "COMPLETED": "Recovery workflow completed",
        "FAILED": "Recovery workflow failed",
        "RUNNING": "Forensic recovery in progress",
    }

    def __init__(self, device_id, case_id, recovery_type="full", status="PENDING",
                 stage="PENDING", progress=0, files_found=0, start_time=None,
                 completion_time=None, error_message=None, current_operation=None,
                 _id=None):
        self._id = _id
        self.device_id = str(device_id)
        self.case_id = str(case_id)
        self.recovery_type = recovery_type
        self.status = status
        self.stage = stage
        self.progress = int(progress)
        self.files_found = int(files_found)
        self.start_time = start_time or datetime.now(timezone.utc)
        self.completion_time = completion_time
        self.error_message = error_message
        self.current_operation = current_operation or self.STAGE_OPERATIONS.get(stage, stage)

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
            "stage": "PENDING",
            "progress": 0,
            "files_found": 0,
            "start_time": datetime.now(timezone.utc),
            "completion_time": None,
            "error_message": None,
            "current_operation": RecoveryJob.STAGE_OPERATIONS["PENDING"],
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
    def get_all(case_id=None, device_id=None, status=None, limit=100):
        col = RecoveryJob.get_collection()
        query = {}
        if case_id:
            query["case_id"] = str(case_id)
        if device_id:
            query["device_id"] = str(device_id)
        if status:
            query["status"] = status

        if col is not None:
            try:
                cursor = col.find(query).sort("start_time", -1).limit(limit)
                return [RecoveryJob.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(RECOVERY_JOBS_FILE):
            try:
                with open(RECOVERY_JOBS_FILE, 'r') as f:
                    jobs = json.load(f)
                if case_id:
                    jobs = [j for j in jobs if str(j.get('case_id')) == str(case_id)]
                if device_id:
                    jobs = [j for j in jobs if str(j.get('device_id')) == str(device_id)]
                if status:
                    jobs = [j for j in jobs if j.get('status') == status]
                jobs.sort(key=lambda x: x.get('start_time', ''), reverse=True)
                return [RecoveryJob.from_dict(d) for d in jobs[:limit]]
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

        for k, v in kwargs.items():
            setattr(self, k, v)

        update_data = {
            "status": self.status,
            "stage": self.stage,
            "progress": int(self.progress),
            "files_found": int(self.files_found),
            "completion_time": self.completion_time,
            "error_message": self.error_message,
            "current_operation": self.current_operation,
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
            stage=data.get('stage', 'PENDING'),
            progress=data.get('progress', 0),
            files_found=data.get('files_found', 0),
            start_time=start_time,
            completion_time=completion_time,
            error_message=data.get('error_message'),
            current_operation=data.get('current_operation'),
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "device_id": self.device_id,
            "case_id": self.case_id,
            "recovery_type": self.recovery_type,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "files_found": self.files_found,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "error_message": self.error_message,
            "current_operation": self.current_operation,
        }


class RecoveredFile:
    """
    Model representing a file carved or recovered from a physical drive.
    Stores full forensic metadata per file.
    """
    def __init__(self, filename, storage_location, hash_sha256, hash_sha512,
                 size, case_id, recovery_job_id,
                 # Extended forensic metadata
                 hash_md5=None, hash_sha1=None,
                 original_path=None, recovered_path=None,
                 file_extension=None, mime_type=None,
                 recovery_method=None, recovery_status="recovered",
                 created_time=None, modified_time=None,
                 accessed_time=None, deleted_time=None,
                 device_id=None, examiner=None,
                 carve_offset=None, description=None,
                 created_at=None, _id=None):
        self._id = _id
        self.filename = filename
        self.storage_location = storage_location
        self.hash_sha256 = hash_sha256
        self.hash_sha512 = hash_sha512
        self.hash_md5 = hash_md5
        self.hash_sha1 = hash_sha1
        self.size = int(size) if size else 0
        self.case_id = str(case_id)
        self.recovery_job_id = str(recovery_job_id)
        # Extended
        self.original_path = original_path
        self.recovered_path = recovered_path or storage_location
        self.file_extension = file_extension or (
            os.path.splitext(filename)[1].lower().lstrip('.') if filename else ''
        )
        self.mime_type = mime_type
        self.recovery_method = recovery_method or "signature_carving"
        self.recovery_status = recovery_status
        self.created_time = created_time
        self.modified_time = modified_time
        self.accessed_time = accessed_time
        self.deleted_time = deleted_time
        self.device_id = device_id
        self.examiner = examiner
        self.carve_offset = carve_offset
        self.description = description
        self.created_at = created_at or datetime.now(timezone.utc)

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['recovered_files']
        return None

    @staticmethod
    def create(filename, storage_location, hash_sha256, hash_sha512, size,
               case_id, recovery_job_id, **kwargs):
        col = RecoveredFile.get_collection()
        doc = {
            "filename": filename,
            "storage_location": storage_location,
            "hash_sha256": hash_sha256,
            "hash_sha512": hash_sha512,
            "hash_md5": kwargs.get("hash_md5"),
            "hash_sha1": kwargs.get("hash_sha1"),
            "size": int(size) if size else 0,
            "case_id": str(case_id),
            "recovery_job_id": str(recovery_job_id),
            "original_path": kwargs.get("original_path"),
            "recovered_path": kwargs.get("recovered_path", storage_location),
            "file_extension": kwargs.get("file_extension",
                os.path.splitext(filename)[1].lower().lstrip('.') if filename else ''),
            "mime_type": kwargs.get("mime_type"),
            "recovery_method": kwargs.get("recovery_method", "signature_carving"),
            "recovery_status": kwargs.get("recovery_status", "recovered"),
            "created_time": kwargs.get("created_time"),
            "modified_time": kwargs.get("modified_time"),
            "accessed_time": kwargs.get("accessed_time"),
            "deleted_time": kwargs.get("deleted_time"),
            "device_id": kwargs.get("device_id"),
            "examiner": kwargs.get("examiner"),
            "carve_offset": kwargs.get("carve_offset"),
            "description": kwargs.get("description"),
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
    def get_by_case(case_id, limit=500):
        col = RecoveredFile.get_collection()
        case_id_str = str(case_id)
        if col is not None:
            try:
                cursor = col.find({"case_id": case_id_str}).sort("created_at", -1).limit(limit)
                return [RecoveredFile.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(RECOVERED_FILES_FILE):
            try:
                with open(RECOVERED_FILES_FILE, 'r') as f:
                    files = json.load(f)
                filtered = [f for f in files if str(f.get("case_id")) == case_id_str]
                filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return [RecoveredFile.from_dict(d) for d in filtered[:limit]]
            except:
                pass
        return []

    @staticmethod
    def search(case_id=None, filename=None, extension=None, hash_value=None,
               device_id=None, date_from=None, date_to=None,
               min_size=None, max_size=None, keyword=None, limit=200):
        """Search recovered files by multiple criteria."""
        col = RecoveredFile.get_collection()
        query = {}
        if case_id:
            query["case_id"] = str(case_id)
        if device_id:
            query["device_id"] = str(device_id)
        if filename:
            query["filename"] = {"$regex": filename, "$options": "i"}
        if extension:
            query["file_extension"] = extension.lower().lstrip('.')
        if hash_value:
            query["$or"] = [
                {"hash_sha256": hash_value},
                {"hash_md5": hash_value},
                {"hash_sha1": hash_value}
            ]

        if col is not None:
            try:
                cursor = col.find(query).sort("created_at", -1).limit(limit)
                results = [RecoveredFile.from_dict(d) for d in cursor]
                # Apply size filters
                if min_size is not None:
                    results = [r for r in results if r.size >= int(min_size)]
                if max_size is not None:
                    results = [r for r in results if r.size <= int(max_size)]
                return results
            except:
                pass
        if os.path.exists(RECOVERED_FILES_FILE):
            try:
                with open(RECOVERED_FILES_FILE, 'r') as f:
                    files = json.load(f)
                results = []
                for file_obj in files:
                    if case_id and str(file_obj.get('case_id')) != str(case_id):
                        continue
                    if device_id and str(file_obj.get('device_id')) != str(device_id):
                        continue
                    if filename and filename.lower() not in (file_obj.get('filename') or '').lower():
                        continue
                    if extension and (file_obj.get('file_extension') or '').lower() != extension.lower().lstrip('.'):
                        continue
                    if hash_value and hash_value not in [
                        file_obj.get('hash_sha256'), file_obj.get('hash_md5'), file_obj.get('hash_sha1')
                    ]:
                        continue
                    fsize = file_obj.get('size', 0)
                    if min_size is not None and fsize < int(min_size):
                        continue
                    if max_size is not None and fsize > int(max_size):
                        continue
                    results.append(RecoveredFile.from_dict(file_obj))
                results.sort(key=lambda x: (x.created_at.isoformat() if x.created_at else ''), reverse=True)
                return results[:limit]
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
            hash_md5=data.get('hash_md5'),
            hash_sha1=data.get('hash_sha1'),
            size=data.get('size', 0),
            case_id=data.get('case_id'),
            recovery_job_id=data.get('recovery_job_id'),
            original_path=data.get('original_path'),
            recovered_path=data.get('recovered_path'),
            file_extension=data.get('file_extension'),
            mime_type=data.get('mime_type'),
            recovery_method=data.get('recovery_method', 'signature_carving'),
            recovery_status=data.get('recovery_status', 'recovered'),
            created_time=data.get('created_time'),
            modified_time=data.get('modified_time'),
            accessed_time=data.get('accessed_time'),
            deleted_time=data.get('deleted_time'),
            device_id=data.get('device_id'),
            examiner=data.get('examiner'),
            carve_offset=data.get('carve_offset'),
            description=data.get('description'),
            created_at=created_at
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "filename": self.filename,
            "storage_location": None,  # Never expose internal paths
            "hash_sha256": self.hash_sha256,
            "hash_sha512": self.hash_sha512,
            "hash_md5": self.hash_md5,
            "hash_sha1": self.hash_sha1,
            "size": self.size,
            "case_id": self.case_id,
            "recovery_job_id": self.recovery_job_id,
            "original_path": self.original_path,
            "file_extension": self.file_extension,
            "mime_type": self.mime_type,
            "recovery_method": self.recovery_method,
            "recovery_status": self.recovery_status,
            "created_time": self.created_time,
            "modified_time": self.modified_time,
            "accessed_time": self.accessed_time,
            "deleted_time": self.deleted_time,
            "device_id": self.device_id,
            "examiner": self.examiner,
            "carve_offset": self.carve_offset,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TimelineEvent:
    """
    Forensic timeline event. Records every significant forensic action.
    """
    def __init__(self, case_id, event_type, description, timestamp=None,
                 actor=None, device_id=None, evidence_id=None,
                 metadata=None, _id=None):
        self._id = _id
        self.case_id = str(case_id)
        self.event_type = event_type
        self.description = description
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.actor = actor
        self.device_id = device_id
        self.evidence_id = evidence_id
        self.metadata = metadata or {}

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['timeline_events']
        return None

    @staticmethod
    def create(case_id, event_type, description, **kwargs):
        col = TimelineEvent.get_collection()
        doc = {
            "case_id": str(case_id),
            "event_type": event_type,
            "description": description,
            "timestamp": kwargs.get("timestamp", datetime.now(timezone.utc)),
            "actor": kwargs.get("actor"),
            "device_id": kwargs.get("device_id"),
            "evidence_id": kwargs.get("evidence_id"),
            "metadata": kwargs.get("metadata", {}),
        }
        if col is not None:
            result = col.insert_one(doc)
            doc["_id"] = result.inserted_id
        else:
            doc["_id"] = str(uuid.uuid4())
            events = []
            if os.path.exists(TIMELINE_EVENTS_FILE):
                try:
                    with open(TIMELINE_EVENTS_FILE, 'r') as f:
                        events = json.load(f)
                except:
                    pass
            events.append(doc)
            with open(TIMELINE_EVENTS_FILE, 'w') as f:
                json.dump(events, f, indent=2, default=str)
        return TimelineEvent.from_dict(doc)

    @staticmethod
    def get_by_case(case_id, event_type=None, limit=500):
        col = TimelineEvent.get_collection()
        query = {"case_id": str(case_id)}
        if event_type:
            query["event_type"] = event_type
        if col is not None:
            try:
                cursor = col.find(query).sort("timestamp", 1).limit(limit)
                return [TimelineEvent.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(TIMELINE_EVENTS_FILE):
            try:
                with open(TIMELINE_EVENTS_FILE, 'r') as f:
                    events = json.load(f)
                filtered = [e for e in events if str(e.get('case_id')) == str(case_id)]
                if event_type:
                    filtered = [e for e in filtered if e.get('event_type') == event_type]
                filtered.sort(key=lambda x: x.get('timestamp', ''))
                return [TimelineEvent.from_dict(d) for d in filtered[:limit]]
            except:
                pass
        return []

    @staticmethod
    def from_dict(data):
        ts = data.get('timestamp')
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                pass
        return TimelineEvent(
            _id=data.get('_id'),
            case_id=data.get('case_id'),
            event_type=data.get('event_type'),
            description=data.get('description'),
            timestamp=ts,
            actor=data.get('actor'),
            device_id=data.get('device_id'),
            evidence_id=data.get('evidence_id'),
            metadata=data.get('metadata', {})
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "case_id": self.case_id,
            "event_type": self.event_type,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor": self.actor,
            "device_id": self.device_id,
            "evidence_id": self.evidence_id,
            "metadata": self.metadata,
        }
