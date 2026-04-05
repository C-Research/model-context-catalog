from pathlib import Path

import yaml

from mcc.models import ToolModel
from mcc.settings import settings
from mcc.db import ToolIndex


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
    groups: list[str] = tool.get("groups", ["public"])
    return [
        ToolModel(groups=entry.pop("groups", groups), **entry) for entry in tool["tools"]
    ]


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
            raise ValueError(f"Duplicate tool {tool.name} in groups {tool.groups}")
        self[tool.key] = tool

    async def save(self) -> None:
        async with ToolIndex() as idx:
            await idx.drop()
            await idx.create()
            for tool in self.values():
                await idx.put(tool)

    async def reload(self):
        self.clear()
        for path in self.paths:
            self.load(path)
        await self.save()

    async def search(self, query: str, group: str | None = None) -> list[ToolModel]:
        async with ToolIndex() as idx:
            keys = await idx.search(query, group)
        return [self[k] for k in keys if k in self]

    def list_all(self):
        return "\n\n".join([tool.signature for tool in self.values()])


loader = Loader()
loader.load(Path(__file__).parent / "tools")
if settings.contrib:
    loader.load(Path(__file__).parent / "contrib")
if settings.tools:
    loader.load(*settings.tools)
