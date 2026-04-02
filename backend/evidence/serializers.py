from rest_framework import serializers

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


class EvidenceHashSerializer(serializers.Serializer):
    hash_value = serializers.CharField()
