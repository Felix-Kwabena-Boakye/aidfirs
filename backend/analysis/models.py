from mongo_connection import analysis_results_collection
from datetime import datetime, timezone
from bson import ObjectId

class AnalysisResult:
    """
    MongoDB-based AnalysisResult model for digital forensics analysis.
    """
    
    ANALYSIS_TYPE_CHOICES = [
        ('static', 'Static Analysis'),
        ('dynamic', 'Dynamic Analysis'),
        ('malware', 'Malware Analysis'),
        ('network', 'Network Analysis'),
        ('memory', 'Memory Analysis'),
        ('disk', 'Disk Forensics'),
        ('log', 'Log Analysis'),
        ('ai', 'AI-Powered Analysis')
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ]
    
    def __init__(self, case_id, evidence_id, analysis_type, findings,
                 severity='info', status='pending', analyzed_by='',
                 analyzed_at=None, completed_at=None,
                 indicators=None, summaries=None, recommendations=None, metadata=None, _id=None):
        self._id = _id
        self.case_id = case_id
        self.evidence_id = evidence_id
        self.analysis_type = analysis_type
        self.findings = findings
        self.severity = severity
        self.status = status
        self.analyzed_by = analyzed_by
        self.analyzed_at = analyzed_at or datetime.now(timezone.utc)
        self.completed_at = completed_at
        self.indicators = indicators or []
        self.summaries = summaries or []
        self.recommendations = recommendations or []
        self.metadata = metadata or {}

    @property
    def ResultID(self):
        """Alias for _id as per ER diagram."""
        return str(self._id) if self._id else None
    
    @staticmethod
    def create(case_id, evidence_id, analysis_type, findings,
               severity='info', analyzed_by=''):
        """
        Create new analysis result in MongoDB.
        """
        analysis_doc = {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "analysis_type": analysis_type,
            "findings": findings,
            "severity": severity,
            "status": "pending",
            "analyzed_by": analyzed_by,
            "analyzed_at": datetime.now(timezone.utc),
            "completed_at": None,
            "indicators": [],
            "summaries": [],
            "recommendations": [],
            "metadata": {}
        }
        
        result = analysis_results_collection.insert_one(analysis_doc)
        analysis_doc["_id"] = result.inserted_id
        
        return AnalysisResult.from_dict(analysis_doc)
    
    @staticmethod
    def get_by_id(analysis_id):
        """
        Get analysis result by ID.
        """
        try:
            analysis_data = analysis_results_collection.find_one({"_id": ObjectId(analysis_id)})
            if analysis_data:
                return AnalysisResult.from_dict(analysis_data)
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_all():
        """
        Get all analysis results.
        """
        results = analysis_results_collection.find().sort("analyzed_at", -1)
        return [AnalysisResult.from_dict(a) for a in results]
    
    @staticmethod
    def get_by_case(case_id):
        """
        Get all analysis results for a specific case.
        """
        results = analysis_results_collection.find({"case_id": case_id}).sort("analyzed_at", -1)
        return [AnalysisResult.from_dict(a) for a in results]
    
    @staticmethod
    def get_by_evidence(evidence_id):
        """
        Get all analysis results for a specific evidence.
        """
        results = analysis_results_collection.find({"evidence_id": evidence_id}).sort("analyzed_at", -1)
        return [AnalysisResult.from_dict(a) for a in results]
    
    @staticmethod
    def get_by_status(status):
        """
        Get analysis results by status.
        """
        results = analysis_results_collection.find({"status": status}).sort("analyzed_at", -1)
        return [AnalysisResult.from_dict(a) for a in results]
    
    def update(self, **kwargs):
        """
        Update analysis result fields.
        """
        # Don't update _id
        update_data = {k: v for k, v in kwargs.items() if k != '_id'}
        
        analysis_results_collection.update_one(
            {"_id": self._id},
            {"$set": update_data}
        )
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        return self
    
    def complete(self):
        """
        Mark analysis as completed.
        """
        return self.update(status='completed', completed_at=datetime.now(timezone.utc))
    
    def add_indicator(self, indicator):
        """
        Add IOC (Indicator of Compromise).
        """
        analysis_results_collection.update_one(
            {"_id": self._id},
            {"$addToSet": {"indicators": indicator}}
        )
        if indicator not in self.indicators:
            self.indicators.append(indicator)
        return self
    
    def add_summary(self, summary):
        """
        Add analysis summary.
        """
        analysis_results_collection.update_one(
            {"_id": self._id},
            {"$push": {"summaries": summary}}
        )
        self.summaries.append(summary)
        return self
    
    def add_recommendation(self, recommendation):
        """
        Add recommendation.
        """
        analysis_results_collection.update_one(
            {"_id": self._id},
            {"$push": {"recommendations": recommendation}}
        )
        self.recommendations.append(recommendation)
        return self
    
    def delete(self):
        """
        Delete analysis result from MongoDB.
        """
        analysis_results_collection.delete_one({"_id": self._id})
    
    @staticmethod
    def from_dict(data):
        """
        Create AnalysisResult instance from dictionary.
        """
        return AnalysisResult(
            _id=data.get('_id'),
            case_id=data.get('case_id'),
            evidence_id=data.get('evidence_id'),
            analysis_type=data.get('analysis_type'),
            findings=data.get('findings'),
            severity=data.get('severity', 'info'),
            status=data.get('status', 'pending'),
            analyzed_by=data.get('analyzed_by', ''),
            analyzed_at=data.get('analyzed_at'),
            completed_at=data.get('completed_at'),
            indicators=data.get('indicators', []),
            summaries=data.get('summaries', []),
            recommendations=data.get('recommendations', []),
            metadata=data.get('metadata', {})
        )
    
    def to_dict(self):
        """
        Convert AnalysisResult to dictionary.
        """
        return {
            "_id": str(self._id) if self._id else None,
            "case_id": self.case_id,
            "evidence_id": self.evidence_id,
            "analysis_type": self.analysis_type,
            "findings": self.findings,
            "severity": self.severity,
            "status": self.status,
            "analyzed_by": self.analyzed_by,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "indicators": self.indicators,
            "summaries": self.summaries,
            "recommendations": self.recommendations,
            "metadata": self.metadata
        }
    
    def __str__(self):
        return f"Analysis {self.analysis_type} - {self.status}"
