from rest_framework import serializers

from habits.models import Habit
from habits.validators import HabitValidator


class HabitSerializer(serializers.ModelSerializer[Habit]):
    class Meta:
        model = Habit
        fields = [
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "related_habit",
            "periodicity",
            "reward",
            "duration",
            "is_public",
        ]
        read_only_fields = ["id", "user"]
        validators = [HabitValidator()]

    def validate_related_habit(self, value: Habit | None) -> Habit | None:
        request = self.context.get("request")
        if value is not None and request is not None and value.user != request.user:
            raise serializers.ValidationError("Можно выбрать только свою привычку.")
        return value
