from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    """
    Cameroon customers log in with a phone number, not a username.
    `username` is kept (Django needs it) but we authenticate on `phone`.
    """
    phone = PhoneNumberField(unique=True, region="CM")
    phone_verified = models.BooleanField(default=False)
    preferred_language = models.CharField(
        max_length=2, choices=[("en", "English"), ("fr", "Français")], default="fr"
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["phone"]

    def __str__(self):
        return str(self.phone)


class SavedRecipient(models.Model):
    """
    A recipient number/account the user has paid before (a meter number,
    a decoder card, a friend's phone). Surfaced as "recent" shortcuts in
    the app — never auto-filled without the user picking it explicitly,
    since the whole point of GueMi_Pay is deliberate recipient checking.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_recipients")
    service_type = models.CharField(max_length=20)  # matches catalog.ServiceType
    label = models.CharField(max_length=80, blank=True)
    reference_number = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "service_type", "reference_number")

    def __str__(self):
        return f"{self.label or self.reference_number} ({self.service_type})"
