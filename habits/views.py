from typing import cast

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from habits.models import Habit
from habits.permissions import IsOwner
from habits.serializers import HabitSerializer
from users.models import User


class HabitListAPIView(generics.ListAPIView[Habit]):
    """Список привычек текущего пользователя (с пагинацией)."""

    serializer_class = HabitSerializer

    def get_queryset(self) -> QuerySet[Habit]:
        user = cast(User, self.request.user)
        return Habit.objects.filter(user=user).order_by("id")


class PublicHabitListAPIView(generics.ListAPIView[Habit]):
    """Список публичных привычек (только чтение, без авторизации)."""

    serializer_class = HabitSerializer
    queryset = Habit.objects.filter(is_public=True).order_by("id")
    permission_classes = [AllowAny]


class HabitCreateAPIView(generics.CreateAPIView[Habit]):
    """Создание привычки."""

    serializer_class = HabitSerializer

    def perform_create(self, serializer: HabitSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)


class HabitUpdateAPIView(generics.RetrieveUpdateAPIView[Habit]):
    """Просмотр и редактирование своей привычки."""

    serializer_class = HabitSerializer
    queryset = Habit.objects.all()
    permission_classes = [IsAuthenticated, IsOwner]


class HabitDestroyAPIView(generics.DestroyAPIView[Habit]):
    """Удаление своей привычки."""

    serializer_class = HabitSerializer
    queryset = Habit.objects.all()
    permission_classes = [IsAuthenticated, IsOwner]
