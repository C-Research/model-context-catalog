import asyncio
from pathlib import Path

from click.testing import CliRunner

from mcc.cli.tools import tool
from mcc.db import ToolIndex
from mcc.loader import loader

FIXTURES = Path(__file__).parent / "fixtures"


class TestToolReindex:
    def test_reindex_repopulates_index_from_disk(self, load_fixture, tool_idx):
        load_fixture("tools_ungrouped.yaml")
        loader.paths = {str(FIXTURES / "tools_ungrouped.yaml")}

        result = CliRunner().invoke(tool, ["reindex"])

        assert result.exit_code == 0
        assert "Reindexed 1 tools." in result.output

        async def _query():
            async with ToolIndex() as idx:
                return await idx.query("echo", None, None)

        hits = asyncio.run(_query())
        assert "echo" in [key for key, _ in hits]


class TestToolCallValidationError:
    def test_missing_required_param_shows_description(self, load_fixture):
        load_fixture("tools_validation_error.yaml")
        result = CliRunner().invoke(
            tool, ["call", "create_contact", "email=jane@example.com"]
        )
        assert result.exit_code == 1
        assert "The contact's full name" in result.output

    def test_unknown_param_suggests_correction(self, load_fixture):
        load_fixture("tools_validation_error.yaml")
        result = CliRunner().invoke(
            tool,
            ["call", "create_contact", "fullname=Jane Doe", "email=jane@example.com"],
        )
        assert result.exit_code == 1
        assert "did you mean `full_name`?" in result.output
