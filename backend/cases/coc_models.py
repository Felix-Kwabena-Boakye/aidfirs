from datetime import datetime, timezone
import json
import os
import uuid
from bson import ObjectId
from mongo_connection import get_chain_of_custody_collection, get_timeline_events_collection

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COC_FILE = os.path.join(BASE_DIR, 'chain_of_custody.json')
TIMELINE_FILE = os.path.join(BASE_DIR, 'timeline_events.json')

class ChainOfCustody:
    """
    MongoDB-based Chain of Custody record with file-based fallback.
    """
    def __init__(self, case_id, evidence_id, action, performed_by, timestamp=None,
                 hash_before='', hash_after='', notes='', ip_address=None, _id=None):
        self._id = _id
        self.case_id = str(case_id)
        self.evidence_id = str(evidence_id) if evidence_id else None
        self.action = action
        self.performed_by = performed_by
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.hash_before = hash_before or ''
        self.hash_after = hash_after or ''
        self.notes = notes or ''
        self.ip_address = ip_address or ''

    @staticmethod
    def create(case_id, evidence_id, action, performed_by, notes='', hash_before='', hash_after='',
               ip_address=None):
        """
        Create a new Chain of Custody entry.
        """
        coc_doc = {
            "case_id": str(case_id),
            "evidence_id": str(evidence_id) if evidence_id else None,
            "action": action,
            "performed_by": performed_by,
            "timestamp": datetime.now(timezone.utc),
            "hash_before": hash_before or '',
            "hash_after": hash_after or '',
            "notes": notes or '',
            "ip_address": ip_address or '',
        }

        collection = get_chain_of_custody_collection()
        if collection is not None:
            try:
                result = collection.insert_one(coc_doc)
                coc_doc["_id"] = result.inserted_id
            except Exception as e:
                # If DB fails, fallback to file
                coc_doc["_id"] = str(uuid.uuid4())
                ChainOfCustody._write_to_file(coc_doc)
        else:
            coc_doc["_id"] = str(uuid.uuid4())
            ChainOfCustody._write_to_file(coc_doc)

        return ChainOfCustody.from_dict(coc_doc)

    @staticmethod
    def _write_to_file(doc):
        """Helper to write CoC to local JSON file."""
        data = []
        if os.path.exists(COC_FILE):
            try:
                with open(COC_FILE, 'r') as f:
                    data = json.load(f)
            except:
                pass
        
        # Serialize datetime
        doc_serialized = doc.copy()
        if isinstance(doc_serialized.get('timestamp'), datetime):
            doc_serialized['timestamp'] = doc_serialized['timestamp'].isoformat()
        
        data.append(doc_serialized)
        try:
            with open(COC_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    @staticmethod
    def get_by_case(case_id):
        """
        Retrieve CoC entries for a case.
        """
        case_id_str = str(case_id)
        collection = get_chain_of_custody_collection()
        if collection is not None:
            try:
                cursor = collection.find({"case_id": case_id_str}).sort("timestamp", 1)
                return [ChainOfCustody.from_dict(d) for d in cursor]
            except Exception:
                pass

        # Fallback
        if os.path.exists(COC_FILE):
            try:
                with open(COC_FILE, 'r') as f:
                    data = json.load(f)
                filtered = [d for d in data if str(d.get('case_id')) == case_id_str]
                filtered.sort(key=lambda x: x.get('timestamp', ''))
                return [ChainOfCustody.from_dict(d) for d in filtered]
            except:
                pass
        return []

    @staticmethod
    def from_dict(data):
        """Create instance from dictionary."""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                pass
        return ChainOfCustody(
            _id=data.get('_id'),
            case_id=data.get('case_id'),
            evidence_id=data.get('evidence_id'),
            action=data.get('action'),
            performed_by=data.get('performed_by'),
            timestamp=timestamp,
            hash_before=data.get('hash_before'),
            hash_after=data.get('hash_after'),
            notes=data.get('notes'),
            ip_address=data.get('ip_address'),
        )

    def to_dict(self):
        """Convert to dict."""
        return {
            "_id": str(self._id) if self._id else None,
            "case_id": self.case_id,
            "evidence_id": self.evidence_id,
            "action": self.action,
            "performed_by": self.performed_by,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "hash_before": self.hash_before,
            "hash_after": self.hash_after,
            "notes": self.notes,
            "ip_address": self.ip_address,
        }


class TimelineEvent:
    """
    MongoDB-based Timeline Event with file-based fallback.
    """
    def __init__(self, case_id, timestamp, event_type, description, severity='info', _id=None):
        self._id = _id
        self.case_id = str(case_id)
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.event_type = event_type
        self.description = description
        self.severity = severity # 'info', 'low', 'medium', 'high', 'critical'

    @staticmethod
    def create(case_id, event_type, description, severity='info', timestamp=None):
        """
        Create a new Timeline Event.
        """
        event_doc = {
            "case_id": str(case_id),
            "timestamp": timestamp or datetime.now(timezone.utc),
            "event_type": event_type,
            "description": description,
            "severity": severity
        }

        collection = get_timeline_events_collection()
        if collection is not None:
            try:
                result = collection.insert_one(event_doc)
                event_doc["_id"] = result.inserted_id
            except Exception:
                event_doc["_id"] = str(uuid.uuid4())
                TimelineEvent._write_to_file(event_doc)
        else:
            event_doc["_id"] = str(uuid.uuid4())
            TimelineEvent._write_to_file(event_doc)

        return TimelineEvent.from_dict(event_doc)

    @staticmethod
    def _write_to_file(doc):
        """Helper to write timeline event to local JSON file."""
        data = []
        if os.path.exists(TIMELINE_FILE):
            try:
                with open(TIMELINE_FILE, 'r') as f:
                    data = json.load(f)
            except:
                pass
        
        # Serialize datetime
        doc_serialized = doc.copy()
        if isinstance(doc_serialized.get('timestamp'), datetime):
            doc_serialized['timestamp'] = doc_serialized['timestamp'].isoformat()
        
        data.append(doc_serialized)
        try:
            with open(TIMELINE_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    @staticmethod
    def get_by_case(case_id):
        """
        Retrieve timeline events for a case.
        """
        case_id_str = str(case_id)
        collection = get_timeline_events_collection()
        if collection is not None:
            try:
                cursor = collection.find({"case_id": case_id_str}).sort("timestamp", 1)
                return [TimelineEvent.from_dict(d) for d in cursor]
            except Exception:
                pass

        # Fallback
        if os.path.exists(TIMELINE_FILE):
            try:
                with open(TIMELINE_FILE, 'r') as f:
                    data = json.load(f)
                filtered = [d for d in data if str(d.get('case_id')) == case_id_str]
                filtered.sort(key=lambda x: x.get('timestamp', ''))
                return [TimelineEvent.from_dict(d) for d in filtered]
            except:
                pass
        return []

    @staticmethod
    def from_dict(data):
        """Create instance from dictionary."""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                pass
        return TimelineEvent(
            _id=data.get('_id'),
            case_id=data.get('case_id'),
            timestamp=timestamp,
            event_type=data.get('event_type'),
            description=data.get('description'),
            severity=data.get('severity', 'info'),
        )

    def to_dict(self):
        """Convert to dict."""
        return {
            "_id": str(self._id) if self._id else None,
            "case_id": self.case_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "event_type": self.event_type,
            "description": self.description,
            "severity": self.severity
        }
