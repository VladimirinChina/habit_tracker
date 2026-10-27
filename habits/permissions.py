from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwner(BasePermission):
    """Доступ к объекту только у его владельца."""

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return bool(obj.user == request.user)
