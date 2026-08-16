# Agents

## pytest

Run the test suite with the following, checking for smoke tests first to fail fast:

```bash
uv run pytest -m smoke tests/
uv run pytest -m "not smoke" tests/
```

All tests must pass. Tests are async-first (`asyncio_mode = "auto"`). Do not mock the database or external services unless the test explicitly sets up a mock context — integration behavior matters here.

## ruff

Python files only 

Lint and format with:

```bash
uv run ruff check --fix mcc/ tests/
uv run ruff format mcc/ tests/
```

Fix lint errors before considering a task complete. Do not suppress warnings with `# noqa` unless there is a specific, documented reason.

## pyright

Python files only 

Type-check with:

```bash
uv run pyright mcc/
```

All type errors must be resolved. Do not use `# type: ignore` to silence errors without a comment explaining why.

## bandit

Python files only

Security-scan with:

```bash
uv run bandit -r mcc/ toolsets/ -c pyproject.toml
```

All findings must be resolved. Fix real issues; do not suppress with `# nosec` unless there is a specific, documented reason (e.g. a mitigation bandit's static analysis can't detect, or a check that doesn't apply in context).
