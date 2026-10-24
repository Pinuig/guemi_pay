from django.urls import path

from . import views

urlpatterns = [
    path("orders/", views.OrderCreateView.as_view(), name="order-create"),
    path("orders/history/", views.OrderListView.as_view(), name="order-list"),
    path("orders/<uuid:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("webhooks/collector/", views.PaymentWebhookView.as_view(), name="collector-webhook"),
]
