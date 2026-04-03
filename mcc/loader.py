from pathlib import Path

import yaml

from mcc.models import ToolModel


def load_file(path: str | Path) -> list[ToolModel]:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        raise ValueError(f"Tool file {path} not found")
    tool = yaml.safe_load(path.read_text())
    if not isinstance(tool, dict) or "tools" not in tool:
        raise ValueError(
            f"{path}: expected a dict with a 'tools' key, got {type(tool).__name__}"
        )
    group: str | None = tool.get("group", None)
    return [ToolModel(group=group, **entry) for entry in tool["tools"]]


class Loader(dict):
    paths = set()

    def load(self, *paths: str | Path) -> None:
        for path in paths:
            path = Path(path)
            self.paths.add(path)
            if path.is_dir():
                for file in sorted(path.glob("*.y*ml")):
                    for tool in load_file(file):
                        self.register(tool)
            else:
                for tool in load_file(path):
                    self.register(tool)

    def register(self, tool: ToolModel):
        if tool.key in self:
            raise ValueError(f"Duplicate tool {tool.name} in group {tool.group}")
        self[tool.key] = tool

    def reload(self):
        self.clear()
        for path in self.paths:
            self.load(path)


loader = Loader()
loader.load(Path(__file__).parent / "tools")
