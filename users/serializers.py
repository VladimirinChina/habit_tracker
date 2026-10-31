from typing import Any

from rest_framework import serializers

from users.models import User


class UserRegisterSerializer(serializers.ModelSerializer[User]):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "tg_chat_id"]
        read_only_fields = ["id"]

    def create(self, validated_data: dict[str, Any]) -> User:
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "tg_chat_id"]
        read_only_fields = ["id", "email"]
