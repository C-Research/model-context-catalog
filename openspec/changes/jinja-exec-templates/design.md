## Context

Exec tools currently use `str.format()` for command interpolation, with `shlex.quote()` applied to every parameter unconditionally before substitution. This means all values are always shell-quoted — useful for safety, but prevents passing raw flags (`-v -f`), iterating over list params, or using conditional logic in the template. Jinja2 is already a project dependency (via FastMCP/other deps), making this a low-cost upgrade.

## Goals / Non-Goals

**Goals:**
- Replace `str.format(**safe)` with Jinja2 template rendering in `make_exec_callable`
- Add a `| quote` Jinja filter that calls `shlex.quote` for scalars and quote-joins lists
- Use `StrictUndefined` so missing variables raise a clear error rather than silently producing empty strings
- Update all exec fixture YAML files to Jinja syntax
- Document the new syntax and the EnvYAML `${VAR}` / Jinja `{{ }}` composition pattern

**Non-Goals:**
- Supporting the old `{param}` format-string syntax alongside Jinja (no dual-mode)
- Applying any automatic quoting — quoting is now fully the template author's responsibility
- Changing stdin mode (params sent as JSON on stdin are unaffected)

## Decisions

### Jinja2 as the templating engine

Jinja2 is already available in the environment. It supports filters, conditionals, and loops — all the flexibility needed. The alternative (a custom mini-language) would be more work for less capability.

### `| quote` filter semantics

- Scalar: `shlex.quote(str(value))`
- List: `" ".join(shlex.quote(str(v)) for v in value)` — produces `'a.txt' 'b.txt'` suitable for direct shell interpolation

### `StrictUndefined` for missing variables

Silent empty substitution in a shell command is dangerous (e.g., `rm -rf {{ path }}` becoming `rm -rf`). `StrictUndefined` raises `UndefinedError` immediately, which surfaces as a clear error before subprocess execution.

### Breaking change — no backward compat

Old `{param}` syntax is gone. All fixture YAML files are updated as part of this change. The conversion is mechanical: `{param}` → `{{ param | quote }}`. This keeps the implementation clean and avoids a dual-parse path.

### EnvYAML coexistence

EnvYAML processes `${VAR}` substitution at YAML load time, producing a plain Python string stored in `ToolModel.exec`. Jinja processes that string at call time. The two stages are completely independent — `${LOG_DIR}/out.txt` in a template becomes a literal path before Jinja ever sees it.

## Risks / Trade-offs

- **Author must apply `| quote` explicitly** — forgetting it on user-supplied input is a shell injection risk. Mitigation: docs prominently note this; `| quote` is shown in all examples.
- **Jinja adds a dependency** — already present, but worth noting it now becomes load-bearing for exec tools.
- **List params are a new concept** — the param model only supports scalar types today. List support via `| quote` works at the template level (pass a JSON array as a string, or extend ParamModel). Mitigation: scope this change to the templating layer only; list param types are a separate concern.

## Migration Plan

1. Update `make_exec_callable` in `mcc/exec.py`
2. Update all `tests/fixtures/tools_exec_*.yaml` to Jinja syntax
3. Add/update tests in `tests/test_exec.py`
4. Add docs page covering exec templating

No data migration needed — exec strings live only in YAML tool files, which are updated in step 2.
