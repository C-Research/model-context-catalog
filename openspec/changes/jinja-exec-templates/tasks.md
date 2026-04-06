## 1. Core Implementation

- [x] 1.1 Add Jinja2 environment with `StrictUndefined` and `| quote` filter to `mcc/exec.py`
- [x] 1.2 Replace `shlex`+`str.format` interpolation with Jinja template rendering in `make_exec_callable`
- [x] 1.3 Remove the blanket `shlex.quote` pre-pass over kwargs

## 2. Fixture Updates

- [x] 2.1 Update `tests/fixtures/tools_exec_interpolate.yaml` to Jinja syntax
- [x] 2.2 Audit and update any other `tests/fixtures/tools_exec_*.yaml` files that use `{param}` syntax

## 3. Tests

- [x] 3.1 Add test: scalar value with spaces is correctly quoted via `| quote`
- [x] 3.2 Add test: shell metacharacters in value are safely quoted
- [x] 3.3 Add test: list value with `| quote` joins and quotes each element
- [x] 3.4 Add test: empty list with `| quote` produces empty string
- [x] 3.5 Add test: conditional `{% if %}` block includes/excludes flag based on param
- [x] 3.6 Add test: unknown variable raises `UndefinedError` before subprocess runs
- [x] 3.7 Add test: EnvYAML `${VAR}` and Jinja `{{ }}` coexist correctly in same exec string

## 4. Docs

- [x] 4.1 Write `docs/exec-templates.md` covering Jinja syntax, `| quote` filter (scalar and list), conditional blocks, and EnvYAML composition
- [x] 4.2 Note in docs that quoting is the author's responsibility and omitting `| quote` on user input is a shell injection risk
- [x] 4.3 Register the new page in `mkdocs.yml`
