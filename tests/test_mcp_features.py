import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from mcc.app import debug_error, explain_tool, find_and_run
from mcc.cache import parse_rate_limit
from mcc.context import ANONYMOUS_USER, UserModel, current_user_var
from mcc.loader import loader
from mcc.middleware import AuthMiddleware, check_rate_limit
from mcc.models import ToolCallEvent, on_tool_call

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

    async def test_anonymous_sets_anonymous_user(self):
        with patch("mcc.middleware.get_current_user", return_value=None):
            middleware = AuthMiddleware()

            async def _noop(ctx):
                return None

            await middleware.on_message(None, _noop)
            assert current_user_var.get().is_anonymous


@pytest.mark.smoke
class TestToolCallHooks:
    """ToolModel.call()'s on_tool_call hook mechanism (mcc/models.py) — the
    single choke point every catalog tool call passes through regardless of
    transport, fired once per invocation whether it succeeds or fails.
    LoggingMiddleware/MetricsMiddleware no longer exist as separate FastMCP
    middleware classes; both are now hooks registered against this same
    mechanism (mcc/middleware.py), exercised here at the source instead."""

    @pytest.fixture
    def probe(self):
        from mcc.models import _call_hooks

        events: list[ToolCallEvent] = []

        async def _capture(event: ToolCallEvent) -> None:
            events.append(event)

        on_tool_call(_capture)
        yield events
        _call_hooks.remove(_capture)

    async def test_fires_on_success(self, probe):
        current_user_var.set(ANONYMOUS_USER)
        _load("tools_ungrouped.yaml")
        tool = loader["echo"]

        result = await tool.call(message="hi")

        # tool.call() returns the fn subprocess's raw JSON string —
        # execute()'s _coerce_result() is what decodes it, one layer up.
        assert result == '["hi"]'
        assert len(probe) == 1
        event = probe[0]
        assert event.tool_key == "echo"
        assert event.status == "success"
        assert event.error is None
        assert event.params == {"message": "hi"}
        assert event.duration >= 0

    async def test_fires_on_runtime_error(self, probe):
        current_user_var.set(ANONYMOUS_USER)
        _load("tools_ungrouped.yaml")
        tool = loader["echo"]

        def _raise(**kwargs):
            raise RuntimeError("boom")

        tool.__dict__["callable"] = _raise  # overrides the cached_property

        with pytest.raises(RuntimeError):
            await tool.call(message="hi")

        assert len(probe) == 1
        event = probe[0]
        assert event.status == "error"
        assert event.error == "RuntimeError: boom"

    async def test_fires_on_validation_error(self, probe):
        current_user_var.set(ANONYMOUS_USER)
        _load("tools_ungrouped.yaml")
        tool = loader["echo"]

        with pytest.raises(Exception):
            await tool.call()  # missing required "message"

        assert len(probe) == 1
        event = probe[0]
        assert event.status == "error"
        # Params are unknown at this point — validation failed before any
        # were resolved — so the event carries an empty dict, not a guess.
        assert event.params == {}

    async def test_carries_resolved_user_and_key_prefix(self, probe):
        user = UserModel(username="alice", key={"prefix": "abc123"})
        current_user_var.set(user)
        try:
            _load("tools_ungrouped.yaml")
            tool = loader["echo"]
            await tool.call(message="hi")
        finally:
            current_user_var.set(ANONYMOUS_USER)

        event = probe[0]
        assert event.user is user
        assert event.key_prefix == "abc123"

    async def test_no_key_prefix_without_a_key(self, probe):
        current_user_var.set(UserModel(username="alice"))
        try:
            _load("tools_ungrouped.yaml")
            tool = loader["echo"]
            await tool.call(message="hi")
        finally:
            current_user_var.set(ANONYMOUS_USER)

        assert probe[0].key_prefix is None

    async def test_hidden_and_override_params_never_included(self, probe):
        current_user_var.set(ANONYMOUS_USER)
        _load("tools_override.yaml")
        tool = loader["echo_with_flag"]

        await tool.call(message="hi")

        event = probe[0]
        assert event.params == {"message": "hi"}
        assert "flag" not in event.params


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


@pytest.mark.smoke
class TestCheckRateLimit:
    """check_rate_limit() (mcc/middleware.py) — called explicitly by
    execute() (before its cache lookup) and tool_execute() (before
    invocation), never from a standalone middleware class. RateLimitMiddleware
    no longer exists; unlike logging/metrics, rate limiting can't move onto
    ToolModel.call()'s hook, since a cache hit must still count against the
    limit and never reaches call() (see design.md). Cache-hit-still-counts
    and throttled-call-is-logged are exercised at the execute() integration
    level in test_app.py, since both depend on where this check sits
    relative to execute()'s cache lookup, not on this function alone."""

    async def test_within_limit_passes_through(self):
        with patch("mcc.middleware.settings", _FakeSettings(default="5/60s")):
            exceeded, _remaining = await check_rate_limit("admin.shell", "anon")
            assert exceeded is False

    async def test_over_limit_rejects(self):
        with patch("mcc.middleware.settings", _FakeSettings(default="1/60s")):
            first, _ = await check_rate_limit("admin.shell", "anon")
            second, _ = await check_rate_limit("admin.shell", "anon")
            assert first is False
            assert second is True

    async def test_window_resets_after_period(self):
        with patch("mcc.middleware.settings", _FakeSettings(default="1/1s")):
            first, _ = await check_rate_limit("admin.shell", "anon")
            throttled, _ = await check_rate_limit("admin.shell", "anon")
            await asyncio.sleep(1.2)
            third, _ = await check_rate_limit("admin.shell", "anon")
            assert first is False
            assert throttled is True
            assert third is False

    async def test_tool_specific_overrides_default(self):
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="100/60s", tools={"admin.shell": "1/60s"}),
        ):
            first, _ = await check_rate_limit("admin.shell", "anon")
            second, _ = await check_rate_limit("admin.shell", "anon")
            other, _ = await check_rate_limit("public.request", "anon")
            assert first is False
            assert second is True
            assert other is False

    async def test_unlimited_tool_never_throttles(self):
        with patch(
            "mcc.middleware.settings",
            _FakeSettings(default="1/60s", tools={"admin.shell": -1}),
        ):
            for _ in range(5):
                exceeded, _ = await check_rate_limit("admin.shell", "anon")
                assert exceeded is False

    async def test_anonymous_callers_share_one_bucket(self):
        # No per-connection identity for anonymous callers — both calls pass
        # the same literal username, landing on the same bucket (execute()/
        # tool_execute() derive "anonymous" for real anonymous callers; the
        # exact string doesn't matter to check_rate_limit itself).
        with patch("mcc.middleware.settings", _FakeSettings(default="1/60s")):
            first, _ = await check_rate_limit("admin.shell", "anon")
            second, _ = await check_rate_limit("admin.shell", "anon")
            assert first is False
            assert second is True


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
