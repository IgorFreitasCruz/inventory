from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CreateUserView, LoginView, MeView, UpdatePasswordView,
                    UserActivitiesView, UsersView)

router = DefaultRouter(trailing_slash=False)

router.register("login", LoginView, "login")
router.register("create-user", CreateUserView, "create-user")
router.register("me", MeView, "me")
router.register("password-update", UpdatePasswordView, "password-update")
router.register("users", UsersView, "users")
router.register("activity-log", UserActivitiesView, "activity-log")


urlpatterns = [
    path("", include(router.urls)),
]
