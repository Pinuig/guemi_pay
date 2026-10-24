"""
Cameroon mobile number validation and operator detection, shared by order
creation (recipient/payer checks) so the backend enforces the same rules
the frontend already nudges the user toward — the backend is the one that
actually has to be right, since it decides what gets charged.
"""
import re

_PREFIXES = {
    "MTN": re.compile(r"^6(7|8|5[0-4])"),
    "Orange": re.compile(r"^6(9|5[5-9])"),
    "Nexttel": re.compile(r"^66"),
    "Camtel": re.compile(r"^62"),
}

# Which payment methods accept which detected operator. "any" = no restriction.
PAYMENT_METHOD_OPERATOR = {
    "momo": "MTN",
    "om": "Orange",
    "eu": "any",
    "card": None,  # no phone number involved
}


def normalize_cm_number(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("237"):
        digits = digits[3:]
    return digits


def detect_operator(raw: str) -> str | None:
    digits = normalize_cm_number(raw)
    if len(digits) != 9 or not digits.startswith("6"):
        return None
    for operator, pattern in _PREFIXES.items():
        if pattern.match(digits):
            return operator
    return None
