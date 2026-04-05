# Agents

## pytest

Run the test suite with:

```bash
uv run pytest tests/
```

All tests must pass. Tests are async-first (`asyncio_mode = "auto"`). Do not mock the database or external services unless the test explicitly sets up a mock context — integration behavior matters here.

## ruff

Lint and format with:

```bash
uv run ruff check mcc/ tests/
uv run ruff format mcc/ tests/
```

Fix lint errors before considering a task complete. Do not suppress warnings with `# noqa` unless there is a specific, documented reason.

## pyright

Type-check with:

```bash
uv run pyright mcc/
```

All type errors must be resolved. Do not use `# type: ignore` to silence errors without a comment explaining why.



