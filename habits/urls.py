from django.urls import path

from habits.apps import HabitsConfig
from habits.views import (
    HabitCreateAPIView,
    HabitDestroyAPIView,
    HabitListAPIView,
    HabitUpdateAPIView,
    PublicHabitListAPIView,
)

app_name = HabitsConfig.name

urlpatterns = [
    path("", HabitListAPIView.as_view(), name="habit-list"),
    path("public/", PublicHabitListAPIView.as_view(), name="habit-public"),
    path("create/", HabitCreateAPIView.as_view(), name="habit-create"),
    path("<int:pk>/", HabitUpdateAPIView.as_view(), name="habit-detail"),
    path("<int:pk>/delete/", HabitDestroyAPIView.as_view(), name="habit-delete"),
]
