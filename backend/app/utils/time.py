from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def shanghai_now() -> datetime:
    try:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=8), name="UTC+08"))


def session_expires_at() -> datetime:
    return utc_now() + timedelta(hours=settings.auth_session_ttl_hours)
