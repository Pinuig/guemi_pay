from rest_framework import permissions, viewsets

from .models import AirtimeRule, CanalPlan, DataBundle, UtilityServiceConfig
from .serializers import (
    AirtimeRuleSerializer,
    CanalPlanSerializer,
    DataBundleSerializer,
    UtilityServiceConfigSerializer,
)

# Catalog browsing is public: a customer should see prices before logging in,
# same as any storefront. Only checkout (apps.payments) requires auth.


class DataBundleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DataBundleSerializer
    permission_classes = [permissions.AllowAny]
    queryset = DataBundle.objects.filter(is_active=True)

    def get_queryset(self):
        qs = super().get_queryset()
        operator = self.request.query_params.get("operator")
        period = self.request.query_params.get("period")
        if operator:
            qs = qs.filter(operator=operator)
        if period:
            qs = qs.filter(period=period)
        return qs


class AirtimeRuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AirtimeRuleSerializer
    permission_classes = [permissions.AllowAny]
    queryset = AirtimeRule.objects.filter(is_active=True)
    lookup_field = "operator"


class CanalPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CanalPlanSerializer
    permission_classes = [permissions.AllowAny]
    queryset = CanalPlan.objects.filter(is_active=True)


class UtilityServiceConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UtilityServiceConfigSerializer
    permission_classes = [permissions.AllowAny]
    queryset = UtilityServiceConfig.objects.filter(is_active=True)
    lookup_field = "service_type"
