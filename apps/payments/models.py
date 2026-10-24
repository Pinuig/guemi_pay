import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.choices import ServiceType
from apps.catalog.models import CanalPlan, DataBundle

from .choices import OrderStatus, PaymentMethod


class Order(models.Model):
    """
    One checkout: one thing bought, for one recipient, paid one way.
    This is the single source of truth for money movement — the frontend
    never decides success, only this model (updated by Celery tasks) does.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")

    # Prevents double-submit from a flaky network or a double-tap: the
    # client generates this once per checkout attempt and resends it on
    # retry, so a repeat request returns the existing order instead of
    # creating (and charging) a second one.
    idempotency_key = models.CharField(max_length=64, unique=True)

    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    operator = models.CharField(max_length=10, blank=True, help_text="For data/airtime orders.")
    data_bundle = models.ForeignKey(DataBundle, null=True, blank=True, on_delete=models.PROTECT)
    canal_plan = models.ForeignKey(CanalPlan, null=True, blank=True, on_delete=models.PROTECT)
    canal_months = models.PositiveSmallIntegerField(null=True, blank=True)
    account_type = models.CharField(max_length=10, blank=True, help_text="ENEO: prepaid/postpaid.")

    # Recipient: what/who receives the service. Verified twice client-side;
    # stored once here, exactly as the aggregator needs it.
    recipient_number = models.CharField(max_length=32)
    recipient_label = models.CharField(max_length=120, help_text="Human-readable item, e.g. 'MTN 1 GB / 30 days'.")

    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    payer_number = models.CharField(max_length=32, blank=True, help_text="Blank for card payments.")

    status = models.CharField(max_length=24, choices=OrderStatus.choices, default=OrderStatus.CREATED)
    failure_reason = models.CharField(max_length=200, blank=True)

    collector_reference = models.CharField(max_length=80, blank=True, help_text="MoMo/Orange/card charge id.")
    aggregator_reference = models.CharField(max_length=80, blank=True, help_text="Fulfillment id from the aggregator.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.id} · {self.recipient_label} · {self.status}"

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            OrderStatus.COMPLETED,
            OrderStatus.PAYMENT_FAILED,
            OrderStatus.FULFILLMENT_FAILED,
            OrderStatus.REFUNDED,
        }


class AggregatorCallLog(models.Model):
    """
    Raw snapshot of every outbound call to the payment collector or the
    service aggregator. This is what support and reconciliation actually
    run on when a customer says "I paid but got nothing" — never delete it.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="call_logs")
    direction = models.CharField(max_length=10, choices=[("collect", "Collection"), ("fulfill", "Fulfillment")])
    request_payload = models.JSONField()
    response_payload = models.JSONField(null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
