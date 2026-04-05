from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def now(tz: str = "UTC") -> str:
    """Return the current date and time as an ISO 8601 string in the given timezone."""
    return datetime.now(ZoneInfo(tz)).isoformat()


def format(dt: str, fmt: str) -> str:
    """Format an ISO 8601 datetime string using a strftime format string."""
    return datetime.fromisoformat(dt).strftime(fmt)


def delta(
    dt: str,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """Add a time delta to an ISO 8601 datetime string and return the result."""
    parsed = datetime.fromisoformat(dt)
    result = parsed + timedelta(
        days=days, hours=hours, minutes=minutes, seconds=seconds
    )
    return result.isoformat()
