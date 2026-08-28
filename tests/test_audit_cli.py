from asyncio import run as arun
from datetime import UTC, datetime

from click.testing import CliRunner
from mcc.cli.audit import audit
from mcc.settings import settings


def _iso(hour: int) -> str:
    return datetime(2026, 1, 1, hour, tzinfo=UTC).isoformat()


def _tool_doc(hour: int, username: str, tool_key: str = "admin.shell") -> dict:
    return {
        "timestamp": _iso(hour),
        "username": username,
        "key_prefix": None,
        "tool_key": tool_key,
        "status": "success",
        "error": None,
        "duration_ms": 1.0,
    }


def _search_doc(hour: int, username: str, query: str, results: str = "admin.shell=8.0") -> dict:
    return {
        "timestamp": _iso(hour),
        "username": username,
        "query": query,
        "min_score": None,
        "results": results,
    }


async def _seed(idx_cls, docs: dict[str, dict]) -> None:
    """Writes docs through a fresh connection, opened and closed within this
    one asyncio.run() call — CliRunner.invoke() below runs the CLI command's
    own separate asyncio.run(), so a fixture's already-open client (bound to
    a different event loop) can't be reused here."""
    async with idx_cls() as idx:
        for doc_id, doc in docs.items():
            await idx.put(doc_id, doc)


class TestAuditToolCommand:
    def test_not_configured_prints_notice(self):
        assert not settings.AUDIT_TOOL_INDEX  # disabled for the whole test session
        result = CliRunner().invoke(audit, ["tool"])
        assert result.exit_code == 0
        assert "not configured" in result.output

    def test_lists_newest_first(self, audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_TOOL_INDEX", "mcc-audit-test")
        arun(
            _seed(
                type(audit_idx),
                {
                    str(i): _tool_doc(i, username)
                    for i, username in enumerate(["alice", "bob", "carol"])
                },
            )
        )
        result = CliRunner().invoke(audit, ["tool"])
        assert result.exit_code == 0
        assert result.output.index("carol") < result.output.index("alice")

    def test_filters_by_user(self, audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_TOOL_INDEX", "mcc-audit-test")
        arun(
            _seed(
                type(audit_idx),
                {"1": _tool_doc(0, "alice"), "2": _tool_doc(1, "bob")},
            )
        )
        result = CliRunner().invoke(audit, ["tool", "--user", "alice"])
        assert "alice" in result.output
        assert "bob" not in result.output

    def test_filters_by_tool_key(self, audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_TOOL_INDEX", "mcc-audit-test")
        arun(
            _seed(
                type(audit_idx),
                {
                    "1": _tool_doc(0, "alice", "admin.shell"),
                    "2": _tool_doc(1, "alice", "public.request"),
                },
            )
        )
        result = CliRunner().invoke(audit, ["tool", "--tool-key", "admin.shell"])
        assert "admin.shell" in result.output
        assert "public.request" not in result.output

    def test_offset_and_limit_page_correctly(self, audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_TOOL_INDEX", "mcc-audit-test")
        arun(
            _seed(
                type(audit_idx),
                {str(i): _tool_doc(i, f"user{i}") for i in range(5)},
            )
        )
        # newest first: user4, user3, user2, user1, user0 -- offset 1, limit 2 -> user3, user2
        result = CliRunner().invoke(audit, ["tool", "--offset", "1", "--limit", "2"])
        assert "user3" in result.output
        assert "user2" in result.output
        assert "user4" not in result.output
        assert "user1" not in result.output
        assert "user0" not in result.output

    def test_defaults_are_zero_offset_twenty_limit(self):
        params = {p.name: p.default for p in audit.commands["tool"].params}
        assert params["offset"] == 0
        assert params["limit"] == 20


class TestAuditSearchCommand:
    def test_not_configured_prints_notice(self):
        assert not settings.AUDIT_SEARCH_INDEX  # disabled for the whole test session
        result = CliRunner().invoke(audit, ["search"])
        assert result.exit_code == 0
        assert "not configured" in result.output

    def test_lists_newest_first(self, search_audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_SEARCH_INDEX", "mcc-search-audit-test")
        arun(
            _seed(
                type(search_audit_idx),
                {
                    "1": _search_doc(0, "alice", "shell"),
                    "2": _search_doc(1, "alice", "http"),
                },
            )
        )
        result = CliRunner().invoke(audit, ["search"])
        assert result.exit_code == 0
        assert result.output.index("http") < result.output.index("shell")

    def test_filters_by_user(self, search_audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_SEARCH_INDEX", "mcc-search-audit-test")
        arun(
            _seed(
                type(search_audit_idx),
                {
                    "1": _search_doc(0, "alice", "shell command"),
                    "2": _search_doc(1, "bob", "http request"),
                },
            )
        )
        result = CliRunner().invoke(audit, ["search", "--user", "alice"])
        assert "shell command" in result.output
        assert "http request" not in result.output

    def test_filters_by_query_text(self, search_audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_SEARCH_INDEX", "mcc-search-audit-test")
        arun(
            _seed(
                type(search_audit_idx),
                {
                    "1": _search_doc(0, "alice", "shell command"),
                    "2": _search_doc(1, "alice", "http request"),
                },
            )
        )
        result = CliRunner().invoke(audit, ["search", "--query", "shell"])
        assert "shell command" in result.output
        assert "http request" not in result.output

    def test_offset_and_limit_page_correctly(self, search_audit_idx, monkeypatch):
        monkeypatch.setattr(settings, "AUDIT_SEARCH_INDEX", "mcc-search-audit-test")
        arun(
            _seed(
                type(search_audit_idx),
                {str(i): _search_doc(i, "alice", f"query{i}") for i in range(5)},
            )
        )
        result = CliRunner().invoke(audit, ["search", "--offset", "1", "--limit", "2"])
        assert "query3" in result.output
        assert "query2" in result.output
        assert "query4" not in result.output
        assert "query1" not in result.output
        assert "query0" not in result.output

    def test_defaults_are_zero_offset_twenty_limit(self):
        params = {p.name: p.default for p in audit.commands["search"].params}
        assert params["offset"] == 0
        assert params["limit"] == 20
