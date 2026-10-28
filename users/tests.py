from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class UserAPITests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="user@example.com", password="pass12345")

    def test_register(self) -> None:
        response = self.client.post(
            reverse("users:register"),
            {"email": "new@example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        created = User.objects.get(email="new@example.com")
        self.assertTrue(created.check_password("pass12345"))

    def test_register_short_password(self) -> None:
        response = self.client.post(
            reverse("users:register"),
            {"email": "new@example.com", "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self) -> None:
        response = self.client.post(
            reverse("users:register"),
            {"email": "user@example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login(self) -> None:
        response = self.client.post(
            reverse("users:login"),
            {"email": "user@example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self) -> None:
        response = self.client.post(
            reverse("users:login"),
            {"email": "user@example.com", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_auth(self) -> None:
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_and_update(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@example.com")

        response = self.client.patch(
            reverse("users:profile"),
            {"tg_chat_id": "123456789", "email": "hacker@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.tg_chat_id, "123456789")
        self.assertEqual(self.user.email, "user@example.com")


class UserModelTests(APITestCase):
    def test_str(self) -> None:
        user = User.objects.create_user(email="user@example.com", password="pass12345")
        self.assertEqual(str(user), "user@example.com")

    def test_create_user_without_email(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass12345")

    def test_create_superuser(self) -> None:
        admin = User.objects.create_superuser(email="admin@example.com", password="pass12345")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
