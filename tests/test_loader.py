from pathlib import Path

import pytest

from mcc.loader import Loader, load_file

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadFile:
    def test_loads_ungrouped(self):
        tools, group = load_file(FIXTURES / "tools_ungrouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert group is None

    def test_loads_grouped(self):
        tools, group = load_file(FIXTURES / "tools_grouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert group == "example"

    def test_rejects_missing_tools_key(self):
        with pytest.raises(ValueError, match="expected a dict with a 'tools' key"):
            load_file(FIXTURES / "tools_missing_key.yaml")

    def test_rejects_missing_file(self):
        with pytest.raises(ValueError, match="not found"):
            load_file(FIXTURES / "nonexistent.yaml")


class TestLoader:
    def test_load_ungrouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        assert "echo" in loader
        assert loader["echo"]["group"] is None

    def test_load_grouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "example.echo" in loader
        assert loader["example.echo"]["group"] == "example"

    def test_same_name_different_groups(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "echo" in loader
        assert "example.echo" in loader

    def test_duplicate_tool_raises(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        with pytest.raises(ValueError, match="Duplicate tool name"):
            loader.load(FIXTURES / "tools_ungrouped.yaml")

    def test_name_defaults_to_fn_name(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_name.yaml")
        assert "echo" in loader

    def test_description_defaults_to_fn_docstring(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_description.yaml")
        assert loader["doc_tool"]["description"] == "A tool loaded from its docstring."

    def test_registry_entry_has_expected_keys(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        entry = loader["echo"]
        assert callable(entry["fn"])
        assert "model" in entry
        assert entry["description"] == "Echoes back the provided message"
        assert isinstance(entry["params"], list)
        assert "group" in entry
