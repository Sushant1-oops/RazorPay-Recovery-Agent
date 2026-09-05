"""Idempotency key helpers.

Webhook idempotency itself is enforced at the DB level via the unique
constraint on PaymentEvent.event_id (see EventRepository.exists /
app/models/payment_event.py). This helper is for deriving a stable key
when a caller (e.g. the simulation routes) needs to synthesize one.
"""
import hashlib


def derive_key(*parts: str) -> str:
    """Deterministic idempotency key from an ordered set of string parts."""
    joined = "|".join(p or "" for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]
