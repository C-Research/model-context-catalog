from pathlib import Path

import yaml

from .models import ToolModel


def load_file(path: str | Path) -> list[ToolModel]:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        raise ValueError(f"Tool file {path} not found")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict) or "tools" not in raw:
        raise ValueError(
            f"{path}: expected a dict with a 'tools' key, got {type(raw).__name__}"
        )
    group: str | None = raw.get("group", None)
    return [ToolModel(group=group, **entry) for entry in raw["tools"]]


class Loader(dict):
    paths = set()

    def load(self, *paths: str | Path) -> None:
        for path in paths:
            self.paths.add(path)
            for tool in load_file(path):
                self.register(tool)

    def register(self, tool: ToolModel):
        if tool.key in self:
            raise ValueError(f"Duplicate tool name: {tool.key}")
        self[tool.key] = tool

    def reload(self):
        for key in self:
            del self[key]
        for path in self.paths:
            self.load(path)


loader = Loader()
loader.load(Path(__file__).parent / "tools.yaml")
