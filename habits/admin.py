from django.contrib import admin

from habits.models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "action", "user", "time", "is_pleasant", "is_public")
    list_filter = ("is_pleasant", "is_public")
    search_fields = ("action", "place")
