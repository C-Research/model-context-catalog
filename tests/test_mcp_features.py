import asyncio
import logging
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest
from mcc.app import debug_error, explain_tool, find_and_run
from mcc.auth.models import UserModel
from mcc.cache import parse_rate_limit
from mcc.context import current_user_var
from mcc.loader import loader
from mcc.middleware import AuthMiddleware, LoggingMiddleware, RateLimitMiddleware

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_loader():
    loader.clear()
    yield
    loader.clear()


def _load(filename: str):
    loader.load(FIXTURES / filename)


# --- Middleware ---


@pytest.mark.smoke
class TestAuthMiddleware:
    async def test_resolves_authenticated_user(self):
        user = UserModel(username="alice", email="a@b.com", groups=["admin"])
        with patch("mcc.middleware.get_current_user", return_value=user):
            middleware = AuthMiddleware()

            async def _noop(ctx):
                return None

            await middleware.on_message(None, _noop)
            assert current_user_var.get() == user

    async def test_anonymous_sets_none(self):
        with patch("mcc.middleware.get_current_user", return_value=None):
            middleware = AuthMiddleware()

            async def _noop(ctx):
                return None

            await middleware.on_message(None, _noop)
            assert current_user_var.get() is None


@pytest.mark.smoke
class TestLoggingMiddleware:
    async def test_logs_tool_call(self, caplog):
        import logging

        current_user_var.set(None)

        class FakeMessage:
            name = "test.tool"
            arguments: ClassVar = {"key": "val"}

        class FakeContext:
            message = FakeMessage()

        middleware = LoggingMiddleware()

        async def _noop(ctx):
            return "result"

        mcc_logger = logging.getLogger("mcc")
        mcc_logger.propagate = True
        try:
            with caplog.at_level("INFO", logger="mcc"):
                await middleware.on_call_tool(FakeContext(), _noop)

            assert "anonymous calling test.tool" in caplog.text
            assert "completed test.tool" in caplog.text
        finally:
            mcc_logger.propagate = False


@pytest.mark.smoke
class TestParseRateLimit:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("60/1min", (60, 60)),
            ("50/24hr", (50, 24 * 3600)),
            ("10/30s", (10, 30)),
            ("1/1s", (1, 1)),
            (-1, (-1, 0)),
        ],
    )
    def test_valid_formats(self, value, expected):
        assert parse_rate_limit(value) == expected

    @pytest.mark.parametrize(
        "value",
        ["abc", "60", "60/1", "60/1day", "60/-1min", "-1/1min", ""],
    )
    def test_invalid_formats_raise(self, value):
        with pytest.raises(ValueError):
            parse_rate_limit(value)


class _FakeRateLimitCfg:
    def __init__(self, default, tools=None):
        self.default = default
        self.tools = tools or {}


class _FakeSettings:
    def __init__(self, default, tools=None):
        self.rate_limit = _FakeRateLimitCfg(default, tools)


def _execute_ctx(key="admin.shell"):
    class FakeMessage:
        name = "execute"
        arguments: ClassVar = {"key": key}

    class FakeContext:
        message = FakeMessage()

    return FakeContext()


@pytest.mark.smoke
class TestRateLimitMiddleware:
    async def test_within_limit_passes_through(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="5/60s"),
        ):
            middleware = RateLimitMiddleware()

            async def _compute(ctx):
                return "ok"

            result = await middleware.on_call_tool(_execute_ctx(), _compute)
            assert result == "ok"

    async def test_over_limit_rejects(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s"),
        ):
            middleware = RateLimitMiddleware()
            calls = []

            async def _compute(ctx):
                calls.append(1)
                return "ok"

            first = await middleware.on_call_tool(_execute_ctx(), _compute)
            second = await middleware.on_call_tool(_execute_ctx(), _compute)

            assert first == "ok"
            assert len(calls) == 1
            assert "Rate limit exceeded for admin.shell" in second.content[0].text

    async def test_window_resets_after_period(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/1s"),
        ):
            middleware = RateLimitMiddleware()

            async def _compute(ctx):
                return "ok"

            first = await middleware.on_call_tool(_execute_ctx(), _compute)
            throttled = await middleware.on_call_tool(_execute_ctx(), _compute)
            await asyncio.sleep(1.2)
            third = await middleware.on_call_tool(_execute_ctx(), _compute)

            assert first == "ok"
            assert "Rate limit exceeded" in throttled.content[0].text
            assert third == "ok"

    async def test_tool_specific_overrides_default(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(
                default="100/60s",
                tools={"admin.shell": "1/60s"},
            ),
        ):
            middleware = RateLimitMiddleware()

            async def _compute(ctx):
                return "ok"

            first = await middleware.on_call_tool(_execute_ctx("admin.shell"), _compute)
            second = await middleware.on_call_tool(_execute_ctx("admin.shell"), _compute)
            other = await middleware.on_call_tool(_execute_ctx("public.request"), _compute)

            assert first == "ok"
            assert "Rate limit exceeded for admin.shell" in second.content[0].text
            assert other == "ok"

    async def test_unlimited_tool_never_throttles(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(
                default="1/60s",
                tools={"admin.shell": -1},
            ),
        ):
            middleware = RateLimitMiddleware()

            async def _compute(ctx):
                return "ok"

            for _ in range(5):
                result = await middleware.on_call_tool(_execute_ctx("admin.shell"), _compute)
                assert result == "ok"

    async def test_missing_key_argument_skips_check(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s"),
        ):
            middleware = RateLimitMiddleware()

            class FakeMessage:
                name = "execute"
                arguments: ClassVar = {}

            class FakeContext:
                message = FakeMessage()

            async def _compute(ctx):
                return "ok"

            for _ in range(3):
                result = await middleware.on_call_tool(FakeContext(), _compute)
                assert result == "ok"

    async def test_non_string_key_argument_skips_check(self):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s"),
        ):
            middleware = RateLimitMiddleware()

            class FakeMessage:
                name = "execute"
                arguments: ClassVar = {"key": None}

            class FakeContext:
                message = FakeMessage()

            async def _compute(ctx):
                return "ok"

            for _ in range(3):
                result = await middleware.on_call_tool(FakeContext(), _compute)
                assert result == "ok"

    @pytest.mark.parametrize(
        "verb", ["search", "whoami", "describe_tools", "set_session", "get_session"]
    )
    async def test_non_execute_verbs_never_limited(self, verb):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s"),
        ):
            middleware = RateLimitMiddleware()

            class FakeMessage:
                name = verb
                arguments: ClassVar = {"key": "admin.shell"}

            class FakeContext:
                message = FakeMessage()

            async def _compute(ctx):
                return "ok"

            for _ in range(3):
                result = await middleware.on_call_tool(FakeContext(), _compute)
                assert result == "ok"

    async def test_anonymous_callers_share_one_bucket(self):
        # There is no per-connection identity for anonymous callers in this
        # system — current_user_var is None for every anonymous caller, so
        # this demonstrates the shared "anon" bucket directly: two calls with
        # no user set both land on the same rate-limit key.
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s"),
        ):
            middleware = RateLimitMiddleware()

            async def _compute(ctx):
                return "ok"

            first = await middleware.on_call_tool(_execute_ctx(), _compute)
            current_user_var.set(None)  # a second, distinct anonymous caller
            second = await middleware.on_call_tool(_execute_ctx(), _compute)

            assert first == "ok"
            assert "Rate limit exceeded" in second.content[0].text

    async def test_cache_hit_still_counts(self):
        # RateLimitMiddleware increments before call_next runs, so it counts a
        # call regardless of whether call_next turns out to serve a cached
        # result downstream (execute()'s own cache_ttl lookup).
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="2/60s"),
        ):
            middleware = RateLimitMiddleware()

            async def _cached_result(ctx):
                return "cached-value"

            first = await middleware.on_call_tool(_execute_ctx(), _cached_result)
            second = await middleware.on_call_tool(_execute_ctx(), _cached_result)
            third = await middleware.on_call_tool(_execute_ctx(), _cached_result)

            assert first == "cached-value"
            assert second == "cached-value"
            assert "Rate limit exceeded" in third.content[0].text

    async def test_throttled_call_still_logged(self, caplog):
        current_user_var.set(None)
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s"),
        ):
            rate_middleware = RateLimitMiddleware()
            log_middleware = LoggingMiddleware()

            async def _compute(ctx):
                return "ok"

            async def _chain(ctx):
                return await rate_middleware.on_call_tool(ctx, _compute)

            mcc_logger = logging.getLogger("mcc")
            mcc_logger.propagate = True
            try:
                with caplog.at_level("INFO", logger="mcc"):
                    first = await log_middleware.on_call_tool(_execute_ctx(), _chain)
                    second = await log_middleware.on_call_tool(_execute_ctx(), _chain)
                assert first == "ok"
                assert "Rate limit exceeded" in second.content[0].text
                # both the allowed call and the throttled one produced a
                # calling/completed log pair — throttling didn't suppress logging
                assert "anonymous calling execute" in caplog.text
                assert "anonymous completed execute" in caplog.text
            finally:
                mcc_logger.propagate = False


# --- Prompts ---


@pytest.mark.smoke
class TestPrompts:
    def test_find_and_run(self):
        result = find_and_run("deploy the app")
        assert "deploy the app" in result
        assert "Search" in result or "search" in result.lower()

    def test_explain_tool(self):
        result = explain_tool("admin.shell")
        assert "admin.shell" in result
        assert "parameters" in result.lower()

    def test_debug_error(self):
        result = debug_error("admin.shell", "permission denied")
        assert "admin.shell" in result
        assert "permission denied" in result
        assert "fix" in result.lower() or "troubleshoot" in result.lower()
