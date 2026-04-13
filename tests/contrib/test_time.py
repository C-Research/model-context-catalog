from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from mcc.app import execute

_CTX = MagicMock()


@pytest.fixture(autouse=True)
async def _load(load_contrib):
    load_contrib("time.yaml")


class TestNow:
    async def test_returns_iso_string(self):
        result = await execute(_CTX, "public.time.now", {})
        dt = datetime.fromisoformat(result)
        assert dt.tzinfo is not None

    async def test_respects_timezone(self):
        result = await execute(_CTX, "public.time.now", {"tz": "US/Eastern"})
        dt = datetime.fromisoformat(result)
        expected_offset = datetime.now(ZoneInfo("US/Eastern")).utcoffset()
        assert dt.utcoffset() == expected_offset

    async def test_defaults_to_utc(self):
        result = await execute(_CTX, "public.time.now", {})
        dt = datetime.fromisoformat(result)
        assert dt.utcoffset().total_seconds() == 0


class TestFormat:
    async def test_format_date(self):
        result = await execute(_CTX,
            "public.time.format",
            {
                "dt": "2025-06-15T10:30:00",
                "fmt": "%Y-%m-%d",
            },
        )
        assert result == "2025-06-15"

    async def test_format_time(self):
        result = await execute(_CTX,
            "public.time.format",
            {
                "dt": "2025-06-15T10:30:00",
                "fmt": "%H:%M",
            },
        )
        assert result == "10:30"

    async def test_format_custom(self):
        result = await execute(_CTX,
            "public.time.format",
            {
                "dt": "2025-06-15T10:30:00",
                "fmt": "%B %d, %Y",
            },
        )
        assert result == "June 15, 2025"


class TestDelta:
    async def test_add_days(self):
        result = await execute(_CTX,
            "public.time.delta",
            {
                "dt": "2025-06-15T10:00:00",
                "days": 3,
            },
        )
        assert result == "2025-06-18T10:00:00"

    async def test_subtract_hours(self):
        result = await execute(_CTX,
            "public.time.delta",
            {
                "dt": "2025-06-15T10:00:00",
                "hours": -2,
            },
        )
        assert result == "2025-06-15T08:00:00"

    async def test_combined_delta(self):
        result = await execute(_CTX,
            "public.time.delta",
            {
                "dt": "2025-06-15T10:00:00",
                "days": 1,
                "hours": 2,
                "minutes": 30,
            },
        )
        assert result == "2025-06-16T12:30:00"

    async def test_preserves_timezone(self):
        result = await execute(_CTX,
            "public.time.delta",
            {
                "dt": "2025-06-15T10:00:00+05:30",
                "hours": 1,
            },
        )
        dt = datetime.fromisoformat(result)
        assert dt.hour == 11
        assert str(dt.utcoffset()) == "5:30:00"
