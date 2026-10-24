from django.db import models


class PaymentMethod(models.TextChoices):
    MOMO = "momo", "MTN Mobile Money"
    ORANGE_MONEY = "om", "Orange Money"
    EXPRESS_UNION = "eu", "Express Union Mobile Money"
    CARD = "card", "Bank card"


class OrderStatus(models.TextChoices):
    CREATED = "created", "Created"
    PAYMENT_PENDING = "payment_pending", "Waiting for payer approval"
    PAID = "paid", "Payment collected"
    FULFILLING = "fulfilling", "Delivering to recipient"
    COMPLETED = "completed", "Completed"
    PAYMENT_FAILED = "payment_failed", "Payment failed"
    FULFILLMENT_FAILED = "fulfillment_failed", "Delivery failed"
    REFUNDING = "refunding", "Refunding"
    REFUNDED = "refunded", "Refunded"
