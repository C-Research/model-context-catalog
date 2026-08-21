import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from mcc.app import describe_tools, execute, search, whoami
from mcc.auth.models import UserModel
from mcc.cache import cache, params_hash
from mcc.loader import loader
from mcc.context import current_user_var
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)


def _with_state(ctx, session="s1"):
    """Back a mock ctx with an in-memory, session-scoped state store mirroring
    FastMCP's key prefixing (`{session_id}:{key}`), so execute() and the session
    tools behave as they would against a real store."""
    store: dict = {}

    async def _get(key):
        return store.get(f"{session}:{key}")

    async def _set(key, value):
        store[f"{session}:{key}"] = value

    ctx.get_state = AsyncMock(side_effect=_get)
    ctx.set_state = AsyncMock(side_effect=_set)
    return ctx


def _ctx_raises():
    """Mock ctx whose elicit() raises — simulates a client that doesn't support elicitation."""
    ctx = MagicMock()
    ctx.elicit = AsyncMock(side_effect=Exception("elicitation not supported"))
    return _with_state(ctx)


def _ctx_accepts(**data):
    """Mock ctx whose elicit() returns an AcceptedElicitation with the given data fields."""

    class _Data(BaseModel):
        model_config = {"extra": "allow"}

    instance = _Data(**data)
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=AcceptedElicitation(data=instance))
    return _with_state(ctx)


def _ctx_declines():
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=DeclinedElicitation())
    return _with_state(ctx)


def _ctx_cancels():
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=CancelledElicitation())
    return _with_state(ctx)


def _ctx_state(session="s1"):
    """A plain state-backed ctx for testing get_session / set_session."""
    return _with_state(MagicMock(), session)


class TestSearch:
    async def test_matches_by_name(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        result = await search("echo")
        assert "echo" in result
        assert "Echoes back" in result

    async def test_no_match(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        result = await search("zzz_nonexistent", min_score=999.0)
        assert result.startswith("No tools matched your query.")

    async def test_grouped_tool_inaccessible_anonymous(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        await loader.save()
        result = await search("echo")
        assert result.startswith("No tools matched your query.")


class TestExecute:
    async def test_execute_public_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "echo", {"message": "hi"})
        assert result == ["hi"]

    @pytest.mark.smoke
    async def test_execute_grouped_tool_unauthorized(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        result = await execute(_ctx_raises(), "example.echo", {"message": "hi"})
        assert result.startswith("Unauthorized")

    @pytest.mark.smoke
    async def test_execute_unknown_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "nonexistent", {})
        assert "Unknown tool" in result

    @pytest.mark.smoke
    async def test_execute_validation_error(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "echo", {})
        assert "Validation error" in result

    async def test_elicit_accepted_executes_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_accepts(message="elicited"), "echo", {})
        assert result == ["elicited"]

    async def test_elicit_declined_returns_cancelled(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_declines(), "echo", {})
        assert result == "Execution cancelled: required parameters not provided"

    async def test_elicit_cancelled_returns_cancelled(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_cancels(), "echo", {})
        assert result == "Execution cancelled: required parameters not provided"

    async def test_elicit_unsupported_client_falls_through(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "echo", {})
        assert "Validation error" in result

    async def test_elicit_not_triggered_when_params_provided(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        ctx = _ctx_accepts(message="should not be called")
        result = await execute(ctx, "echo", {"message": "direct"})
        ctx.elicit.assert_not_awaited()
        assert result == ["direct"]

    async def test_elicit_skipped_for_list_param(self, load_fixture):
        load_fixture("tools_list_param.yaml")
        ctx = _ctx_accepts()
        result = await execute(ctx, "join", {})
        ctx.elicit.assert_not_awaited()
        assert "Validation error" in result


class TestDescribeTools:
    async def test_lists_accessible_tools(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await describe_tools()
        assert "## echo" in result
        assert "Echoes back" in result

    async def test_format(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await describe_tools()
        assert result.startswith("## echo\n")

    async def test_grouped_tools_inaccessible_anonymous(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        result = await describe_tools()
        assert result == "No tools available."

    async def test_groups_and_filter(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="test", groups=["a", "b"]))
        try:
            result = await describe_tools(["a", "b"])
            assert "a.b.multi_ab" in result
            assert "a.single_a" not in result
            assert "b.single_b" not in result
        finally:
            current_user_var.set(None)

    async def test_groups_filter_no_match(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="test", groups=["a", "b"]))
        try:
            result = await describe_tools(["a", "b", "nonexistent"])
            assert result == "No tools available."
        finally:
            current_user_var.set(None)

    async def test_empty_description(self, load_fixture):
        load_fixture("tools_no_description.yaml")
        result = await describe_tools()
        assert "## doc_tool" in result


class TestWhoami:
    @pytest.mark.smoke
    async def test_anonymous(self):
        current_user_var.set(None)
        result = await whoami()
        assert result.startswith("Not authenticated")

    async def test_tools_resolved_from_groups(self, load_fixture):
        # multigroup catalog: a.b.multi_ab (groups a,b), a.single_a (a), b.single_b (b)
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="alice", groups=["a"]))
        try:
            result = await whoami()
            assert "username: alice" in result
            assert "groups: a" in result
            # exhaustive: every tool reachable via group a, none from b-only
            assert "a.b.multi_ab" in result
            assert "a.single_a" in result
            assert "b.single_b" not in result
        finally:
            current_user_var.set(None)

    async def test_tools_union_of_groups_and_direct_grants(self, load_fixture):
        # In group b (→ a.b.multi_ab, b.single_b) plus a direct grant to a.single_a.
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(
            UserModel(username="bob", groups=["b"], tools=["a.single_a"])
        )
        try:
            result = await whoami()
            assert "a.b.multi_ab" in result  # via group b
            assert "b.single_b" in result  # via group b
            assert "a.single_a" in result  # via direct grant
        finally:
            current_user_var.set(None)

    async def test_admin_sees_all_tools(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="root", groups=["admin"]))
        try:
            result = await whoami()
            assert "a.b.multi_ab" in result
            assert "a.single_a" in result
            assert "b.single_b" in result
        finally:
            current_user_var.set(None)

    async def test_no_accessible_tools_shows_none(self, load_fixture):
        # User in an unrelated group with no public tools loaded → tools: (none).
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="nobody", groups=["unrelated"]))
        try:
            result = await whoami()
            assert "username: nobody" in result
            assert "tools: (none)" in result
        finally:
            current_user_var.set(None)

    async def test_no_email_or_groups_shows_none(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="loner"))
        try:
            result = await whoami()
            assert "email: (none)" in result
            assert "groups: (none)" in result
            assert "tools: (none)" in result
        finally:
            current_user_var.set(None)


class TestWhoamiCache:
    async def test_second_call_uses_cache(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="alice", groups=["a"]))
        try:
            result1 = await whoami()
            assert "a.single_a" in result1
            # Overwrite the cache entry — a cache hit returns the sentinel verbatim.
            await cache.set("whoami:alice", "SENTINEL", expire=60)
            result2 = await whoami()
            assert result2 == "SENTINEL"
        finally:
            current_user_var.set(None)

    async def test_reload_invalidates_cache(self, load_fixture):
        from pathlib import Path

        fixture_path = str(Path(__file__).parent / "fixtures" / "tools_multigroup.yaml")
        load_fixture("tools_multigroup.yaml")
        loader.paths = {fixture_path}
        await loader.save()
        current_user_var.set(UserModel(username="alice", groups=["a"]))
        try:
            # Prime the cache with a sentinel; served from cache while valid.
            await cache.set("whoami:alice", "SENTINEL", expire=60)
            assert await whoami() == "SENTINEL"
            # reload busts whoami:* → real result is recomputed from the catalog.
            await loader.reload()
            result = await whoami()
            assert result != "SENTINEL"
            assert "a.single_a" in result
        finally:
            current_user_var.set(None)

    async def test_user_modification_invalidates_cache(self, users_idx, load_fixture):
        from mcc.auth.db import add_tool, create_user

        load_fixture("tools_multigroup.yaml")
        await create_user("carol", groups=["a"])
        current_user_var.set(UserModel(username="carol", groups=["a"]))
        try:
            # Prime cache with a sentinel; a hit would return it verbatim.
            await cache.set("whoami:carol", "SENTINEL", expire=60)
            assert await whoami() == "SENTINEL"
            # Granting a tool must drop the cached entry → no longer the sentinel.
            await add_tool("carol", "b.single_b")
            result = await whoami()
            assert result != "SENTINEL"
            assert "username: carol" in result
        finally:
            current_user_var.set(None)


# Anonymous context assembled by execute() for every TestExecuteCache test below
# (no current_user_var set, no stored session vars) — must match the same
# {"user": ..., ...} shape assemble_context(None, None) produces.
_ANON_CONTEXT = {"user": "anonymous"}


class TestExecuteCache:
    async def test_cache_hit_skips_tool_call(self, load_fixture):
        # First call populates the cache with the real result.
        # We then overwrite the cache entry with a sentinel.
        # If the second call returns the sentinel, the cache was used.
        load_fixture("tools_cached.yaml")
        ctx = _ctx_raises()
        result1 = await execute(ctx, "echo", {"message": "hi"})
        assert result1 == ["hi"]
        cache_key = (
            f"exec:echo:{params_hash({'message': 'hi'})}:"
            f"{params_hash(_ANON_CONTEXT)}"
        )
        await cache.set(cache_key, "sentinel", expire=60)
        result2 = await execute(ctx, "echo", {"message": "hi"})
        assert result2 == "sentinel"

    async def test_no_cache_ttl_always_calls_tool(self, load_fixture):
        # Tool without cache_ttl: manually set a cache entry and verify it's ignored.
        load_fixture("tools_ungrouped.yaml")
        ctx = _ctx_raises()
        result1 = await execute(ctx, "echo", {"message": "hi"})
        assert result1 == ["hi"]
        cache_key = (
            f"exec:echo:{params_hash({'message': 'hi'})}:"
            f"{params_hash(_ANON_CONTEXT)}"
        )
        await cache.set(cache_key, "sentinel", expire=60)
        result2 = await execute(ctx, "echo", {"message": "hi"})
        assert result2 == ["hi"]  # real result, not sentinel

    async def test_different_params_different_cache_keys(self, load_fixture):
        load_fixture("tools_cached.yaml")
        ctx = _ctx_raises()
        result_a = await execute(ctx, "echo", {"message": "a"})
        result_b = await execute(ctx, "echo", {"message": "b"})
        assert result_a == ["a"]
        assert result_b == ["b"]

    async def test_different_context_different_cache_keys(self, load_fixture):
        """A tool result that depends on context must not leak across sessions.

        Same tool, same params, two different sessions with different stored
        `database` context vars: each must see its own result, not the other's
        cached one — regression test for the params-only cache key bug.
        """
        load_fixture("tools_context_cached.yaml")
        ctx_a = _ctx_state(session="s1")
        ctx_b = _ctx_state(session="s2")
        await execute(ctx_a, "stash_cursor", {"n": 1})
        await execute(ctx_b, "stash_cursor", {"n": 2})

        result_a = await execute(ctx_a, "needs_context", {"x": 1})
        result_b = await execute(ctx_b, "needs_context", {"x": 1})

        assert result_a["context"].get("cursor") == 1
        assert result_b["context"].get("cursor") == 2

    async def test_different_user_different_cache_keys(self, load_fixture):
        """Same params, two different authenticated users: no cross-user leak."""
        load_fixture("tools_context_cached.yaml")
        current_user_var.set(UserModel(username="alice"))
        try:
            result_alice = await execute(_ctx_raises(), "needs_context", {"x": 1})
        finally:
            current_user_var.set(None)
        current_user_var.set(UserModel(username="bob"))
        try:
            result_bob = await execute(_ctx_raises(), "needs_context", {"x": 1})
        finally:
            current_user_var.set(None)

        assert result_alice["context"]["user"] == "alice"
        assert result_bob["context"]["user"] == "bob"


class TestSearchCache:
    async def test_second_search_uses_cache(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        result1 = await search("echo")
        assert "echo" in result1
        # Override cache with a nonexistent key sentinel — if cache is hit,
        # the loader filter drops it and search returns the "no results" message.
        cache_key = f"search:{params_hash({'q': 'echo', 's': None})}"
        await cache.set(cache_key, [("__nonexistent__", 99.0)], expire=60)
        result2 = await search("echo")
        assert result2.startswith("No tools matched")

    async def test_reload_clears_search_cache(self, load_fixture):
        from pathlib import Path

        fixture_path = str(Path(__file__).parent / "fixtures" / "tools_ungrouped.yaml")
        load_fixture("tools_ungrouped.yaml")
        loader.paths = {fixture_path}
        await loader.save()
        # Prime cache with a nonexistent key sentinel
        cache_key = f"search:{params_hash({'q': 'echo', 's': None})}"
        await cache.set(cache_key, [("__nonexistent__", 99.0)], expire=60)
        result1 = await search("echo")
        assert result1.startswith("No tools matched")  # served from cache
        # After reload the cache is busted — ES is hit and returns real results
        await loader.reload()
        result2 = await search("echo")
        assert "echo" in result2


class TestSessionTools:
    """set_session / get_session round-trip, scoping, reserved keys, and slug rules."""

    async def test_set_then_get_authed(self):
        from mcc.app import get_session, set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            assert "Set" in await set_session(ctx, "target", "example.com")
            assert json.loads(await get_session(ctx, "target")) == "example.com"
        finally:
            current_user_var.set(None)

    async def test_set_then_get_anonymous(self):
        from mcc.app import get_session, set_session

        current_user_var.set(None)
        ctx = _ctx_state()
        await set_session(ctx, "note", "hi")
        assert json.loads(await get_session(ctx, "note")) == "hi"

    async def test_value_types_preserved(self):
        from mcc.app import get_session, set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            await set_session(ctx, "budget", 1000)
            await set_session(ctx, "filters", {"q": "x"})
            assert json.loads(await get_session(ctx, "budget")) == 1000
            assert json.loads(await get_session(ctx, "filters")) == {"q": "x"}
        finally:
            current_user_var.set(None)

    async def test_missing_key_returns_none(self):
        from mcc.app import get_session

        current_user_var.set(UserModel(username="alice"))
        try:
            assert json.loads(await get_session(_ctx_state(), "nope")) is None
        finally:
            current_user_var.set(None)

    async def test_reserved_key_resolves_to_identity(self):
        from mcc.app import get_session

        current_user_var.set(UserModel(username="alice", groups=["admin"]))
        try:
            ctx = _ctx_state()
            assert json.loads(await get_session(ctx, "user")) == "alice"
            assert json.loads(await get_session(ctx, "groups")) == ["admin"]
        finally:
            current_user_var.set(None)

    async def test_set_rejects_reserved_key(self):
        from mcc.app import get_session, set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            result = await set_session(ctx, "user", "admin")
            assert "reserved" in result.lower()
            # identity is unchanged
            assert json.loads(await get_session(ctx, "user")) == "alice"
        finally:
            current_user_var.set(None)

    async def test_set_rejects_bad_slug(self):
        from mcc.app import set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            for bad in ("My Key", "1abc", "has-dash", "UPPER"):
                result = await set_session(ctx, bad, 1)
                assert "Invalid name" in result
            assert await _with_state_store_empty(ctx)
        finally:
            current_user_var.set(None)

    async def test_session_isolation_same_user(self):
        from mcc.app import get_session, set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx_a = _ctx_state(session="A")
            ctx_b = _ctx_state(session="B")
            await set_session(ctx_a, "secret", "in_a")
            assert json.loads(await get_session(ctx_b, "secret")) is None
        finally:
            current_user_var.set(None)

    async def test_user_isolation_same_session(self):
        # Same backing store + session id, different usernames → different keys.
        from mcc.app import get_session, set_session

        store: dict = {}

        def _ctx_for(session):
            ctx = MagicMock()

            async def _get(key):
                return store.get(f"{session}:{key}")

            async def _set(key, value):
                store[f"{session}:{key}"] = value

            ctx.get_state = AsyncMock(side_effect=_get)
            ctx.set_state = AsyncMock(side_effect=_set)
            return ctx

        ctx = _ctx_for("shared")
        current_user_var.set(UserModel(username="alice"))
        await set_session(ctx, "k", "alice_val")
        current_user_var.set(UserModel(username="bob"))
        try:
            assert json.loads(await get_session(ctx, "k")) is None
        finally:
            current_user_var.set(None)


async def _with_state_store_empty(ctx) -> bool:
    """True if no mutable var was written (only verifies set() was never persisted)."""
    return not ctx.set_state.await_count


class TestExecuteContextSnapshot:
    """execute() assembles the context snapshot and exposes it to the tool."""

    async def test_fn_tool_receives_stored_var_via_context(self, load_fixture):
        load_fixture("tools_context.yaml")
        from mcc.app import set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            await set_session(ctx, "budget", 42)
            result = await execute(ctx, "needs_context", {"x": 5})
            assert result["x"] == 5
            assert result["context"]["budget"] == 42
            assert result["context"]["user"] == "alice"
        finally:
            current_user_var.set(None)


class TestContextWriteback:
    """fn tools persist session state by mutating their injected `context`."""

    async def test_writeback_visible_to_later_tool(self, load_fixture):
        # A tool sets context["cursor"]; a later execute in the same session reads it.
        load_fixture("tools_context.yaml")
        from mcc.app import get_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            result = await execute(ctx, "stash_cursor", {"n": 6})
            assert result == 6
            # visible via get_session and injected into the next tool's context
            assert json.loads(await get_session(ctx, "cursor")) == 6
            follow = await execute(ctx, "needs_context", {"x": 1})
            assert follow["context"]["cursor"] == 6
        finally:
            current_user_var.set(None)

    async def test_no_context_param_does_not_touch_state(self, load_fixture):
        # no_context declares no `context` param → [result, null] → state untouched.
        load_fixture("tools_context.yaml")
        from mcc.app import set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            await set_session(ctx, "keep", "me")
            ctx.set_state.reset_mock()
            result = await execute(ctx, "no_context", {"x": 3})
            assert result == 3
            # no write-back occurred
            assert ctx.set_state.await_count == 0
        finally:
            current_user_var.set(None)

    async def test_empty_context_clears_non_identity_vars(self, load_fixture):
        # A tool that empties its context clears stored vars; identity survives.
        load_fixture("tools_context.yaml")
        from mcc.app import get_session, set_session

        current_user_var.set(UserModel(username="alice", groups=["admin"]))
        try:
            ctx = _ctx_state()
            await set_session(ctx, "budget", 42)
            result = await execute(ctx, "clear_context", {})
            assert result == "cleared"
            assert json.loads(await get_session(ctx, "budget")) is None
            # identity re-derived on read, still present
            assert json.loads(await get_session(ctx, "user")) == "alice"
            assert json.loads(await get_session(ctx, "groups")) == ["admin"]
        finally:
            current_user_var.set(None)

    async def test_cannot_spoof_or_delete_identity(self, load_fixture):
        # A tool sets user="admin" and deletes groups; both are ignored.
        load_fixture("tools_context.yaml")
        from mcc.app import get_session

        current_user_var.set(UserModel(username="alice", groups=["admin"]))
        try:
            ctx = _ctx_state()
            await execute(ctx, "spoof_identity", {})
            assert json.loads(await get_session(ctx, "user")) == "alice"
            assert json.loads(await get_session(ctx, "groups")) == ["admin"]
        finally:
            current_user_var.set(None)

    async def test_invalid_key_rejects_whole_writeback(self, load_fixture, caplog):
        # An invalid slug key rejects the write-back; result still returns; state kept.
        load_fixture("tools_context.yaml")
        from mcc.app import get_session, set_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            await set_session(ctx, "kept", "yes")
            with caplog.at_level("WARNING"):
                result = await execute(ctx, "bad_key", {})
            assert result == "ok"  # tool result still returned
            # prior state unchanged; the bad key was not written
            assert json.loads(await get_session(ctx, "kept")) == "yes"
            assert json.loads(await get_session(ctx, "bad key")) is None
            # the rejection log names the offending key
            assert "bad key" in caplog.text
        finally:
            current_user_var.set(None)

    async def test_list_result_unwrapped_correctly(self, load_fixture):
        # A list-valued result must not be confused with the [result, context] envelope.
        load_fixture("tools_context.yaml")
        from mcc.app import get_session

        current_user_var.set(UserModel(username="alice"))
        try:
            ctx = _ctx_state()
            result = await execute(ctx, "echo_list", {"items": [1, 2, 3]})
            assert result == [1, 2, 3]
            assert json.loads(await get_session(ctx, "seen")) is True
        finally:
            current_user_var.set(None)


def test_rate_limit_middleware_not_registered_when_disabled():
    # settings.yaml ships rate_limit.enabled: false, so the app under test
    # must not have registered RateLimitMiddleware at all.
    from mcc.app import mcp
    from mcc.middleware import RateLimitMiddleware

    assert not any(isinstance(mw, RateLimitMiddleware) for mw in mcp.middleware)
