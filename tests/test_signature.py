import pytest

from mcc.models import ParamModel, ToolModel


@pytest.fixture
def echo_tool():
    """Mirrors tests/fixtures/tools_ungrouped.yaml"""
    return ToolModel(
        name="echo",
        fn="tests.example:echo",
        params=[
            ParamModel(
                name="message",
                type="str",
                required=True,
                description="The message to echo back",
            )
        ],
        description="Echoes back the provided message",
        return_type="str",
    )


@pytest.mark.smoke
class TestSignature:
    def test_heading(self, echo_tool):
        assert "## echo" in echo_tool.signature

    def test_no_groups_line_when_ungrouped(self, echo_tool):
        assert "groups:" not in echo_tool.signature

    def test_groups_line_when_grouped(self, echo_tool):
        echo_tool.groups = ["example"]
        assert "## example.echo" in echo_tool.signature

    def test_required_param(self, echo_tool):
        sig = echo_tool.signature
        assert "`message`" in sig
        assert "message:str" in sig

    def test_param_description(self, echo_tool):
        assert "The message to echo back" in echo_tool.signature

    def test_return_type(self, echo_tool):
        assert "-> str" in echo_tool.signature

    def test_description_present(self, echo_tool):
        assert "Echoes back the provided message" in echo_tool.signature
