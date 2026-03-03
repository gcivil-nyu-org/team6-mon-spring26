from rest_framework import serializers
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "display_name", "avatar_url", "date_joined",
            "phone", "timezone", "language", "notifications_enabled", 
            "default_currency", "date_format", "auth_provider", "email_verified"
        ]
        read_only_fields = ["id", "email", "date_joined", "auth_provider", "email_verified"]

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username", "full_name", "avatar", "phone", "timezone", "language", 
            "notifications_enabled", "default_currency", "date_format"
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
