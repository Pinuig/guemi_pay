from django.db import models


class ServiceType(models.TextChoices):
    DATA = "data", "Data bundle"
    AIRTIME = "airtime", "Airtime top-up"
    CANAL = "canal", "Canal+ subscription"
    ENEO = "eneo", "ENEO electricity"
    WATER = "water", "CAMWATER water bill"


class Operator(models.TextChoices):
    MTN = "MTN", "MTN Cameroon"
    ORANGE = "Orange", "Orange Cameroon"
    NEXTTEL = "Nexttel", "Nexttel"
    CAMTEL = "Camtel", "Camtel"


class BundlePeriod(models.TextChoices):
    DAILY = "D", "Daily"
    WEEKLY = "W", "Weekly"
    MONTHLY = "M", "Monthly"


class AccountType(models.TextChoices):
    PREPAID = "prepaid", "Prepaid"
    POSTPAID = "postpaid", "Postpaid"
