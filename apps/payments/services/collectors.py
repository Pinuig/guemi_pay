"""
Payment collection: getting money FROM the customer.

In production this calls your PSP/mobile-money collection API (often the
same aggregator that does fulfillment, e.g. Smobilpay's collection API, or
a dedicated MoMo/Orange Money merchant API). Mobile money collection is
normally asynchronous: you request a charge, the customer approves a
prompt on their phone, and you get a webhook later — so `request_payment`
returns "pending" and the real answer arrives at `PaymentWebhookView`.

Swap MockCollector for a real implementation once merchant credentials
exist; the interface (`request_payment` / `check_status`) is what the
rest of the codebase depends on, not the implementation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from django.conf import settings

CollectionStatus = Literal["pending", "succeeded", "failed"]


@dataclass
class CollectionResult:
    reference: str
    status: CollectionStatus
    raw: dict


class BaseCollector:
    def request_payment(self, *, payer_number: str, amount: int, method: str, order_id: str) -> CollectionResult:
        raise NotImplementedError

    def check_status(self, reference: str) -> CollectionResult:
        raise NotImplementedError

    def refund(self, reference: str, amount: int) -> CollectionResult:
        raise NotImplementedError


class MockCollector(BaseCollector):
    """Deterministic fake used in dev/tests: never blocks, always succeeds."""

    def request_payment(self, *, payer_number, amount, method, order_id):
        ref = f"MOCK-COL-{uuid.uuid4().hex[:10].upper()}"
        return CollectionResult(reference=ref, status="pending", raw={
            "payer_number": payer_number, "amount": amount, "method": method, "order_id": order_id,
        })

    def check_status(self, reference):
        # A real webhook would flip this; in mock mode we just say yes.
        return CollectionResult(reference=reference, status="succeeded", raw={"mock": True})

    def refund(self, reference, amount):
        return CollectionResult(reference=f"{reference}-REFUND", status="succeeded", raw={"amount": amount})


class SmobilpayCollector(BaseCollector):
    """
    Sketch of a real collector using an aggregator's collection API.
    Fill in the exact endpoint paths/signing scheme from your merchant
    documentation — Smobilpay/PayUnit-style APIs typically sign requests
    with an HMAC over the request using your API key/secret pair.
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

    def request_payment(self, *, payer_number, amount, method, order_id):
        import json
        payload = {
            "payer_number": payer_number,
            "amount": amount,
            "channel": method,  # e.g. "momo" / "om"
            "merchant_reference": order_id,
        }
        body = json.dumps(payload).encode()
        resp = self.session.post(f"{self.base_url}/collect", data=body, headers=self._headers(body), timeout=15)
        data = resp.json()
        status = "pending" if resp.status_code in (200, 202) else "failed"
        return CollectionResult(reference=data.get("transactionId", ""), status=status, raw=data)

    def check_status(self, reference):
        resp = self.session.get(f"{self.base_url}/collect/{reference}", headers=self._headers(b""), timeout=15)
        data = resp.json()
        mapped = {"SUCCESS": "succeeded", "FAILED": "failed"}.get(data.get("status"), "pending")
        return CollectionResult(reference=reference, status=mapped, raw=data)

    def refund(self, reference, amount):
        body = f'{{"transactionId":"{reference}","amount":{amount}}}'.encode()
        resp = self.session.post(f"{self.base_url}/refund", data=body, headers=self._headers(body), timeout=15)
        data = resp.json()
        status = "succeeded" if resp.status_code == 200 else "failed"
        return CollectionResult(reference=reference, status=status, raw=data)


def get_collector() -> BaseCollector:
    if settings.AGGREGATOR_MODE == "mock":
        return MockCollector()
    return SmobilpayCollector()
