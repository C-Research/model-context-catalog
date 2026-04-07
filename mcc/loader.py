import glob as glob_module
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from time import time
from typing import Optional

from envyaml import EnvYAML

from mcc.db import ToolIndex
from mcc.models import ToolModel
from mcc.settings import logger, settings


def _resolve_python(raw: str | None) -> str:
    """Resolve a python interpreter path to its absolute form."""
    candidate = raw or sys.executable
    return shutil.which(candidate) or candidate


def _introspect_key(entry: dict) -> tuple:
    """Grouping key for batch introspection: (python, cwd, env_file, env_items)."""
    return (
        _resolve_python(entry.get("python")),
        entry.get("cwd") or "",
        entry.get("env_file") or "",
        tuple(sorted((entry.get("env") or {}).items())),
    )


def _batch_introspect(
    python: str,
    fn_paths: list[str],
    source_path: Path,
    cwd: str | None,
    env_file: str | None,
    env: dict[str, str] | None,
) -> dict[str, dict]:
    """Run one introspect subprocess for all fn_paths sharing the same interpreter.

    Returns a map of fn_path → result dict. Raises ValueError on subprocess
    failure or per-item introspection errors, with the source file and full
    traceback in the message.
    """
    from mcc.exec import _build_env

    pyrunner_path = str(Path(__file__).with_name("pyrunner.py"))
    run_kwargs: dict = {"capture_output": True, "text": True, "timeout": 60}
    if cwd:
        run_kwargs["cwd"] = cwd
    merged_env = _build_env(env, env_file)
    # Always set MCC_SKIP_AUTOLOAD to prevent recursive subprocess spawning
    # when introspected tools import mcc.loader (e.g. loader.reload)
    introspect_env = dict(merged_env if merged_env is not None else os.environ)
    introspect_env["MCC_SKIP_AUTOLOAD"] = "1"
    run_kwargs["env"] = introspect_env

    logger.debug("introspecting %d fn(s) with %s: %s", len(fn_paths), python, fn_paths)
    t0 = time()
    result = subprocess.run(
        [python, pyrunner_path, "introspect", *fn_paths],
        **run_kwargs,
    )
    logger.debug("introspect subprocess finished in %dms", (time() - t0) * 1000)
    if result.returncode != 0:
        raise ValueError(
            f"Introspection subprocess failed for {source_path}:\n{result.stderr}"
        )

    items: list[dict] = json.loads(result.stdout)
    results: dict[str, dict] = {}
    for item in items:
        fn_path = item["fn_path"]
        if "error" in item:
            raise ValueError(
                f"Failed to load tool '{fn_path}' from {source_path}:\n{item['error']}"
            )
        results[fn_path] = item
    return results


def load_file(path: str | Path) -> list[ToolModel]:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        raise ValueError(f"Tool file {path} not found")
    tool = EnvYAML(path, strict=False)
    if "tools" not in tool:
        raise ValueError(
            f"{path}: expected a dict with a 'tools' key, got {type(tool).__name__}"
        )
    parent_groups: list[str] = tool.get("groups", [])  # type: ignore[assignment]  # EnvYAML stubs return Unknown|None regardless of default
    entries: list[dict] = list(tool.get("tools", []))  # type: ignore[arg-type]  # EnvYAML stubs return Unknown|None regardless of default

    # Pre-pass: batch introspect fn entries that need it, grouped by interpreter
    needs_introspect = [
        (i, e) for i, e in enumerate(entries) if e.get("fn") and not e.get("params")
    ]
    if needs_introspect:
        groups: dict[tuple, list[tuple[int, dict]]] = defaultdict(list)
        for i, e in needs_introspect:
            groups[_introspect_key(e)].append((i, e))

        for key, group in groups.items():
            python, cwd, env_file, env_items = key
            env = dict(env_items) if env_items else None
            fn_paths = [e["fn"] for _, e in group]
            results = _batch_introspect(
                python, fn_paths, path, cwd or None, env_file or None, env
            )
            for _, e in group:
                info = results[e["fn"]]
                if not e.get("name"):
                    e["name"] = info["name"]
                if not e.get("description"):
                    e["description"] = info["doc"]
                e["params"] = info["params"]
                e["return_type"] = info.get("return_type")

    tools = [
        # fromkeys deduplicates while preserving order
        ToolModel(
            groups=list(dict.fromkeys(parent_groups + entry.pop("groups", []))), **entry
        )
        for entry in entries
    ]
    return tools


class Loader(dict):
    paths = set()

    def load(self, *paths: str) -> None:
        t0 = time()
        before = len(self)
        for path in paths:
            path_str = str(path)
            self.paths.add(path_str)
            if any(c in path_str for c in ("*", "?", "[")):
                for file in sorted(glob_module.glob(path_str, recursive=True)):
                    for tool in load_file(file):
                        self.register(tool)
            else:
                path = Path(path_str)
                if path.is_dir():
                    for file in sorted(path.glob("*.y*ml")):
                        for tool in load_file(file):
                            self.register(tool)
                else:
                    for tool in load_file(path):
                        self.register(tool)
        added = len(self) - before
        logger.debug(
            "Loaded %d tools in %dms from %s ",
            added,
            (time() - t0) * 1000,
            [str(p) for p in paths],
        )

    def register(self, tool: ToolModel):
        if tool.key in self:
            raise ValueError(f"Duplicate tool {tool.name} in groups {tool.groups}")
        self[tool.key] = tool

    async def save(self) -> None:
        logger.debug("Indexing %d tools to Elasticsearch...", len(self))
        t0 = time()
        async with ToolIndex() as idx:
            await idx.drop()
            await idx.create()
            for tool in self.values():
                await idx.index_tool(tool)
        logger.debug("Indexing complete in %dms", (time() - t0) * 1000)

    async def reload(self):
        logger.info("Reloading tools...")
        t0 = time()
        self.clear()
        for path in self.paths:
            self.load(path)
        await self.save()
        logger.info("Reloaded %d tools in %dms", len(self), (time() - t0) * 1000)

    async def search(
        self, query: str, min_score: Optional[float] = None
    ) -> list[tuple[ToolModel, float]]:
        async with ToolIndex() as idx:
            hits = await idx.query(query, min_score)
        return [(self[k], score) for k, score in hits if k in self]

    def list_all(self):
        return "\n\n".join([self[key].signature for key in sorted(self)])


loader = Loader()
if not os.environ.get("MCC_SKIP_AUTOLOAD"):
    loader.load(Path(__file__).parent / "tools")
    if settings.contrib:
        loader.load(Path(__file__).parent / "contrib")
    if settings.tools:
        loader.load(*settings.tools)
