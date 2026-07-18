from rest_framework import serializers

class DeviceSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    _id = serializers.CharField(read_only=True)
    device_name = serializers.CharField(max_length=200)
    serial_number = serializers.CharField(max_length=100, allow_blank=True, required=False, default='')
    model = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')
    filesystem = serializers.CharField(max_length=50, allow_blank=True, required=False, default='')
    size_gb = serializers.FloatField(required=False, default=0.0)
    drive_letter = serializers.CharField(max_length=50, allow_blank=True, required=False, default='')
    connected_at = serializers.DateTimeField(required=False, allow_null=True)
    source = serializers.CharField(max_length=100, allow_blank=True, required=False, default='AIDFIRS Agent')
