from rest_framework.permissions import BasePermission

from .utils import decodeJWT


class IsAuthenticatedCustom(BasePermission):
    def has_permission(self, request, view):
        auth_token = request.META.get("HTTP_AUTHORIZATION", None)
        if not auth_token:
            return False

        user = decodeJWT(auth_token)

        if not user:
            return False

        request.user = user
        return True