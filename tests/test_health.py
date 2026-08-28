import asyncio
import json

import mcc.app as app_module
import mcc.db.base as db_base
import mcc.routes as routes_module
from mcc.context import ANONYMOUS_USER, current_user_var
from mcc.routes import healthz, readyz
from starlette.requests import Request

# The handlers' own bodies never read the request, but both are wrapped by
# @route(anonymous=True), which always sets request.scope["user"] = ANONYMOUS_USER
# before calling them — so a real (if minimal) Request is needed, not a bare
# None stand-in.
_REQ = Request({"type": "http", "headers": [], "query_string": b""})


class _RaisingIndex:
    """Stand-in for UsersIndex whose __aenter__ raises, simulating an unreachable cluster."""

    async def __aenter__(self):
        raise RuntimeError("search backend unreachable")

    async def __aexit__(self, *exc):
        return False


class _SlowIndex:
    """Stand-in for UsersIndex whose __aenter__ outlasts the readyz timeout."""

    async def __aenter__(self):
        await asyncio.sleep(0.05)

    async def __aexit__(self, *exc):
        return False


def _body(response):
    return json.loads(response.body)


class TestHealthz:
    async def test_ok_with_no_backend_calls(self, monkeypatch):
        monkeypatch.setattr(routes_module, "UsersIndex", _RaisingIndex)

        async def _boom(*args, **kwargs):
            raise RuntimeError("cache must not be touched by /healthz")

        monkeypatch.setattr(routes_module.cache, "ping", _boom)

        response = await healthz(_REQ)
        assert response.status_code == 200
        assert _body(response) == {"status": "ok"}


class TestReadyz:
    async def test_ok_when_both_backends_reachable(self):
        response = await readyz(_REQ)
        assert response.status_code == 200
        assert _body(response) == {"status": "ok"}

    async def test_degraded_when_search_backend_down(self, monkeypatch):
        monkeypatch.setattr(routes_module, "UsersIndex", _RaisingIndex)
        response = await readyz(_REQ)
        assert response.status_code == 503
        assert _body(response) == {"status": "degraded"}

    async def test_degraded_when_loader_empty(self):
        original = dict(routes_module.loader)
        routes_module.loader.clear()
        try:
            response = await readyz(_REQ)
            assert response.status_code == 503
            assert _body(response) == {"status": "degraded"}
        finally:
            routes_module.loader.update(original)

    async def test_degraded_when_cache_down(self, monkeypatch):
        async def _boom(*args, **kwargs):
            raise RuntimeError("cache unreachable")

        monkeypatch.setattr(routes_module.cache, "ping", _boom)
        response = await readyz(_REQ)
        assert response.status_code == 503
        assert _body(response) == {"status": "degraded"}

    async def test_degraded_on_timeout(self, monkeypatch):
        monkeypatch.setattr(routes_module, "UsersIndex", _SlowIndex)
        monkeypatch.setattr(routes_module, "_READYZ_TIMEOUT", 0.01)
        response = await readyz(_REQ)
        assert response.status_code == 503
        assert _body(response) == {"status": "degraded"}

    async def test_failure_reason_not_leaked_in_body(self, monkeypatch, caplog):
        monkeypatch.setattr(routes_module, "UsersIndex", _RaisingIndex)
        with caplog.at_level("WARNING"):
            response = await readyz(_REQ)
        assert _body(response) == {"status": "degraded"}
        assert "search backend unreachable" not in bytes(response.body).decode()
        assert "search backend" in caplog.text

    async def test_does_not_load_embedding_model(self, monkeypatch):
        calls = []
        monkeypatch.setattr(db_base, "_get_model", lambda: calls.append("get_model"))

        async def _embed(*args, **kwargs):
            calls.append("embed")

        monkeypatch.setattr(db_base, "embed", _embed)

        response = await readyz(_REQ)
        assert response.status_code == 200
        assert calls == []


class TestNoAuthRequired:
    def test_routes_registered_as_custom_routes(self):
        paths = {
            getattr(route, "path", None)
            for route in app_module.mcp._additional_http_routes
        }
        assert "/healthz" in paths
        assert "/readyz" in paths

    async def test_handlers_ignore_caller_identity(self):
        # No MCP auth or user identity is consulted by either handler — calling
        # them with an explicitly unauthenticated context still succeeds,
        # unlike execute()/search() which check current_user_var.
        current_user_var.set(ANONYMOUS_USER)
        try:
            health = await healthz(_REQ)
            ready = await readyz(_REQ)
        finally:
            current_user_var.set(ANONYMOUS_USER)
        assert health.status_code == 200
        assert ready.status_code == 200
