from rest_framework import serializers

from .models import AirtimeRule, CanalPlan, DataBundle, UtilityServiceConfig


class DataBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataBundle
        fields = ["id", "operator", "period", "data_label", "validity_label", "price"]


class AirtimeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirtimeRule
        fields = ["operator", "min_amount", "max_amount"]


class CanalPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanalPlan
        fields = ["id", "name", "monthly_price"]


class UtilityServiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityServiceConfig
        fields = [
            "service_type", "account_type", "reference_label",
            "reference_min_length", "reference_max_length", "min_amount",
        ]
