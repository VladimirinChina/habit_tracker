import requests
from django.conf import settings

from habits.models import Habit


def send_telegram_message(chat_id: str, text: str) -> None:
    url = f"{settings.TELEGRAM_API_URL}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
    response.raise_for_status()


def build_reminder_text(habit: Habit) -> str:
    text = f"Я буду {habit.action} в {habit.time:%H:%M} в {habit.place}."
    if habit.related_habit:
        text += f"\nПосле этого: {habit.related_habit.action}."
    elif habit.reward:
        text += f"\nНаграда: {habit.reward}."
    return text
