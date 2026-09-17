from click.testing import CliRunner

from mcc.cli.tools import tool


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
