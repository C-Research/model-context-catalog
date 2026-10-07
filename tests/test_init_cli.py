from asyncio import run as arun

import pytest
from click.testing import CliRunner
from mcc.audit import AuditIndex, SearchAuditIndex
from mcc.cli.init import init
from mcc.db import KeysIndex, ToolIndex, UsersIndex
from mcc.settings import settings


async def _exists(idx_cls) -> bool:
    async with idx_cls() as idx:
        return bool(await idx._client.indices.exists(index=idx.index))


async def _drop(idx_cls) -> None:
    async with idx_cls() as idx:
        await idx.drop()


@pytest.fixture
def fresh_indices(monkeypatch):
    """Drops every index `mcc init` may touch before the test and after it.

    Audit index names are pinned to test indices on the class (their `index`
    attribute is read once at import, like the audit_idx fixture)."""
    monkeypatch.setattr(AuditIndex, "index", "mcc-audit-test")
    monkeypatch.setattr(SearchAuditIndex, "index", "mcc-audit-search-test")
    classes = [UsersIndex, KeysIndex, ToolIndex, AuditIndex, SearchAuditIndex]
    for cls in classes:
        arun(_drop(cls))
    yield
    for cls in classes:
        arun(_drop(cls))


class TestInit:
    def test_creates_users_and_keys_only_by_default(self, fresh_indices):
        assert not settings.AUDIT_TOOL_INDEX  # disabled for the whole test session
        result = CliRunner().invoke(init)
        assert result.exit_code == 0
        assert arun(_exists(UsersIndex))
        assert arun(_exists(KeysIndex))
        assert not arun(_exists(ToolIndex))
        assert not arun(_exists(AuditIndex))
        assert not arun(_exists(SearchAuditIndex))

    def test_creates_audit_indices_when_configured(self, fresh_indices, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_TOOL_INDEX", "mcc-audit-test")
        monkeypatch.setattr(settings, "AUDIT_SEARCH_INDEX", "mcc-audit-search-test")
        result = CliRunner().invoke(init)
        assert result.exit_code == 0
        assert arun(_exists(AuditIndex))
        assert arun(_exists(SearchAuditIndex))

    def test_is_idempotent(self, fresh_indices):
        assert CliRunner().invoke(init).exit_code == 0
        assert CliRunner().invoke(init).exit_code == 0
        assert arun(_exists(UsersIndex))
