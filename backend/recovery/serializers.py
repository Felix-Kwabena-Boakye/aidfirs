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
    size = serializers.IntegerField(required=False, allow_null=True)
    hash_sha256 = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    hash_sha512 = serializers.CharField(max_length=128, required=False, allow_blank=True, allow_null=True)
    case_id = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    recovery_job_id = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)

    # Extended forensic metadata fields
    hash_md5 = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    hash_sha1 = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True)
    file_extension = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    mime_type = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    recovery_method = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    recovery_status = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    original_path = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    recovered_path = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    created_time = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    modified_time = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    accessed_time = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    deleted_time = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    device_id = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    examiner = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    carve_offset = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)