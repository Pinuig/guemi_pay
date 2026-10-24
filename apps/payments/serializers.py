from rest_framework import serializers

from apps.catalog.choices import ServiceType
from apps.catalog.models import AirtimeRule, CanalPlan, DataBundle, UtilityServiceConfig

from .choices import PaymentMethod
from .models import AggregatorCallLog, Order
from .validators import PAYMENT_METHOD_OPERATOR, detect_operator, normalize_cm_number


class OrderCreateSerializer(serializers.Serializer):
    """
    Deliberately NOT a ModelSerializer: the client sends what it *wants*
    to buy and how it will pay, but price, recipient_label and the actual
    FK links are all resolved from the catalog here — never trusted from
    the request body. This is what stops a tampered client from buying a
    30 GB bundle for 200 FCFA.
    """
    idempotency_key = serializers.CharField(max_length=64)
    service_type = serializers.ChoiceField(choices=ServiceType.choices)

    # data
    operator = serializers.CharField(required=False, allow_blank=True)
    data_bundle_id = serializers.IntegerField(required=False)

    # airtime
    amount = serializers.IntegerField(required=False)

    # canal
    canal_plan_id = serializers.IntegerField(required=False)
    canal_months = serializers.IntegerField(required=False, min_value=1, max_value=12)

    # eneo
    account_type = serializers.CharField(required=False, allow_blank=True)

    # recipient — entered twice on the client; both copies arrive here and
    # must already match, but we re-check rather than trust the client did.
    recipient_number = serializers.CharField(max_length=32)
    recipient_number_confirm = serializers.CharField(max_length=32)

    # payer
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    payer_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    payer_number_confirm = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def validate(self, attrs):
        service_type = attrs["service_type"]

        if normalize_cm_number(attrs["recipient_number"]) != normalize_cm_number(attrs["recipient_number_confirm"]) \
                and attrs["recipient_number"] != attrs["recipient_number_confirm"]:
            raise serializers.ValidationError({"recipient_number_confirm": "Recipient numbers do not match."})

        method = attrs["payment_method"]
        if method != PaymentMethod.CARD:
            payer = attrs.get("payer_number", "")
            payer_confirm = attrs.get("payer_number_confirm", "")
            if not payer:
                raise serializers.ValidationError({"payer_number": "Required for this payment method."})
            if normalize_cm_number(payer) != normalize_cm_number(payer_confirm):
                raise serializers.ValidationError({"payer_number_confirm": "Payer numbers do not match."})
            required_operator = PAYMENT_METHOD_OPERATOR[method]
            detected = detect_operator(payer)
            if not detected:
                raise serializers.ValidationError({"payer_number": "Not a valid Cameroon mobile number."})
            if required_operator != "any" and detected != required_operator:
                raise serializers.ValidationError(
                    {"payer_number": f"{dict(PaymentMethod.choices)[method]} needs an {required_operator} number."}
                )

        if service_type == ServiceType.DATA:
            self._validate_data(attrs)
        elif service_type == ServiceType.AIRTIME:
            self._validate_airtime(attrs)
        elif service_type == ServiceType.CANAL:
            self._validate_canal(attrs)
        else:
            self._validate_utility(attrs)

        return attrs

    def _validate_data(self, attrs):
        try:
            bundle = DataBundle.objects.get(id=attrs.get("data_bundle_id"), is_active=True)
        except DataBundle.DoesNotExist:
            raise serializers.ValidationError({"data_bundle_id": "Unknown or inactive bundle."})
        recipient_operator = detect_operator(attrs["recipient_number"])
        if not recipient_operator:
            raise serializers.ValidationError({"recipient_number": "Not a valid Cameroon mobile number."})
        if recipient_operator != bundle.operator:
            raise serializers.ValidationError(
                {"recipient_number": f"This number belongs to {recipient_operator}, not {bundle.operator}."}
            )
        attrs["_bundle"] = bundle
        attrs["_amount"] = bundle.price
        attrs["_label"] = f"{bundle.operator} {bundle.data_label} · {bundle.validity_label}"
        attrs["_operator"] = bundle.operator

    def _validate_airtime(self, attrs):
        operator = detect_operator(attrs["recipient_number"])
        if not operator:
            raise serializers.ValidationError({"recipient_number": "Not a valid Cameroon mobile number."})
        try:
            rule = AirtimeRule.objects.get(operator=operator, is_active=True)
        except AirtimeRule.DoesNotExist:
            raise serializers.ValidationError({"recipient_number": f"Airtime top-up isn't available for {operator}."})
        amount = attrs.get("amount")
        if not amount or not (rule.min_amount <= amount <= rule.max_amount):
            raise serializers.ValidationError(
                {"amount": f"Amount must be between {rule.min_amount} and {rule.max_amount} FCFA for {operator}."}
            )
        attrs["_amount"] = amount
        attrs["_label"] = f"{operator} airtime"
        attrs["_operator"] = operator

    def _validate_canal(self, attrs):
        try:
            plan = CanalPlan.objects.get(id=attrs.get("canal_plan_id"), is_active=True)
        except CanalPlan.DoesNotExist:
            raise serializers.ValidationError({"canal_plan_id": "Unknown or inactive Canal+ plan."})
        months = attrs.get("canal_months") or 1
        config = self._utility_config(ServiceType.CANAL)
        self._check_reference_length(attrs["recipient_number"], config, "recipient_number")
        attrs["_plan"] = plan
        attrs["_amount"] = plan.monthly_price * months
        attrs["_label"] = f"Canal+ {plan.name} · {months} month{'s' if months > 1 else ''}"
        attrs["canal_months"] = months

    def _validate_utility(self, attrs):
        service_type = attrs["service_type"]
        config = self._utility_config(service_type)
        self._check_reference_length(attrs["recipient_number"], config, "recipient_number")
        amount = attrs.get("amount")
        if not amount or amount < config.min_amount:
            raise serializers.ValidationError({"amount": f"Minimum amount is {config.min_amount} FCFA."})
        label = config.get_service_type_display()
        if service_type == ServiceType.ENEO:
            account_type = attrs.get("account_type") or config.account_type or "prepaid"
            label = f"ENEO {account_type}"
            attrs["account_type"] = account_type
        attrs["_amount"] = amount
        attrs["_label"] = label

    def _utility_config(self, service_type):
        try:
            return UtilityServiceConfig.objects.get(service_type=service_type, is_active=True)
        except UtilityServiceConfig.DoesNotExist:
            raise serializers.ValidationError({"service_type": "This service is not configured yet."})

    def _check_reference_length(self, value, config, field):
        digits = "".join(ch for ch in value if ch.isdigit())
        if not (config.reference_min_length <= len(digits) <= config.reference_max_length):
            raise serializers.ValidationError(
                {field: f"{config.reference_label} must be {config.reference_min_length}"
                        f"–{config.reference_max_length} digits."}
            )


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id", "service_type", "operator", "recipient_number", "recipient_label",
            "amount", "payment_method", "status", "failure_reason",
            "aggregator_reference", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AggregatorCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AggregatorCallLog
        fields = ["direction", "succeeded", "http_status", "created_at"]
