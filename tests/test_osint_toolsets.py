from pathlib import Path

from envyaml import EnvYAML

from mcc.loader import load_file


def test_osint_settings_paths_exist_and_load():
    repo_root = Path(__file__).resolve().parents[1]
    settings_path = repo_root / "toolsets" / "osint" / "settings.yaml"
    settings = EnvYAML(settings_path, strict=False)
    tool_paths = settings["default"]["tools"]

    assert tool_paths
    for tool_path in tool_paths:
        absolute_path = repo_root / tool_path
        assert absolute_path.is_file(), f"Missing OSINT tool file: {tool_path}"
        assert load_file(absolute_path), f"No tools loaded from: {tool_path}"
