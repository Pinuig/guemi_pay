from django.contrib import admin

from .models import AggregatorCallLog, Order


class CallLogInline(admin.TabularInline):
    model = AggregatorCallLog
    extra = 0
    readonly_fields = ("direction", "succeeded", "http_status", "response_payload", "created_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "service_type", "recipient_label", "recipient_number",
        "amount", "payment_method", "status", "created_at",
    )
    list_filter = ("service_type", "status", "payment_method")
    search_fields = ("id", "user__phone", "recipient_number", "collector_reference", "aggregator_reference")
    readonly_fields = [f.name for f in Order._meta.fields]
    inlines = [CallLogInline]

    def has_add_permission(self, request):
        # Orders are created through checkout, never by hand.
        return False
