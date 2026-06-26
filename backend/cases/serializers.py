from rest_framework import serializers
from pydantic import BaseModel, field_validator, Field
from typing import Optional, Literal, List
from datetime import datetime
from pydantic import ConfigDict

class CasePydantic(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    _id: Optional[str] = None
    case_number: str
    title: str
    description: str = ''
    investigator_id: Optional[str] = None
    status: Literal['open', 'in_progress', 'closed', 'archived'] = 'open'
    priority: Literal['low', 'medium', 'high', 'critical'] = 'medium'
    case_type: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    evidence_ids: List[str] = []
    tags: List[str] = []
    
    @field_validator('case_number')
    @classmethod
    def validate_case_number(cls, v):
        if not v.strip():
            raise ValueError('Case number cannot be empty')
        return v.strip().upper()

class CaseSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    case_number = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, default='')
    investigator_id = serializers.CharField(required=False, default='')
    status = serializers.ChoiceField(
        choices=['open', 'in_progress', 'closed', 'archived'],
        default='open'
    )
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'critical'],
        default='medium'
    )
    case_type = serializers.CharField(max_length=100, required=False, default='')
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    closed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    evidence_ids = serializers.ListField(child=serializers.CharField(), default=list)
    tags = serializers.ListField(child=serializers.CharField(), default=list)
    
    def validate(self, data):
        CasePydantic(**data)
        return data
