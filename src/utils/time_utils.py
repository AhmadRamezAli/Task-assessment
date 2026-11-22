"""Convert log timestamps and serialize UTC values consistently."""

from datetime import datetime, timezone


def parse_timestamp(value: str) -> datetime:
    """Parse a dataset timestamp into an aware UTC datetime.

    Example: "2026-11-03T17:00:00+03:00" -> datetime(2026, 11, 3, 14, tzinfo=UTC).
    A missing timezone raises ValueError so host-local time is never assumed.
    """
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Log timestamps must include Z or a UTC offset.")
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    """Serialize an aware datetime as an ISO 8601 UTC string.

    Example: datetime(2026, 11, 3, 17, tzinfo=UTC+03:00) -> "2026-11-03T14:00:00Z".
    """
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
