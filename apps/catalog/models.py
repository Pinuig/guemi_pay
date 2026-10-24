from django.core.validators import MinValueValidator
from django.db import models

from .choices import AccountType, BundlePeriod, Operator, ServiceType


class DataBundle(models.Model):
    """
    One purchasable data bundle for one operator. Mirrors the aggregator's
    own product code so a purchase can be forwarded without translation.
    """
    operator = models.CharField(max_length=10, choices=Operator.choices)
    period = models.CharField(max_length=1, choices=BundlePeriod.choices)
    data_label = models.CharField(max_length=30, help_text="e.g. '1 GB', '500 MB'")
    validity_label = models.CharField(max_length=20, help_text="e.g. '24 h', '7 days', '30 days'")
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    aggregator_product_code = models.CharField(
        max_length=64, blank=True,
        help_text="Product/SKU code as known by the aggregator (Smobilpay/PayUnit).",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["operator", "period", "price"]
        indexes = [models.Index(fields=["operator", "period", "is_active"])]

    def __str__(self):
        return f"{self.operator} {self.data_label} / {self.validity_label} — {self.price} FCFA"


class AirtimeRule(models.Model):
    """Per-operator bounds for a free-amount airtime top-up."""
    operator = models.CharField(max_length=10, choices=Operator.choices, unique=True)
    min_amount = models.PositiveIntegerField(default=100)
    max_amount = models.PositiveIntegerField(default=50000)
    aggregator_product_code = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.operator} airtime ({self.min_amount}–{self.max_amount})"


class CanalPlan(models.Model):
    name = models.CharField(max_length=40, unique=True)
    monthly_price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    aggregator_product_code = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "monthly_price"]

    def __str__(self):
        return f"Canal+ {self.name} — {self.monthly_price} FCFA/mo"


class UtilityServiceConfig(models.Model):
    """
    Configuration for a non-telco service (ENEO, CAMWATER): reference
    number format, minimum payment, and the aggregator's own service id.
    Kept as data, not code, so ops can adjust rules without a deploy.
    """
    service_type = models.CharField(max_length=20, choices=ServiceType.choices, unique=True)
    account_type = models.CharField(
        max_length=10, choices=AccountType.choices, blank=True,
        help_text="Only meaningful for ENEO (prepaid meter vs postpaid contract).",
    )
    reference_label = models.CharField(max_length=60, help_text="e.g. 'Meter number'")
    reference_min_length = models.PositiveSmallIntegerField(default=6)
    reference_max_length = models.PositiveSmallIntegerField(default=14)
    min_amount = models.PositiveIntegerField(default=500)
    aggregator_service_code = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_service_type_display()
