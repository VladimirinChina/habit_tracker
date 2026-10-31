from datetime import datetime, time, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit
from habits.services import build_reminder_text, send_telegram_message
from habits.tasks import send_habit_reminders
from users.models import User


def make_habit(user: User, **kwargs: Any) -> Habit:
    data: dict[str, Any] = {
        "user": user,
        "place": "дома",
        "time": time(9, 30),
        "action": "пить воду",
        "duration": 60,
        "reward": "кофе",
    }
    data.update(kwargs)
    return Habit.objects.create(**data)


class HabitAPITests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="user@example.com", password="pass12345")
        self.other = User.objects.create_user(email="other@example.com", password="pass12345")
        self.client.force_authenticate(user=self.user)
        self.payload: dict[str, Any] = {
            "place": "дома",
            "time": "09:30:00",
            "action": "пить воду",
            "is_pleasant": False,
            "periodicity": 1,
            "reward": "кофе",
            "duration": 60,
            "is_public": False,
        }

    def test_create_habit(self) -> None:
        response = self.client.post(reverse("habits:habit-create"), self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        habit = Habit.objects.get()
        self.assertEqual(habit.user, self.user)

    def test_create_useful_habit_with_related_pleasant(self) -> None:
        pleasant = make_habit(self.user, is_pleasant=True, reward=None, action="принять ванну")
        payload = {**self.payload, "reward": None, "related_habit": pleasant.pk}
        response = self.client.post(reverse("habits:habit-create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_pleasant_habit(self) -> None:
        payload = {**self.payload, "is_pleasant": True, "reward": None}
        response = self.client.post(reverse("habits:habit-create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_requires_auth(self) -> None:
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse("habits:habit-create"), self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_validators(self) -> None:
        useful = make_habit(self.user)
        pleasant = make_habit(self.user, is_pleasant=True, reward=None)
        foreign_pleasant = make_habit(self.other, is_pleasant=True, reward=None)
        cases: dict[str, dict[str, Any]] = {
            "reward_and_related": {"reward": "кофе", "related_habit": pleasant.pk},
            "related_not_pleasant": {"reward": None, "related_habit": useful.pk},
            "pleasant_with_reward": {"is_pleasant": True, "reward": "кофе"},
            "pleasant_with_related": {"is_pleasant": True, "reward": None, "related_habit": pleasant.pk},
            "duration_too_long": {"duration": 121},
            "periodicity_too_big": {"periodicity": 8},
            "periodicity_zero": {"periodicity": 0},
            "foreign_related": {"reward": None, "related_habit": foreign_pleasant.pk},
        }
        for name, changes in cases.items():
            with self.subTest(name):
                response = self.client.post(reverse("habits:habit-create"), {**self.payload, **changes}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_own_with_pagination(self) -> None:
        for _ in range(6):
            make_habit(self.user)
        make_habit(self.other)

        response = self.client.get(reverse("habits:habit-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 6)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["next"])

        response = self.client.get(reverse("habits:habit-list"), {"limit": 2, "offset": 4})
        self.assertEqual(len(response.data["results"]), 2)

    def test_public_list(self) -> None:
        make_habit(self.other, is_public=True)
        make_habit(self.other, is_public=False)
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("habits:habit-public"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_public_list_is_read_only(self) -> None:
        response = self.client.post(reverse("habits:habit-public"), self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_retrieve_and_update_own(self) -> None:
        habit = make_habit(self.user)
        url = reverse("habits:habit-detail", args=[habit.pk])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        response = self.client.patch(url, {"action": "ходить пешком"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        habit.refresh_from_db()
        self.assertEqual(habit.action, "ходить пешком")

    def test_update_foreign_forbidden(self) -> None:
        habit = make_habit(self.other)
        url = reverse("habits:habit-detail", args=[habit.pk])
        response = self.client.patch(url, {"action": "взлом"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own(self) -> None:
        habit = make_habit(self.user)
        response = self.client.delete(reverse("habits:habit-delete", args=[habit.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.exists())

    def test_delete_foreign_forbidden(self) -> None:
        habit = make_habit(self.other)
        response = self.client.delete(reverse("habits:habit-delete", args=[habit.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Habit.objects.filter(pk=habit.pk).exists())

    def test_str(self) -> None:
        habit = make_habit(self.user)
        self.assertIn("пить воду", str(habit))

    def test_docs_schema(self) -> None:
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ServicesTests(TestCase):
    @patch("habits.services.requests.post")
    def test_send_telegram_message(self, mock_post: MagicMock) -> None:
        send_telegram_message("123", "привет")
        mock_post.assert_called_once()
        mock_post.return_value.raise_for_status.assert_called_once()

    def test_build_reminder_text(self) -> None:
        user = User.objects.create_user(email="user@example.com", password="pass12345")
        pleasant = make_habit(user, is_pleasant=True, reward=None, action="принять ванну")

        with_reward = make_habit(user)
        self.assertIn("Награда: кофе", build_reminder_text(with_reward))

        with_related = make_habit(user, reward=None, related_habit=pleasant)
        self.assertIn("принять ванну", build_reminder_text(with_related))

        plain = make_habit(user, reward=None)
        self.assertEqual(build_reminder_text(plain), "Я буду пить воду в 09:30 в дома.")


FIXED_NOW = timezone.make_aware(datetime(2026, 10, 28, 9, 30))


@patch("habits.tasks.send_telegram_message")
@patch("habits.tasks.timezone.localtime", return_value=FIXED_NOW)
class ReminderTaskTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="user@example.com", password="pass12345", tg_chat_id="123456789")
        self.today = FIXED_NOW.date()

    def test_sends_reminder_and_saves_date(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        habit = make_habit(self.user)
        send_habit_reminders()
        mock_send.assert_called_once()
        habit.refresh_from_db()
        self.assertEqual(habit.last_reminder_date, self.today)

    def test_skips_when_periodicity_not_passed(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        make_habit(self.user, periodicity=2, last_reminder_date=self.today - timedelta(days=1))
        send_habit_reminders()
        mock_send.assert_not_called()

    def test_sends_when_periodicity_passed(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        make_habit(self.user, periodicity=2, last_reminder_date=self.today - timedelta(days=2))
        send_habit_reminders()
        mock_send.assert_called_once()

    def test_skips_wrong_time(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        make_habit(self.user, time=time(10, 0))
        send_habit_reminders()
        mock_send.assert_not_called()

    def test_skips_pleasant_habit(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        make_habit(self.user, is_pleasant=True, reward=None)
        send_habit_reminders()
        mock_send.assert_not_called()

    def test_skips_user_without_chat_id(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        user = User.objects.create_user(email="nochat@example.com", password="pass12345")
        make_habit(user)
        send_habit_reminders()
        mock_send.assert_not_called()

    def test_telegram_error_does_not_break_task(self, mock_now: MagicMock, mock_send: MagicMock) -> None:
        mock_send.side_effect = requests.RequestException("boom")
        habit = make_habit(self.user)
        with self.assertLogs("habits.tasks", level="ERROR"):
            send_habit_reminders()
        habit.refresh_from_db()
        self.assertIsNone(habit.last_reminder_date)
