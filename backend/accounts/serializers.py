from rest_framework import serializers
from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional, Literal
from datetime import datetime
from pydantic import ConfigDict

class UserPydantic(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    _id: Optional[str] = None
    username: str
    email: EmailStr
    role: Literal['admin', 'investigator', 'analyst'] = 'analyst'
    first_name: str = ''
    last_name: str = ''
    password: Optional[str] = None
    is_active: bool = True
    is_staff: bool = False
    date_joined: Optional[datetime] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain alphanumeric, _, -')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()

class UserLoginPydantic(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    username: str
    password: str

class UserSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.ChoiceField(choices=['admin', 'investigator', 'analyst'], default='analyst')
    first_name = serializers.CharField(max_length=150, default='')
    last_name = serializers.CharField(max_length=150, default='')
    is_active = serializers.BooleanField(default=True)
    is_staff = serializers.BooleanField(default=False)
    date_joined = serializers.DateTimeField(read_only=True)

    def validate(self, data):
        pydantic_model = UserPydantic(**data)
        return data

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        UserLoginPydantic(**data)
        return data
