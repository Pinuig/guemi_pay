"""
Fulfillment: delivering the thing the customer paid for.

This is what actually credits a phone with data/airtime, renews a Canal+
subscription, or tops up an ENEO/CAMWATER account, by calling the digital
service aggregator your business has a merchant agreement with (Smobilpay
by Maviance and PayUnit both offer this kind of unified API in Cameroon).

Only ever call `fulfill()` AFTER payment collection has succeeded — never
before. The mapping from Order -> aggregator product code lives here so
the rest of the codebase doesn't need to know the aggregator's vocabulary.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from django.conf import settings

from apps.catalog.choices import ServiceType

FulfillmentStatus = Literal["succeeded", "failed"]


@dataclass
class FulfillmentResult:
    reference: str
    status: FulfillmentStatus
    raw: dict


class BaseAggregator:
    def fulfill(self, order) -> FulfillmentResult:
        raise NotImplementedError


class MockAggregator(BaseAggregator):
    def fulfill(self, order):
        ref = f"MOCK-FUL-{uuid.uuid4().hex[:10].upper()}"
        return FulfillmentResult(reference=ref, status="succeeded", raw={
            "service_type": order.service_type, "recipient": order.recipient_number, "amount": order.amount,
        })


class SmobilpayAggregator(BaseAggregator):
    """
    Sketch of a real integration. Each service type maps to a different
    aggregator product/service code — read those off your merchant
    dashboard and store them on the catalog rows (see
    apps.catalog.models: aggregator_product_code / aggregator_service_code)
    rather than hardcoding them here.
    """

    def __init__(self):
        import requests
        self.session = requests.Session()
        self.base_url = settings.AGGREGATOR_BASE_URL
        self.api_key = settings.AGGREGATOR_API_KEY
        self.api_secret = settings.AGGREGATOR_API_SECRET

    def _headers(self, body: bytes) -> dict:
        import hashlib
        import hmac
        signature = hmac.new(self.api_secret.encode(), body, hashlib.sha256).hexdigest()
        return {"X-Api-Key": self.api_key, "X-Signature": signature, "Content-Type": "application/json"}

    def _product_code(self, order) -> str:
        if order.service_type == ServiceType.DATA:
            return order.data_bundle.aggregator_product_code
        if order.service_type == ServiceType.CANAL:
            return order.canal_plan.aggregator_product_code
        # Airtime, ENEO, water: resolved from their config rows.
        from apps.catalog.models import AirtimeRule, UtilityServiceConfig
        if order.service_type == ServiceType.AIRTIME:
            return AirtimeRule.objects.get(operator=order.operator).aggregator_product_code
        return UtilityServiceConfig.objects.get(service_type=order.service_type).aggregator_service_code

    def fulfill(self, order):
        import json
        payload = {
            "productCode": self._product_code(order),
            "recipient": order.recipient_number,
            "amount": order.amount,
            "merchantReference": str(order.id),
        }
        body = json.dumps(payload).encode()
        resp = self.session.post(f"{self.base_url}/fulfill", data=body, headers=self._headers(body), timeout=20)
        data = resp.json()
        status = "succeeded" if resp.status_code == 200 and data.get("status") == "SUCCESS" else "failed"
        return FulfillmentResult(reference=data.get("transactionId", ""), status=status, raw=data)


def get_aggregator() -> BaseAggregator:
    if settings.AGGREGATOR_MODE == "mock":
        return MockAggregator()
    return SmobilpayAggregator()
