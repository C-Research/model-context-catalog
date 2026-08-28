.PHONY: lint format typecheck test test-smoke test-rest check docs docs-osint docs-all serve serve-osint ui clean

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
	uv run zensical build -f toolsets/mkdocs.yml
	mv toolsets/site site/toolsets

serve:
	uv run python -m http.server -d site -b 127.0.0.1

# ── Web UI ──────────────────────────────────────────────────────────────────────

# Builds the optional web UI (ui/) and stages it where mcc/routes.py serves it
# from. mcc/static/ui/ is gitignored build output — settings.ui.enabled has
# nothing to mount until this has run.
ui:
	cd ui && pnpm install --frozen-lockfile && pnpm build
	rm -rf mcc/static/ui
	mkdir -p mcc/static
	cp -r ui/dist mcc/static/ui

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:
	rm -rf site/ mcc/static/ui
