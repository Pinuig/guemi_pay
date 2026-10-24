from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .choices import OrderStatus
from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer
from .tasks import mark_paid_and_fulfill, start_collection


class OrderCreateView(APIView):
    """
    POST /api/payments/orders/
    Validates + prices the order server-side, creates it, and hands off to
    Celery to actually collect payment. Returns immediately with status
    "created" / "payment_pending" — the client polls OrderDetailView (or
    listens for a push notification) rather than blocking on this request,
    because mobile money approval can take anywhere from 2 seconds to a
    couple of minutes.
    """
    throttle_scope = "order-create"

    def post(self, request):
        idempotency_key = request.data.get("idempotency_key")
        if idempotency_key:
            existing = Order.objects.filter(user=request.user, idempotency_key=idempotency_key).first()
            if existing:
                return Response(OrderSerializer(existing).data, status=status.HTTP_200_OK)

        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                idempotency_key=data["idempotency_key"],
                service_type=data["service_type"],
                operator=data.get("_operator", data.get("operator", "")),
                data_bundle=data.get("_bundle"),
                canal_plan=data.get("_plan"),
                canal_months=data.get("canal_months"),
                account_type=data.get("account_type", ""),
                recipient_number=data["recipient_number"],
                recipient_label=data["_label"],
                amount=data["_amount"],
                payment_method=data["payment_method"],
                payer_number=data.get("payer_number", ""),
            )
        start_collection.delay(str(order.id))
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderListView(generics.ListAPIView):
    """Purchase history — also what backs the app's "recent payments" list."""
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = Order.objects.filter(user=self.request.user)
        service_type = self.request.query_params.get("service_type")
        if service_type:
            qs = qs.filter(service_type=service_type)
        return qs


class PaymentWebhookView(APIView):
    """
    Callback from the mobile money collector confirming a charge.
    AllowAny because the caller is the collector, not a logged-in user —
    protect this with the collector's own signature verification in
    production (HMAC header check against AGGREGATOR_API_SECRET) before
    trusting the payload.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        reference = request.data.get("transactionId") or request.data.get("reference")
        collector_status = request.data.get("status")
        order = Order.objects.filter(collector_reference=reference).first()
        if not order:
            return Response({"detail": "unknown reference"}, status=status.HTTP_404_NOT_FOUND)

        if order.status != OrderStatus.PAYMENT_PENDING:
            return Response({"detail": "already processed"}, status=status.HTTP_200_OK)

        if str(collector_status).upper() in ("SUCCESS", "SUCCEEDED"):
            mark_paid_and_fulfill(order)
        else:
            order.status = OrderStatus.PAYMENT_FAILED
            order.failure_reason = "Payment was declined."
            order.save(update_fields=["status", "failure_reason", "updated_at"])

        return Response({"detail": "ok"})
