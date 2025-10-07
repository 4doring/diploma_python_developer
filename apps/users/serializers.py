from rest_framework import serializers

from apps.contacts.serializers import ContactSerializer
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "position",
            "contacts",
            "type",
            "password",
        )
        read_only_fields = ("id",)
