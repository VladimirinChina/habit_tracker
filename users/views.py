from typing import cast

from rest_framework import generics
from rest_framework.permissions import AllowAny

from users.models import User
from users.serializers import UserProfileSerializer, UserRegisterSerializer


class UserProfileAPIView(generics.RetrieveUpdateAPIView[User]):
    """Профиль текущего пользователя (в том числе Telegram chat id)."""

    serializer_class = UserProfileSerializer

    def get_object(self) -> User:
        return cast(User, self.request.user)


class UserRegisterAPIView(generics.CreateAPIView[User]):
    """Регистрация нового пользователя."""

    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]
