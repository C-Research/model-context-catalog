# CLAUDE.md

## What this project is

MCC (Model Context Catalog) is an MCP server that exposes Python callables as a permission-controlled tool catalog. LLM clients discover and call tools through a `search` / `execute` interface with RBAC and pluggable auth.

## Agents

See [AGENTS.md](./AGENTS.md) for how to run pytest, ruff, and pyright. Always run all three before considering a task complete.

## Running the server

```bash
uv run python -m mcc.cli
```

Configuration is loaded via [dynaconf](https://www.dynaconf.com/) from `mcc/settings.yaml`. Local overrides go in `settings.local.yaml` (not committed). Environment variables override settings using the `MCC_` prefix (e.g. `MCC_AUTH=dangerous`).

## Key concepts

- **Tools** are defined in YAML files that point at Python callables. Load them with `mcc tool add`.
- **Users** are stored in Elasticsearch and managed with `mcc user add/list/remove`.
- **Auth backends**: `dangerous` (dev mode, no auth), `github_oauth`, or `github_pat`. Set via `auth:` in settings.
- **Tool groups** control which users can call which tools (RBAC).
- **Contrib tools** are optional built-in tools (HTTP, shell, etc.) enabled with `contrib: true`.

## Tests

Tests require a running Elasticsearch instance. The conftest sets up and tears down isolated test indices (`mcc-users-test`, `mcc-tools-test`) automatically — do not share indices with a running dev server.

```bash
uv run pytest tests/
```

## Docs

Docs are written in Markdown under `docs/` and built with [zensical](https://zensical.org/).

```bash
# Serve locally with live reload
uv run zensical serve

# Build static site to site/
uv run zensical build
```

The nav structure is defined in `mkdocs.yml`. When adding a new page, register it there. The built `site/` directory is not committed.

## Project layout

```
mcc/
  app.py          # FastMCP app entrypoint
  loader.py       # YAML tool loader
  db.py           # Elasticsearch index wrappers (UsersIndex, ToolIndex)
  models.py       # Core data models
  settings.py     # Dynaconf settings
  auth/           # Auth backends and user management
  cli/            # Rich-click CLI (mcc user, mcc tool, mcc mcp)
  contrib/        # Optional built-in tools
  tools/          # Tool execution and search
tests/            # pytest integration tests
docs/             # MkDocs source
```
