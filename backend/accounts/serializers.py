from rest_framework import serializers

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


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
