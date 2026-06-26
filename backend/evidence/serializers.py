from rest_framework import serializers
from pydantic import BaseModel, field_validator, Field
from typing import Optional, Literal, List
from datetime import datetime
from pydantic import ConfigDict

class EvidencePydantic(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    _id: Optional[str] = None
    case_id: str
    evidence_type: Literal['file', 'disk_image', 'memory_dump', 'network_capture', 
                          'log_file', 'registry', 'email', 'other']
    file_name: str
    file_path: Optional[str] = None
    file_size: int = 0
    hash_md5: Optional[str] = None
    hash_sha1: Optional[str] = None
    hash_sha256: Optional[str] = None
    description: str = ''
    collector_id: Optional[str] = None
    status: Literal['collected', 'analyzing', 'analyzed', 'archived'] = 'collected'
    collected_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    tags: List[str] = []

class EvidenceSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    case_id = serializers.CharField()
    evidence_type = serializers.ChoiceField(
        choices=['file', 'disk_image', 'memory_dump', 'network_capture', 
                'log_file', 'registry', 'email', 'other']
    )
    file_name = serializers.CharField(max_length=500)
    file_path = serializers.CharField(max_length=1000, required=False)
    file_size = serializers.IntegerField(default=0)
    hash_md5 = serializers.CharField(read_only=True)
    hash_sha1 = serializers.CharField(read_only=True)
    hash_sha256 = serializers.CharField(read_only=True)
    description = serializers.CharField(default='')
    collector_id = serializers.CharField(required=False)
    status = serializers.ChoiceField(
        choices=['collected', 'analyzing', 'analyzed', 'archived'],
        default='collected'
    )
    collected_at = serializers.DateTimeField(read_only=True)
    analyzed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), default=list)
    
    def validate(self, data):
        EvidencePydantic(**data)
        return data

class EvidenceHashSerializer(serializers.Serializer):
    hash_value = serializers.CharField()
    
    def validate(self, data):
        if len(data['hash_value']) < 32:
            raise serializers.ValidationError('Hash must be at least 32 characters')
        return data
