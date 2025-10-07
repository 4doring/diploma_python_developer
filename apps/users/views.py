from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework.authtoken.models import Token
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import ConfirmEmailToken
from apps.users.serializers import UserSerializer


class RegisterAccount(APIView):
    """
    Регистрация нового пользователя (покупателя или магазина)
    """

    def post(self, request, *args, **kwargs):
        """
        Регистрирует нового пользователя на основе переданных данных.
        Обязательные поля: 'email', 'password'.
        Остальные поля (first_name, last_name, company, position, type) — необязательны.
        """

        if {"email", "password"}.issubset(request.data):
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return Response({"status": False, "error": {"password": error_array}})
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data["password"])
                    user.save()
                    return Response({"status": True})
                else:
                    return Response({"status": False, "error": user_serializer.errors})

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )


class ConfirmAccount(APIView):
    """
    Подтверждение email-адреса пользователя по токену.
    """

    def post(self, request, *args, **kwargs):
        """
        Активирует учётную запись пользователя, если переданы корректные email и токен.

        """
        if {"email", "token"}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(
                user__email=request.data["email"], key=request.data["token"]
            ).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return Response({"status": True})
            else:
                return Response(
                    {"status": False, "error": "Неправильно указан токен или email"}
                )

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )


class AccountDetails(APIView):
    """
    Управление данными авторизованного пользователя.
    """

    def get(self, request: Request, *args, **kwargs):
        """
        Возвращает данные авторизованного пользователя.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Обновляет профиль авторизованного пользователя.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        if "password" in request.data:
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return Response({"status": False, "error": {"password": error_array}})
            else:
                request.user.set_password(request.data["password"])

        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response({"status": True})
        else:
            return Response({"status": False, "error": user_serializer.errors})


class LoginAccount(APIView):
    """
    Авторизация пользователя по email и паролю.
    """

    def post(self, request, *args, **kwargs):
        """
        Выполняет вход пользователя по email и паролю.
        Возвращает токен аутентификации при успешной авторизации пользователя.

        """
        if {"email", "password"}.issubset(request.data):
            user = authenticate(
                request,
                username=request.data["email"],
                password=request.data["password"],
            )

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return Response({"status": True, "Token": token.key})

            return Response({"status": False, "error": "Не удалось авторизовать"})

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )
