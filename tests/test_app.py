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


def _ctx_raises():
    """Mock ctx whose elicit() raises — simulates a client that doesn't support elicitation."""
    ctx = MagicMock()
    ctx.elicit = AsyncMock(side_effect=Exception("elicitation not supported"))
    return ctx


def _ctx_accepts(**data):
    """Mock ctx whose elicit() returns an AcceptedElicitation with the given data fields."""

    class _Data(BaseModel):
        model_config = {"extra": "allow"}

    instance = _Data(**data)
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=AcceptedElicitation(data=instance))
    return ctx


def _ctx_declines():
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=DeclinedElicitation())
    return ctx


def _ctx_cancels():
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=CancelledElicitation())
    return ctx


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


class TestExecuteCache:
    async def test_cache_hit_skips_tool_call(self, load_fixture):
        # First call populates the cache with the real result.
        # We then overwrite the cache entry with a sentinel.
        # If the second call returns the sentinel, the cache was used.
        load_fixture("tools_cached.yaml")
        ctx = _ctx_raises()
        result1 = await execute(ctx, "echo", {"message": "hi"})
        assert result1 == ["hi"]
        cache_key = f"exec:echo:{params_hash({'message': 'hi'})}"
        await cache.set(cache_key, "sentinel", expire=60)
        result2 = await execute(ctx, "echo", {"message": "hi"})
        assert result2 == "sentinel"

    async def test_no_cache_ttl_always_calls_tool(self, load_fixture):
        # Tool without cache_ttl: manually set a cache entry and verify it's ignored.
        load_fixture("tools_ungrouped.yaml")
        ctx = _ctx_raises()
        result1 = await execute(ctx, "echo", {"message": "hi"})
        assert result1 == ["hi"]
        cache_key = f"exec:echo:{params_hash({'message': 'hi'})}"
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
