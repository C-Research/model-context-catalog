## 1. Dependency

- [x] 1.1 Add `scrapling[fetchers]` as the `scraping` optional-dependency group in `pyproject.toml` (already done via `uv add --optional scraping "scrapling[fetchers]"`)

## 2. Core callable

- [x] 2.1 Create `toolsets/contrib/scraping.py` with `async def scrape(urls, css=None, xpath=None, mode="static", timeout=30)`
- [x] 2.2 Lazily import `AsyncFetcher`, `DynamicFetcher`, `StealthyFetcher` inside the function body, guarded by `try/except ImportError` with a `pip install mcc[scraping]` message
- [x] 2.3 Validate at least one of `css`/`xpath` is given (`ValueError` otherwise) and that `mode` is one of `static`/`js`/`stealth` (`ValueError` otherwise)
- [x] 2.4 Implement per-URL fetch dispatch by `mode` → `AsyncFetcher.get` / `DynamicFetcher.async_fetch` / `StealthyFetcher.async_fetch`, passing `timeout`
- [x] 2.5 Implement per-URL field extraction: merge `css` matches (`page.css(selector).getall()`) and `xpath` matches (`page.xpath(selector).getall()`) into one fields dict per URL
- [x] 2.6 Run all URLs concurrently via `asyncio.gather`, bounded by a fixed internal `asyncio.Semaphore` (not a tool param)
- [x] 2.7 Isolate per-URL failures: catch exceptions per URL and store `f"{type(exc).__name__}: {exc}"` as that URL's result instead of raising
- [x] 2.8 Write a docstring covering params, `mode` semantics, and the fact that `js`/`stealth` require `playwright install chromium` on the host

## 3. Tool registration

- [x] 3.1 Create `toolsets/contrib/scraping.yaml` with an `admin, scraping` entry (unrestricted `mode`) and a `public, scraping` entry (`mode` forced via `override: static`), following `http.yaml`'s admin/public pattern
- [x] 3.2 Add `toolsets/contrib/scraping.yaml` to the `tools:` list in `toolsets/contrib/settings.yaml`

## 4. Tests

- [x] 4.1 Add `toolsets/contrib/tests/test_scraping.py`, mocking the lazily-imported `AsyncFetcher`/`DynamicFetcher`/`StealthyFetcher` (e.g. via `sys.modules`/`monkeypatch`) rather than hitting real network
- [x] 4.2 Test: single URL, CSS-only fields, returns expected fields dict
- [x] 4.3 Test: single URL, XPath-only fields, returns expected fields dict
- [x] 4.4 Test: combined CSS + XPath fields merge into one dict per URL
- [x] 4.5 Test: neither `css` nor `xpath` given raises `ValueError`
- [x] 4.6 Test: invalid `mode` raises `ValueError`
- [x] 4.7 Test: multiple URLs where one raises during fetch — result dict has an error string for that URL and normal fields dicts for the others
- [x] 4.8 Test: `mode="js"`/`"stealth"` dispatch to `DynamicFetcher`/`StealthyFetcher` respectively (mocked)
- [x] 4.9 Test: importing `toolsets.contrib.scraping` succeeds even when `scrapling` is not importable (simulate via `sys.modules` injection or monkeypatching the import)
- [x] 4.10 Test: calling `scrape` without `scrapling` installed raises `ImportError` mentioning `mcc[scraping]`

Note: the admin/public override (spec's "admin/public group split" requirement) is
verified at the schema level (`TestGroupSplit` in the same file) rather than via
`execute()`, because `fn` tools run in an isolated subprocess (`mcc.exec.make_py_callable`)
that a test-process `sys.modules` patch can't reach — an `execute()`-based test would
either hit real network or hang on `mode="js"`/`"stealth"` without Chromium installed.

## 5. Verification

- [x] 5.1 `uv run pytest toolsets/contrib/tests/test_scraping.py` — 13 passed
- [x] 5.2 `uv run pyright mcc/` — 0 errors (out of scope for `toolsets/`, matching AGENTS.md's `mcc/`-only pyright check and existing precedent for optional-dep imports there, e.g. `sherlock_search`)
- [x] 5.3 `uv run ruff check toolsets/contrib/scraping.py toolsets/contrib/tests/test_scraping.py` — only pre-existing-pattern `BLE001` on the per-URL `except Exception`, unsuppressed the same way `mcc/app.py`/`mcc/models.py`/`mcc/pyrunner.py` already do for the same isolate-failure-as-data purpose
- [x] 5.4 `uv run bandit -r mcc/ toolsets/ -c pyproject.toml` — no issues identified
- [x] 5.5 Manually loaded `toolsets/contrib/scraping.yaml` via `mcc.loader.load_file` and confirmed both `admin.scraping.scrape` (all params visible, no override) and `public.scraping.scrape-static` (`mode` hidden, forced to `"static"`) register correctly; also confirmed the full contrib toolset (`toolsets/contrib/settings.yaml`) still loads all 38 tools together without error

Note: ran the full `toolsets/contrib/tests/` suite too — 2 pre-existing failures in
`test_pysrc.py` (`TestListMembers`) reproduce identically on `main` without this
change, unrelated to scraping.
