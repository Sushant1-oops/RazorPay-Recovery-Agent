"""Small datetime helpers used across the backend."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware 'now', in UTC."""
    return datetime.now(timezone.utc)


def seconds_since(dt: datetime | None) -> float | None:
    """Seconds elapsed since a timezone-aware datetime, or None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (utcnow() - dt).total_seconds()
