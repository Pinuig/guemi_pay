import logging

from celery import shared_task
from django.utils import timezone

from .choices import OrderStatus
from .models import AggregatorCallLog, Order
from .services.aggregator import get_aggregator
from .services.collectors import get_collector

logger = logging.getLogger("apps.payments")


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def start_collection(self, order_id: str):
    """Step 1: ask the payment collector to charge the payer."""
    order = Order.objects.select_related().get(id=order_id)
    if order.status != OrderStatus.CREATED:
        return  # already progressed — idempotency guard against duplicate task runs

    collector = get_collector()
    try:
        result = collector.request_payment(
            payer_number=order.payer_number, amount=order.amount,
            method=order.payment_method, order_id=str(order.id),
        )
    except Exception as exc:
        logger.exception("Collection request failed for order %s", order_id)
        raise self.retry(exc=exc)

    AggregatorCallLog.objects.create(
        order=order, direction="collect", request_payload={"amount": order.amount, "method": order.payment_method},
        response_payload=result.raw, succeeded=result.status != "failed",
    )

    if result.status == "failed":
        order.status = OrderStatus.PAYMENT_FAILED
        order.failure_reason = "Payment was declined."
        order.save(update_fields=["status", "failure_reason", "updated_at"])
        return

    order.collector_reference = result.reference
    order.status = OrderStatus.PAYMENT_PENDING
    order.save(update_fields=["collector_reference", "status", "updated_at"])

    # Card payments and some collectors resolve synchronously via webhook;
    # for phone-approval flows, poll as a safety net in case the webhook
    # is delayed or missed.
    poll_collection_status.apply_async(args=[str(order.id)], countdown=8)


@shared_task(bind=True, max_retries=20, default_retry_delay=8)
def poll_collection_status(self, order_id: str):
    order = Order.objects.get(id=order_id)
    if order.status != OrderStatus.PAYMENT_PENDING:
        return

    collector = get_collector()
    result = collector.check_status(order.collector_reference)

    if result.status == "pending":
        raise self.retry()
    if result.status == "failed":
        order.status = OrderStatus.PAYMENT_FAILED
        order.failure_reason = "Payer did not approve the payment in time."
        order.save(update_fields=["status", "failure_reason", "updated_at"])
        return

    mark_paid_and_fulfill(order)


def mark_paid_and_fulfill(order: Order):
    order.status = OrderStatus.PAID
    order.save(update_fields=["status", "updated_at"])
    fulfill_order.delay(str(order.id))


@shared_task(bind=True, max_retries=5, default_retry_delay=20)
def fulfill_order(self, order_id: str):
    """Step 2: money is in hand — now deliver the bundle/subscription/bill payment."""
    order = Order.objects.get(id=order_id)
    if order.status not in (OrderStatus.PAID, OrderStatus.FULFILLING):
        return

    order.status = OrderStatus.FULFILLING
    order.save(update_fields=["status", "updated_at"])

    aggregator = get_aggregator()
    try:
        result = aggregator.fulfill(order)
    except Exception as exc:
        logger.exception("Fulfillment failed for order %s", order_id)
        # Fulfillment errors are retried — money is already collected, so
        # silently giving up would mean taking payment for nothing.
        raise self.retry(exc=exc)

    AggregatorCallLog.objects.create(
        order=order, direction="fulfill", request_payload={"recipient": order.recipient_number},
        response_payload=result.raw, succeeded=result.status == "succeeded",
    )

    if result.status == "succeeded":
        order.status = OrderStatus.COMPLETED
        order.aggregator_reference = result.reference
        order.save(update_fields=["status", "aggregator_reference", "updated_at"])
    else:
        order.status = OrderStatus.FULFILLMENT_FAILED
        order.failure_reason = "The provider could not complete delivery."
        order.save(update_fields=["status", "failure_reason", "updated_at"])
        refund_order.delay(str(order.id))


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def refund_order(self, order_id: str):
    """Money was collected but delivery failed: send it back automatically."""
    order = Order.objects.get(id=order_id)
    if order.status != OrderStatus.FULFILLMENT_FAILED:
        return

    order.status = OrderStatus.REFUNDING
    order.save(update_fields=["status", "updated_at"])

    collector = get_collector()
    try:
        result = collector.refund(order.collector_reference, order.amount)
    except Exception as exc:
        raise self.retry(exc=exc)

    order.status = OrderStatus.REFUNDED if result.status == "succeeded" else OrderStatus.FULFILLMENT_FAILED
    order.save(update_fields=["status", "updated_at"])


@shared_task
def reconcile_stuck_orders():
    """
    Periodic safety net (wire this to Celery beat, e.g. every 5 minutes).
    Anything sitting in a non-terminal state too long gets nudged forward
    instead of silently vanishing — the single most important habit for a
    money-moving app.
    """
    stale_before = timezone.now() - timezone.timedelta(minutes=10)
    stuck = Order.objects.filter(status=OrderStatus.PAYMENT_PENDING, updated_at__lt=stale_before)
    for order in stuck:
        poll_collection_status.delay(str(order.id))

    stuck_fulfillment = Order.objects.filter(status=OrderStatus.PAID, updated_at__lt=stale_before)
    for order in stuck_fulfillment:
        fulfill_order.delay(str(order.id))
