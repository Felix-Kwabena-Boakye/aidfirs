from rest_framework import serializers


class DeviceSerializer(serializers.Serializer):
    """
    Serializer for device registration from the local forensic agent.
    Accepts all forensic device metadata fields.
    """
    id = serializers.CharField(read_only=True)
    _id = serializers.CharField(read_only=True)

    # Core identification
    device_name = serializers.CharField(max_length=200)
    serial_number = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')
    model = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')
    filesystem = serializers.CharField(max_length=100, allow_blank=True, required=False, default='')
    size_gb = serializers.FloatField(required=False, default=0.0)
    capacity = serializers.FloatField(required=False, default=0.0)  # alias for size_gb from agent
    capacity_bytes = serializers.IntegerField(required=False, default=0)
    drive_letter = serializers.CharField(max_length=100, allow_blank=True, required=False, default='')
    mount_point = serializers.CharField(max_length=500, allow_blank=True, required=False, default='')
    device_path = serializers.CharField(max_length=500, allow_blank=True, required=False, default='')
    volume_label = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')
    volume_name = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')

    # Connection metadata
    connected_at = serializers.DateTimeField(required=False, allow_null=True)
    connected_time = serializers.DateTimeField(required=False, allow_null=True)  # alias from agent
    source = serializers.CharField(max_length=200, allow_blank=True, required=False, default='AIDFIRS Agent')

    # Forensic metadata
    vendor = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')
    manufacturer = serializers.CharField(max_length=200, allow_blank=True, required=False, default='')
    bus_type = serializers.CharField(max_length=100, allow_blank=True, required=False, default='')
    drive_type = serializers.CharField(max_length=100, allow_blank=True, required=False, default='USB Drive')
    interface = serializers.CharField(max_length=100, allow_blank=True, required=False, default='')

    # Hashes
    hash_sha256 = serializers.CharField(max_length=64, allow_blank=True, required=False, default='')
    hash_md5 = serializers.CharField(max_length=32, allow_blank=True, required=False, default='')

    # Backward compat fields
    size_gb_compat = serializers.FloatField(source='size_gb', required=False, default=0.0)

    def validate(self, data):
        """Normalize aliases from agent payload."""
        # Normalize size_gb from 'capacity' field
        if not data.get('size_gb') and data.get('capacity'):
            data['size_gb'] = data['capacity']
        # Normalize connected_at from 'connected_time'
        if not data.get('connected_at') and data.get('connected_time'):
            data['connected_at'] = data['connected_time']
        # Normalize drive_letter from mount_point
        if not data.get('drive_letter') and data.get('mount_point'):
            data['drive_letter'] = data['mount_point']
        # Normalize volume_label from volume_name
        if not data.get('volume_label') and data.get('volume_name'):
            data['volume_label'] = data['volume_name']
        return data
