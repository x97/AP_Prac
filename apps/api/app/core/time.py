from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_expired(value: datetime | None) -> bool:
    return value is not None and as_utc(value) <= utcnow()


def shanghai_date(value: datetime) -> date:
    """Calendar date in the product's China-first timezone."""
    return as_utc(value).astimezone(SHANGHAI).date()
