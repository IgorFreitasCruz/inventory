from datetime import datetime

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from inventory_api.custom_methods import IsAuthenticatedCustom
from inventory_api.utils import get_access_token

from .models import CustomUser, UserActivities
from .serializers import (CreateUserSerializer, CustomUserSerializer,
                          LoginSerializer, UpdatePasswordSerializer,
                          UserActivitiesSerializer)


def add_user_activity(user, action):
    UserActivities.objects.create(
        user_id=user.id,
        email=user.email,
        fullname=user.fullname,
        action=action
    )


class CreateUserView(ModelViewSet):

    http_method_names = ["post"]
    queryset = CustomUser.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def create(self, request):
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)
        CustomUser.objects.create(**valid_request.validated_data)

        add_user_activity(request.user, "criou novo usuário")

        return Response(
            {"Success": "User created successfully"}, status=status.HTTP_201_CREATED
        )


class LoginView(ModelViewSet):

    http_method_names = ["post"]
    queryset = CustomUser.objects.all()
    serializer_class = LoginSerializer

    def create(self, request):
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)

        new_user = valid_request.validated_data["is_new_user"]

        if new_user:
            user = CustomUser.objects.filter(email=valid_request["email"])

            if user:
                user = user.first()
                if not user.password:
                    return Response({"user_id": user.id})
                else:
                    raise Exception("User already have a password")
            else:
                raise Exception("User email not found")

        user = authenticate(
            username=valid_request.validated_data["email"],
            password=valid_request.validated_data.get("password", None),
        )

        if not user:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access = get_access_token({"user_id": user.id}, 1)

        user.last_login = datetime.now()
        user.save()

        add_user_activity(user, "fez login")

        return Response({"access": access})


class UpdatePasswordView(ModelViewSet):

    http_method_names = ["post"]
    queryset = CustomUser.objects.all()
    serializer_class = UpdatePasswordSerializer

    def create(self, request):
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)

        user = CustomUser.objects.fitler(id=valid_request.validated_data["user_id"])

        if not user:
            raise Exception("User not found")

        user = user.first()
        user.set_password(valid_request.validated_data["password"])
        user.save()

        add_user_activity(user, "atualizou a senha")

        return Response({"success": "Senha alterada com sucesso"})


class MeView(ModelViewSet):
    http_method_names = ["get"]
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request):
        data = self.serializer_class(request.user).data
        return Response(data)


class UserActivitiesView(ModelViewSet):

    http_method_names = ["get"]
    queryset = UserActivities.objects.all()
    serializer_class = UserActivitiesSerializer
    permission_classes = (IsAuthenticatedCustom,)


class UsersView(ModelViewSet):
    http_method_names = ["get"]
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request):
        users = self.queryset().filter(is_superuser=False)
        data = self.serializer_class(users, many=True).data
        return Response(data)
