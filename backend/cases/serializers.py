from rest_framework import serializers

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
