from mongo_connection import cases_collection
from datetime import datetime, timezone
from bson import ObjectId

class Case:
    """
    MongoDB-based Case model for digital forensics cases.
    """
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('archived', 'Archived')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ]
    
    def __init__(self, case_number, title, description, investigator_id,
                 status='open', priority='medium', case_type='', 
                 created_at=None, updated_at=None, closed_at=None, 
                 evidence_ids=None, tags=None, assigned_to=None, _id=None):
        self._id = _id
        self.case_number = case_number
        self.title = title
        self.description = description
        self.investigator_id = investigator_id
        self.status = status
        self.priority = priority
        self.case_type = case_type
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.closed_at = closed_at
        self.evidence_ids = evidence_ids or []
        self.tags = tags or []
        self.assigned_to = assigned_to or []

    @property
    def case_name(self):
        """Alias for title as per ER diagram."""
        return self.title

    @case_name.setter
    def case_name(self, value):
        self.title = value

    @property
    def created_date(self):
        """Alias for created_at as per ER diagram."""
        return self.created_at

    @created_date.setter
    def created_date(self, value):
        self.created_at = value

    @property
    def CaseID(self):
        """Alias for _id as per ER diagram."""
        return str(self._id) if self._id else None
    
    @staticmethod
    def create(case_number, title, description, investigator_id, 
               priority='medium', case_type=''):
        """
        Create a new case in MongoDB.
        """
        # Check if case number already exists
        if cases_collection.find_one({"case_number": case_number}):
            raise ValueError(f"Case number {case_number} already exists")
        
        case_doc = {
            "case_number": case_number,
            "title": title,
            "description": description,
            "investigator_id": investigator_id,
            "status": "open",
            "priority": priority,
            "case_type": case_type,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "closed_at": None,
            "evidence_ids": [],
            "tags": []
        }
        
        result = cases_collection.insert_one(case_doc)
        case_doc["_id"] = result.inserted_id
        
        return Case.from_dict(case_doc)
    
    @staticmethod
    def get_by_id(case_id):
        """
        Get case by ID.
        """
        try:
            case_data = cases_collection.find_one({"_id": ObjectId(case_id)})
            if case_data:
                return Case.from_dict(case_data)
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_all():
        """
        Get all cases.
        """
        cases = cases_collection.find().sort("created_at", -1)
        return [Case.from_dict(c) for c in cases]
    
    @staticmethod
    def get_by_investigator(investigator_id):
        """
        Get all cases for a specific investigator.
        """
        cases = cases_collection.find({"investigator_id": investigator_id}).sort("created_at", -1)
        return [Case.from_dict(c) for c in cases]
    
    @staticmethod
    def get_by_status(status):
        """
        Get cases by status.
        """
        cases = cases_collection.find({"status": status}).sort("created_at", -1)
        return [Case.from_dict(c) for c in cases]
    
    def update(self, **kwargs):
        """
        Update case fields.
        """
        kwargs["updated_at"] = datetime.now(timezone.utc)
        
        # Don't update _id
        update_data = {k: v for k, v in kwargs.items() if k != '_id'}
        
        cases_collection.update_one(
            {"_id": self._id},
            {"$set": update_data}
        )
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        return self
    
    def add_evidence(self, evidence_id):
        """
        Add evidence to case.
        """
        cases_collection.update_one(
            {"_id": self._id},
            {"$addToSet": {"evidence_ids": evidence_id}}
        )
        self.evidence_ids.append(evidence_id)
        return self
    
    def close(self):
        """
        Close the case.
        """
        return self.update(status='closed', closed_at=datetime.now(timezone.utc))
    
    def archive(self):
        """
        Archive the case.
        """
        return self.update(status='archived')
    
    def assign_investigators(self, investigator_ids):
        """
        Assign investigators to the case.
        """
        # Ensure assigned_to field exists
        if not hasattr(self, 'assigned_to'):
            self.assigned_to = []
        
        # Update with new investigators
        cases_collection.update_one(
            {"_id": self._id},
            {"$set": {"assigned_to": investigator_ids, "updated_at": datetime.now(timezone.utc)}}
        )
        self.assigned_to = investigator_ids
        return self
    
    def delete(self):
        """
        Delete case from MongoDB.
        """
        cases_collection.delete_one({"_id": self._id})
    
    @staticmethod
    def from_dict(data):
        """
        Create Case instance from dictionary.
        """
        return Case(
            _id=data.get('_id'),
            case_number=data.get('case_number'),
            title=data.get('title'),
            description=data.get('description'),
            investigator_id=data.get('investigator_id'),
            status=data.get('status', 'open'),
            priority=data.get('priority', 'medium'),
            case_type=data.get('case_type', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            closed_at=data.get('closed_at'),
            evidence_ids=data.get('evidence_ids', []),
            tags=data.get('tags', []),
            assigned_to=data.get('assigned_to', [])
        )
    
    def to_dict(self):
        """
        Convert Case to dictionary.
        """
        return {
            "_id": str(self._id) if self._id else None,
            "case_number": self.case_number,
            "title": self.title,
            "description": self.description,
            "investigator_id": self.investigator_id,
            "status": self.status,
            "priority": self.priority,
            "case_type": self.case_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "evidence_ids": self.evidence_ids,
            "tags": self.tags
        }
    
    def __str__(self):
        return f"{self.case_number} - {self.title}"
