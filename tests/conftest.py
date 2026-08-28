import os
from pathlib import Path

import pytest

os.environ.update(
    {
        "MCC_AUTH": "dev-admin",
        "MCC_USER_INDEX": "mcc-users-test",
        "MCC_TOOL_INDEX": "mcc-tools-test",
        "MCC_KEY_INDEX": "mcc-keys-test",
        # Forced off regardless of a local settings.local.yaml override, so
        # "disabled by default" tests (and every other test not explicitly
        # opting in via the audit_idx/search_audit_idx fixtures) stay
        # meaningful independent of the developer's local dev settings.
        "MCC_AUDIT_TOOL_INDEX": "",
        "MCC_AUDIT_SEARCH_INDEX": "",
    }
)
FIXTURES = Path(__file__).parent / "fixtures"


from mcc.audit import AuditIndex, SearchAuditIndex
from mcc.cache import cache
from mcc.db import KeysIndex, ToolIndex, UsersIndex
from mcc.loader import load_file as load
from mcc.loader import loader
from mcc.settings import settings


@pytest.fixture(autouse=True)
async def clear_cache():
    await cache.clear()
    yield
    await cache.clear()


@pytest.fixture
async def tool_idx():
    async with ToolIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def users_idx():
    async with UsersIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def keys_idx():
    async with KeysIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def audit_idx(monkeypatch):
    """Isolated audit index for tests that call mcc.audit._record_call directly.

    settings.audit_tool_index ships empty (disabled) for the whole test session —
    on purpose, so auditing stays off for every other test and the
    "not registered by default" test stays meaningful — so this points
    AuditIndex.index at a test index directly rather than via settings,
    the only lever that works once mcc.audit has already been imported.
    """
    monkeypatch.setattr(AuditIndex, "index", "mcc-audit-test")
    async with AuditIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def search_audit_idx(monkeypatch):
    """Isolated search-audit index, mirroring audit_idx.

    Unlike tool-call auditing (a hook registered once at import time),
    search() checks settings.AUDIT_SEARCH_INDEX itself on every call, so this
    also monkeypatches that setting truthy — otherwise search() never calls
    _record_search regardless of where SearchAuditIndex.index points.
    """
    monkeypatch.setattr(SearchAuditIndex, "index", "mcc-search-audit-test")
    monkeypatch.setattr(settings, "AUDIT_SEARCH_INDEX", "mcc-search-audit-test")
    async with SearchAuditIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def load_fixture():
    def _inner(*fns):
        loader.clear()
        for fn in fns:
            loader.load(FIXTURES / fn)

    return _inner


@pytest.fixture
async def load_file():
    return lambda fn: load(FIXTURES / fn)
