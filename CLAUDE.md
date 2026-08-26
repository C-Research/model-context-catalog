# CLAUDE.md

## What this project is

MCC (Model Context Catalog) is an MCP server that exposes Python callables as a permission-controlled tool catalog. LLM clients discover and call tools through a `search` / `execute` interface with RBAC and pluggable auth.

## Agents

See [AGENTS.md](./AGENTS.md) for how to run pytest, ruff, pyright, and bandit. Always run all four before considering a task complete.

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

## Code style

- **Imports at module level.** All imports go at the top of the file. Never use method-level or function-level imports unless required to break a circular dependency (and document why with a comment).
- **`tests/`, `toolsets/contrib/tests/`, and `scripts/` are excluded from ruff and pyright** (see `[tool.ruff]`/`[tool.pyright]` in `pyproject.toml`). Test helper scripts don't need to satisfy the same type/lint bar as shipped code — don't fight the linter there, and don't add per-file `noqa`s to work around it.
- **`X | None`, not `Optional[X]`.** Ruff's UP045 flags this repo-wide; write the union form from the start.
- **Import `Callable`/`Awaitable` from `collections.abc`, not `typing`** (UP035).
- **`subprocess.run(...)` needs an explicit `check=` kwarg** (PLW1510). If the caller inspects `result.returncode` itself (mcc's pyrunner subprocess calls all do this), pass `check=False` explicitly — passing it inside a `**kwargs` dict doesn't satisfy the rule, it has to be a literal keyword at the call site.
- **Class-level mutable defaults (`= {}`, `= set()`, `= []`) need `ClassVar[...]`** (RUF012), even on plain classes and test fixtures.
- **`except Exception` is flagged (BLE001).** Prefer catching the specific exception type. Where a broad catch is genuinely the right call (subprocess/CLI top-level boundaries, best-effort auth fallbacks that must never crash the request), keep it but add `# noqa: BLE001` — don't invent a narrower exception type that isn't actually what can be raised there.
- **Unused unpacked tuple elements get a leading underscore** (`code, _out, _err = ...`), not a bare unused name (RUF059).
- **`raise` inside an `except ... as exc:` block, not `raise exc`** (TRY201) — preserves the original traceback and satisfies the linter.
- **`datetime.fromtimestamp()` needs an explicit `tz=`** (DTZ006) — use `datetime.UTC` (not `timezone.utc`, per UP017) unless local time is specifically intended.
- **Collapse nested `if` into one `and`-joined condition where possible** (SIM102).
- **Remove stale `# noqa` comments** once the rule they suppressed no longer fires (RUF100) — ruff treats an unused blanket `noqa` as an error, not a no-op.

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
