"""Lightweight payload validators for inbound webhook/simulation data."""


def is_valid_amount(amount) -> bool:
    """Amount must be a positive integer, in the smallest currency unit (paise)."""
    return isinstance(amount, int) and amount > 0


def is_valid_currency(currency: str | None) -> bool:
    return bool(currency) and len(currency) == 3 and currency.isalpha()


def is_valid_payment_method(method: str | None) -> bool:
    return method in {"card", "upi", "netbanking", "wallet", None}
