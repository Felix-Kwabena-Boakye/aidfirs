from rest_framework import serializers

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
