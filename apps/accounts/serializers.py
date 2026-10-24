from django.contrib.auth import password_validation
from rest_framework import serializers

from .models import SavedRecipient, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "phone", "password", "preferred_language"]

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "phone", "phone_verified", "preferred_language"]
        read_only_fields = ["phone_verified"]


class SavedRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedRecipient
        fields = ["id", "service_type", "label", "reference_number", "created_at"]
        read_only_fields = ["id", "created_at"]
