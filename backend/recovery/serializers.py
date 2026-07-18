from rest_framework import serializers

class RecoveryJobSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    _id = serializers.CharField(read_only=True)
    device_id = serializers.CharField(max_length=100)
    case_id = serializers.CharField(max_length=100)
    recovery_type = serializers.CharField(max_length=50, default='full')
    status = serializers.ChoiceField(choices=['PENDING', 'RUNNING', 'COMPLETED', 'FAILED'], default='PENDING')
    progress = serializers.IntegerField(default=0)
    files_found = serializers.IntegerField(default=0)
    start_time = serializers.DateTimeField(read_only=True)
    completion_time = serializers.DateTimeField(required=False, allow_null=True)


class RecoveredFileSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    _id = serializers.CharField(read_only=True)
    filename = serializers.CharField(max_length=255)
    size = serializers.IntegerField()
    hash_sha256 = serializers.CharField(max_length=64)
    hash_sha512 = serializers.CharField(max_length=128)
    case_id = serializers.CharField(max_length=100)
    recovery_job_id = serializers.CharField(max_length=100)
    created_at = serializers.DateTimeField(read_only=True)
