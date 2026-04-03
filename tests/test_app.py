from pathlib import Path

import pytest

from mcc.app import execute, search
from mcc.loader import Loader, loader

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_loader():
    loader.clear()
    yield
    loader.clear()


def _load(filename: str):
    loader.load(FIXTURES / filename)


class TestSearch:
    def test_matches_by_name(self):
        _load("tools_ungrouped.yaml")
        result = search("echo")
        assert "echo" in result
        assert "Echoes back" in result

    def test_no_match(self):
        _load("tools_ungrouped.yaml")
        assert search("zzz_nonexistent") == "No tools matched your query."

    def test_empty_query_returns_all(self):
        _load("tools_ungrouped.yaml")
        result = search("")
        assert "echo" in result

    def test_group_filter(self):
        _load("tools_grouped.yaml")
        assert "echo" in search("", group="example")
        assert search("", group="other") == "No tools matched your query."

    def test_grouped_display_name(self):
        _load("tools_grouped.yaml")
        result = search("echo")
        assert "example.echo" in result
        assert 'execute("example.echo"' in result

    def test_ungrouped_display_name(self):
        _load("tools_ungrouped.yaml")
        result = search("echo")
        assert "example.echo" not in result
        assert 'execute("echo"' in result


class TestExecute:
    def test_execute_by_name(self):
        _load("tools_ungrouped.yaml")
        result = execute("echo", {"message": "hi"})
        assert result == ["hi"]

    def test_execute_by_dotted_name(self):
        _load("tools_grouped.yaml")
        result = execute("example.echo", {"message": "hi"})
        assert result == ["hi"]

    def test_execute_wrong_group_fails(self):
        _load("tools_grouped.yaml")
        result = execute("wrong.echo", {"message": "hi"})
        assert "Unknown tool" in result

    def test_execute_unknown_tool(self):
        _load("tools_ungrouped.yaml")
        result = execute("nonexistent", {})
        assert "Unknown tool" in result

    def test_execute_validation_error(self):
        _load("tools_ungrouped.yaml")
        result = execute("echo", {})
        assert "Validation error" in result
