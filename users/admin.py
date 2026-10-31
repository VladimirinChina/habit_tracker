from django.contrib import admin

from users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "email", "tg_chat_id", "is_staff")
    search_fields = ("email",)
