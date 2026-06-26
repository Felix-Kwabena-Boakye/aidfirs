from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict

class AnalysisResultPydantic(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    _id: Optional[str] = None
    case_id: str
    evidence_id: str
    analysis_type: Literal['static', 'dynamic', 'malware', 'network', 'memory', 'disk', 'log', 'ai']
    findings: Dict[str, Any] = {}
    severity: Literal['info', 'low', 'medium', 'high', 'critical'] = 'info'
    status: Literal['pending', 'in_progress', 'completed', 'failed'] = 'pending'
    analyzed_by: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    indicators: List[Dict[str, Any]] = []
    summaries: List[str] = []
    recommendations: List[str] = []
    metadata: Dict[str, Any] = {}

class AnalysisResultSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    case_id = serializers.CharField()
    evidence_id = serializers.CharField()
    analysis_type = serializers.ChoiceField(
        choices=['static', 'dynamic', 'malware', 'network', 'memory', 'disk', 'log', 'ai']
    )
    findings = serializers.DictField(required=False, default=dict)
    severity = serializers.ChoiceField(
        choices=['info', 'low', 'medium', 'high', 'critical'],
        default='info'
    )
    status = serializers.ChoiceField(
        choices=['pending', 'in_progress', 'completed', 'failed'],
        default='pending'
    )
    analyzed_by = serializers.CharField(required=False)
    analyzed_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    indicators = serializers.ListField(child=serializers.DictField(), default=list)
    summaries = serializers.ListField(child=serializers.CharField(), default=list)
    recommendations = serializers.ListField(child=serializers.CharField(), default=list)
    metadata = serializers.DictField(default=dict)
    
    def validate(self, data):
        AnalysisResultPydantic(**data)
        return data
