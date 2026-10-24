from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import SavedRecipient, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "phone", "phone_verified", "is_active", "date_joined")
    search_fields = ("username", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("GueMi_Pay", {"fields": ("phone", "phone_verified", "preferred_language")}),
    )


@admin.register(SavedRecipient)
class SavedRecipientAdmin(admin.ModelAdmin):
    list_display = ("user", "service_type", "reference_number", "label", "created_at")
    list_filter = ("service_type",)
    search_fields = ("reference_number", "user__phone")
