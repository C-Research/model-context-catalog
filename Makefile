.PHONY: lint format typecheck test test-smoke test-rest check docs docs-osint docs-all serve serve-osint clean

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	uv run ruff check --fix mcc/ tests/ osint/*.py

format:
	uv run ruff format mcc/ tests/ osint/*.py

typecheck:
	uv run pyright mcc/ osint/*.py

test-smoke:
	uv run pytest -m smoke tests/

test-rest:
	uv run pytest -m "not smoke" tests/

test: test-smoke test-rest

# Run all checks (lint → format → typecheck → test)
check: lint format typecheck test

# ── Docs ──────────────────────────────────────────────────────────────────────

docs:
	uv run zensical build -f mkdocs.yml
	uv run zensical build -f osint/mkdocs.yml
	mv osint/site site/osint


# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:
	rm -rf site/
