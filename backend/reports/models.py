from mongo_connection import get_db
from bson import ObjectId
import json
import os
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_FILE = os.path.join(BASE_DIR, 'reports_index.json')


class Report:
    """
    Model representing a generated forensic report.
    """
    FORMATS = ['pdf', 'docx', 'html']

    def __init__(self, case_id, report_type, format, examiner,
                 title=None, file_path=None, status="pending",
                 created_at=None, _id=None):
        self._id = _id
        self.case_id = str(case_id)
        self.report_type = report_type  # 'full', 'summary', 'timeline', 'coc'
        self.format = format.lower()
        self.examiner = examiner
        self.title = title or f"Forensic Report - {report_type}"
        self.file_path = file_path
        self.status = status  # 'pending', 'generating', 'completed', 'failed'
        self.created_at = created_at or datetime.now(timezone.utc)

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['reports']
        return None

    @staticmethod
    def create(case_id, report_type, format, examiner, title=None):
        col = Report.get_collection()
        doc = {
            "case_id": str(case_id),
            "report_type": report_type,
            "format": format.lower(),
            "examiner": examiner,
            "title": title or f"Forensic Report - {report_type}",
            "file_path": None,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        }
        if col is not None:
            result = col.insert_one(doc)
            doc["_id"] = result.inserted_id
        else:
            doc["_id"] = str(uuid.uuid4())
            reports = []
            if os.path.exists(REPORTS_FILE):
                try:
                    with open(REPORTS_FILE, 'r') as f:
                        reports = json.load(f)
                except:
                    pass
            reports.append(doc)
            with open(REPORTS_FILE, 'w') as f:
                json.dump(reports, f, indent=2, default=str)
        return Report.from_dict(doc)

    @staticmethod
    def get_by_case(case_id):
        col = Report.get_collection()
        if col is not None:
            try:
                cursor = col.find({"case_id": str(case_id)}).sort("created_at", -1)
                return [Report.from_dict(d) for d in cursor]
            except:
                pass
        if os.path.exists(REPORTS_FILE):
            try:
                with open(REPORTS_FILE, 'r') as f:
                    reports = json.load(f)
                filtered = [r for r in reports if str(r.get('case_id')) == str(case_id)]
                filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return [Report.from_dict(r) for r in filtered]
            except:
                pass
        return []

    @staticmethod
    def get_by_id(report_id):
        col = Report.get_collection()
        if col is not None:
            try:
                doc = col.find_one({"_id": ObjectId(report_id)})
                if doc:
                    return Report.from_dict(doc)
            except:
                pass
        if os.path.exists(REPORTS_FILE):
            try:
                with open(REPORTS_FILE, 'r') as f:
                    reports = json.load(f)
                for r in reports:
                    if str(r.get('_id')) == str(report_id):
                        return Report.from_dict(r)
            except:
                pass
        return None

    def update(self, **kwargs):
        col = Report.get_collection()
        for k, v in kwargs.items():
            setattr(self, k, v)
        update_data = {
            "status": self.status,
            "file_path": self.file_path,
            "title": self.title,
        }
        if col is not None:
            try:
                col.update_one({"_id": ObjectId(self._id)}, {"$set": update_data})
            except:
                pass
        else:
            if os.path.exists(REPORTS_FILE):
                try:
                    with open(REPORTS_FILE, 'r') as f:
                        reports = json.load(f)
                    for r in reports:
                        if str(r.get('_id')) == str(self._id):
                            for k, v in update_data.items():
                                r[k] = v
                            break
                    with open(REPORTS_FILE, 'w') as f:
                        json.dump(reports, f, indent=2, default=str)
                except:
                    pass
        return self

    def delete(self):
        col = Report.get_collection()
        if col is not None:
            try:
                col.delete_one({"_id": ObjectId(self._id)})
            except:
                pass
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except:
                pass

    @staticmethod
    def from_dict(data):
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                pass
        return Report(
            _id=data.get('_id'),
            case_id=data.get('case_id'),
            report_type=data.get('report_type', 'full'),
            format=data.get('format', 'pdf'),
            examiner=data.get('examiner', ''),
            title=data.get('title', ''),
            file_path=data.get('file_path'),
            status=data.get('status', 'pending'),
            created_at=created_at,
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "case_id": self.case_id,
            "report_type": self.report_type,
            "format": self.format,
            "examiner": self.examiner,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
