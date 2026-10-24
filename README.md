# GueMi_Pay backend

Django + DRF + Celery backend for the GueMi_Pay frontend: data bundles,
airtime, Canal+, ENEO and CAMWATER, paid by mobile money or card, with no
wallet/top-up — every purchase is a single checkout.

## Why it's built this way

- **Django, not FastAPI** — the built-in admin is the ops dashboard (retry
  a failed order, edit prices, watch the call log) from day one.
- **Celery does the slow, unreliable part.** Talking to a mobile money
  collector and a service aggregator are both slow, external, and
  sometimes fail. The request that creates an order returns immediately;
  Celery tasks (`apps/payments/tasks.py`) drive the order through its
  states and retry on failure instead of blocking the HTTP request.
- **Price is never trusted from the client.** `OrderCreateSerializer`
  recomputes the amount from the catalog tables every time.
- **Two collectors, one interface.** `services/collectors.py` (money IN)
  and `services/aggregator.py` (service OUT) each have a `Mock*` class so
  the whole flow works with zero real credentials, and a `Smobilpay*`
  sketch to adapt once you have a merchant agreement (Smobilpay/Maviance
  and PayUnit are the two well-known Cameroon aggregators for this).
- **Every external call is logged** (`AggregatorCallLog`) — this is what
  support actually uses when a customer says "I paid but got nothing."

## Order lifecycle

```
created → payment_pending → paid → fulfilling → completed
                ↓                        ↓
          payment_failed          fulfillment_failed → refunding → refunded
```

## File structure

```
guemi_pay/
├── manage.py
├── requirements.txt
├── .env.example
├── config/                    # project-level config only
│   ├── settings.py
│   ├── urls.py                # /api/auth, /api/accounts, /api/catalog, /api/payments
│   ├── celery.py
│   ├── wsgi.py / asgi.py
├── apps/
│   ├── accounts/              # phone-based user, saved recipients
│   │   ├── models.py  serializers.py  views.py  urls.py  admin.py
│   ├── catalog/                # data bundles, airtime rules, Canal+ plans, utility config
│   │   ├── choices.py         # ServiceType, Operator, BundlePeriod, AccountType
│   │   ├── models.py  serializers.py  views.py  urls.py  admin.py
│   │   └── management/commands/seed_catalog.py
│   └── payments/               # the checkout + fulfillment core
│       ├── choices.py         # PaymentMethod, OrderStatus
│       ├── models.py          # Order, AggregatorCallLog
│       ├── validators.py      # Cameroon operator/number detection
│       ├── serializers.py     # server-side pricing + validation
│       ├── views.py           # OrderCreateView, OrderDetailView, webhook
│       ├── tasks.py           # Celery: collection → fulfillment → refund
│       └── services/
│           ├── collectors.py  # money IN (MoMo / Orange Money / EU / card)
│           └── aggregator.py  # service OUT (ENEO / CAMWATER / Canal+ / telco)
```

## Running it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # AGGREGATOR_MODE=mock needs no real credentials

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_catalog

# three processes:
python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info    # only needed once you wire reconcile_stuck_orders on a schedule
```

## API surface

| Endpoint | Method | Notes |
|---|---|---|
| `/api/auth/login/` | POST | phone/password → JWT pair |
| `/api/catalog/data-bundles/?operator=MTN&period=D` | GET | public |
| `/api/catalog/canal-plans/` | GET | public |
| `/api/catalog/utility-services/eneo/` | GET | reference-number rules for the form |
| `/api/payments/orders/` | POST | creates + prices an order, kicks off Celery |
| `/api/payments/orders/<uuid>/` | GET | poll for status |
| `/api/payments/orders/history/` | GET | past orders |
| `/api/payments/webhooks/collector/` | POST | mobile-money callback |

## Before going to production

1. Sign a merchant agreement with an aggregator (Smobilpay/Maviance or
   PayUnit) and fill in real `AGGREGATOR_*` env vars; swap `AGGREGATOR_MODE`
   from `mock` to whatever you name the real branch in `get_collector()`/
   `get_aggregator()`.
2. Verify the webhook signature in `PaymentWebhookView` before trusting it.
3. Put `reconcile_stuck_orders` on Celery beat (every few minutes).
4. Move `SECRET_KEY`/DB credentials out of `.env` into your real secrets
   manager, and put Django behind HTTPS only.
