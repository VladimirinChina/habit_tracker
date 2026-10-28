import logging

import requests
from celery import shared_task
from django.utils import timezone

from habits.models import Habit
from habits.services import build_reminder_text, send_telegram_message

logger = logging.getLogger(__name__)


@shared_task
def send_habit_reminders() -> None:
    """Раз в минуту находит привычки, которым пора напомнить, и шлёт сообщение в Telegram."""
    now = timezone.localtime()
    today = now.date()

    habits = (
        Habit.objects.filter(
            is_pleasant=False,
            time__hour=now.hour,
            time__minute=now.minute,
            user__tg_chat_id__isnull=False,
        )
        .select_related("user", "related_habit")
        .order_by("id")
    )

    for habit in habits:
        chat_id = habit.user.tg_chat_id
        if not chat_id:
            continue

        last = habit.last_reminder_date
        if last is not None and (today - last).days < habit.periodicity:
            continue

        try:
            send_telegram_message(chat_id, build_reminder_text(habit))
        except requests.RequestException:
            logger.exception("Не удалось отправить напоминание по привычке %s", habit.pk)
            continue

        habit.last_reminder_date = today
        habit.save(update_fields=["last_reminder_date"])
