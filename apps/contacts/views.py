from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contacts.models import Contact
from apps.contacts.serializers import ContactSerializer


class ContactView(APIView):
    """
    Для управления контактной информацией пользователя.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение контактов авторизованного пользователя.
        """
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Log in required"}, status=403)
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Создание нового контакта для авторизованного пользователя.
        Ограничение: Максимум 5 контактов на одного пользователя.
        """
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Log in required"}, status=403)

        if Contact.objects.filter(user=request.user).count() >= 5:
            return Response({"status": False, "error": "Максимум 5 адресов разрешено"})

        if {"phone"}.issubset(request.data):
            data = request.data.copy()
            data["user"] = request.user.id
            serializer = ContactSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response({"status": True})
            else:
                return Response({"status": False, "error": serializer.errors})

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )

    def delete(self, request, *args, **kwargs):
        """
        Удаление контактов пользователя.
        """
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Log in required"}, status=403)

        items_string = request.data.get("items")
        if items_string:
            items_list = items_string.split(",")
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return Response({"status": True, "Удалено объектов": deleted_count})
        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )

    def put(self, request, *args, **kwargs):
        """
        Обновление данных существующего контакта.
        """
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Log in required"}, status=403)

        if "id" in request.data:
            if request.data["id"].isdigit():
                contact = Contact.objects.filter(
                    id=request.data["id"], user_id=request.user.id
                ).first()

                if contact:
                    serializer = ContactSerializer(
                        contact, data=request.data, partial=True
                    )
                    if serializer.is_valid():
                        serializer.save()
                        return Response({"status": True})
                    else:
                        return Response({"status": False, "error": serializer.errors})

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )
