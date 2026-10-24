from django.core.management.base import BaseCommand

from apps.catalog.choices import AccountType, ServiceType
from apps.catalog.models import AirtimeRule, CanalPlan, DataBundle, UtilityServiceConfig

BUNDLES = {
    "MTN": [
        ("D", "100 MB", "24 h", 200), ("D", "350 MB", "24 h", 500), ("D", "1 GB", "24 h", 1000),
        ("W", "1.5 GB", "7 days", 1500), ("W", "4 GB", "7 days", 3000),
        ("M", "8 GB", "30 days", 5000), ("M", "20 GB", "30 days", 10000), ("M", "60 GB", "30 days", 25000),
    ],
    "Orange": [
        ("D", "150 MB", "24 h", 200), ("D", "500 MB", "24 h", 500), ("D", "1.2 GB", "24 h", 1000),
        ("W", "3 GB", "7 days", 2000), ("W", "6 GB", "7 days", 3500),
        ("M", "9 GB", "30 days", 5000), ("M", "22 GB", "30 days", 10000), ("M", "50 GB", "30 days", 20000),
    ],
    "Nexttel": [
        ("D", "200 MB", "24 h", 200), ("D", "700 MB", "24 h", 500),
        ("W", "2 GB", "7 days", 1500), ("W", "5 GB", "7 days", 3000),
        ("M", "10 GB", "30 days", 5000), ("M", "25 GB", "30 days", 10000),
    ],
    "Camtel": [
        ("D", "500 MB", "24 h", 500), ("W", "3 GB", "7 days", 2000),
        ("M", "8 GB", "30 days", 5000), ("M", "20 GB", "30 days", 10000), ("M", "40 GB", "30 days", 15000),
    ],
}

CANAL_PLANS = [("Access", 5000, 0), ("Evasion", 10000, 1), ("Essentiel+", 15000, 2), ("Tout Canal+", 30000, 3)]


class Command(BaseCommand):
    help = "Seed sample data-bundle, airtime, Canal+ and utility catalog rows for development."

    def handle(self, *args, **options):
        for operator, rows in BUNDLES.items():
            for period, data_label, validity_label, price in rows:
                DataBundle.objects.update_or_create(
                    operator=operator, period=period, data_label=data_label, validity_label=validity_label,
                    defaults={"price": price},
                )
            AirtimeRule.objects.update_or_create(
                operator=operator, defaults={"min_amount": 100, "max_amount": 50000},
            )

        for name, price, sort_order in CANAL_PLANS:
            CanalPlan.objects.update_or_create(name=name, defaults={"monthly_price": price, "sort_order": sort_order})

        UtilityServiceConfig.objects.update_or_create(
            service_type=ServiceType.CANAL,
            defaults={"reference_label": "Decoder/smartcard number", "reference_min_length": 10,
                      "reference_max_length": 14, "min_amount": 5000},
        )
        UtilityServiceConfig.objects.update_or_create(
            service_type=ServiceType.ENEO,
            defaults={"account_type": AccountType.PREPAID, "reference_label": "Meter number",
                      "reference_min_length": 8, "reference_max_length": 14, "min_amount": 1000},
        )
        UtilityServiceConfig.objects.update_or_create(
            service_type=ServiceType.WATER,
            defaults={"reference_label": "Customer contract number", "reference_min_length": 6,
                      "reference_max_length": 14, "min_amount": 500},
        )

        self.stdout.write(self.style.SUCCESS("Catalog seeded."))
