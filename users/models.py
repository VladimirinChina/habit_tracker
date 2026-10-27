from django.contrib.auth.models import AbstractUser
from django.db import models

from users.managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    tg_chat_id = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Telegram chat id"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email
