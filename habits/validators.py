from typing import Any

from rest_framework.exceptions import ValidationError


class HabitValidator:
    requires_context = True

    def __call__(self, attrs: dict[str, Any], serializer: Any) -> None:
        instance = serializer.instance

        def get(name: str) -> Any:
            if name in attrs:
                return attrs[name]
            return getattr(instance, name, None) if instance else None

        reward = get("reward")
        related = get("related_habit")
        is_pleasant = get("is_pleasant")
        duration = get("duration")
        periodicity = get("periodicity")

        if reward and related:
            raise ValidationError("Нельзя одновременно указать вознаграждение и связанную привычку.")
        if related and not related.is_pleasant:
            raise ValidationError("Связанной может быть только приятная привычка.")
        if is_pleasant and (reward or related):
            raise ValidationError("У приятной привычки не может быть вознаграждения или связанной привычки.")
        if duration is not None and duration > 120:
            raise ValidationError("Время выполнения не может превышать 120 секунд.")
        if periodicity is not None and not 1 <= periodicity <= 7:
            raise ValidationError("Привычку нельзя выполнять реже, чем раз в 7 дней.")
