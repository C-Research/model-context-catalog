## Context

MCC's contrib toolsets (`toolsets/contrib/*.py` + matching `*.yaml`) are all loaded from a single opt-in `toolsets/contrib/settings.yaml` (enabled via `MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml`). Loading introspects every `fn` entry by importing its module in a subprocess (`mcc/pyrunner.py introspect`), which runs at server startup / `mcc tool add` time — before any tool is actually called.

`toolsets/osint/people.py:sherlock_search` already establishes the pattern for an optional heavy dependency in this codebase: the import is inside the function body, guarded by `try/except ImportError` with a message pointing at the right `pip install mcc[extra]` command. That's necessary because introspection only inspects the function signature/docstring — it does not call the function — so a lazy import lets the module load (and the rest of the toolset register) even when the optional package isn't installed.

`scrapling` needs the `[fetchers]` extra to do anything useful: the bare package has no working `Fetcher`/`AsyncFetcher` (missing `curl_cffi`), and `DynamicFetcher`/`StealthyFetcher` need `playwright`/`patchright`. `scrapling[fetchers]` has already been added as `pyproject.toml`'s `scraping` optional-dependency group.

## Goals / Non-Goals

**Goals:**
- Fetch one or more URLs and extract named fields via CSS and/or XPath selectors in a single tool call.
- Support pages that need JS rendering or anti-bot evasion, without forcing that cost on every call.
- Keep the failure mode of one bad URL from taking down an entire multi-page batch.
- Keep the contrib toolset loadable for deployers who haven't installed the `scraping` extra.
- Gate the heavier/riskier fetch modes behind the `admin` group, the same way `http.yaml` gates unrestricted HTTP methods.

**Non-Goals:**
- Automating `playwright install chromium` / browser provisioning — that remains a deployment step, documented but not scripted by this change.
- Structured multi-selector chaining (e.g. selecting within a selected sub-tree, pagination-follow, or scraping infinite-scroll content) — out of scope for this MVP.
- Rate-limiting or politeness policies beyond a fixed internal concurrency cap (no per-domain throttling, robots.txt handling, etc.).
- A generic "any CSS/XPath library" abstraction — this is a thin wrapper around Scrapling's own `.css()`/`.xpath()`/`.getall()`, not a new selector engine.

## Decisions

**One function, dict-valued `css`/`xpath` params instead of a single selector string.**
A `{field_name: selector}` mapping lets one call pull multiple named fields per page (title, price, link, …) instead of round-tripping once per field. Scrapling's selectors already support Scrapy-style pseudo-selectors inline (`"h1::text"`, `"a::attr(href)"`), so no separate "extract text" vs. "extract attribute" API is needed — the selector string itself encodes that. `css` and `xpath` can both be given in the same call (merged into one fields dict per page); at least one is required.

**`mode: str` enum (`static` / `js` / `stealth`) instead of separate booleans.**
Considered `render_js: bool` + `stealth: bool` as two independent flags, but `stealth=True, render_js=False` is a nonsensical combination that would need extra validation to reject. A single string param with three valid values maps 1:1 onto Scrapling's three fetcher classes (`AsyncFetcher`, `DynamicFetcher`, `StealthyFetcher`) and has no invalid combinations to guard against.

**Per-URL failure isolation, not all-or-nothing.**
`asyncio.gather` over per-URL fetch+extract, with each URL's own try/except: a failure becomes an error string for that URL's value in the result dict rather than raising and losing every other page's results. This matches the spirit of `loader._batch_introspect`'s per-item error handling, and is more useful to an LLM doing a multi-page pull than an exception that discards partial progress.

**Small internal concurrency cap, not a tool param.**
`js`/`stealth` modes each spin up a headless browser page; unbounded concurrency across a large `urls` list could exhaust the host. A fixed internal `asyncio.Semaphore` bounds this. It's not exposed as a tool param — it's a resource-safety detail, not something callers need to tune, and keeping it out of the schema keeps the tool's surface area small.

**`admin`/`public` YAML split, mirroring `http.yaml`.**
`http.yaml` already has this exact pattern: an unrestricted `admin, http` entry and a locked-down `public, http` entry (`responsible-get`) that overrides risky params via `override:`. `scraping.yaml` does the same — `public, scraping` forces `mode` to `static` via `override: static`, so untrusted callers can't trigger headless-browser spin-up (a much heavier resource cost, and a wider SSRF-via-browser surface, than a plain HTTP GET).

**Lazy import inside the function body, not module level.**
Because `toolsets/contrib/settings.yaml` loads every contrib tool file together, a module-level `import scrapling` would make loading `scraping.yaml` — and therefore the whole contrib toolset load call — raise at introspection time for any deployer who has enabled contrib tools but not the `scraping` extra. The lazy-import-with-`ImportError`-message pattern from `sherlock_search` avoids this: the module always imports cleanly, and the clear error only surfaces when `scrape()` is actually called without the dependency installed.

## Risks / Trade-offs

- **[Risk]** `js`/`stealth` modes require `playwright install chromium` on the host, which `uv add`/`pip install` doesn't do automatically → **Mitigation**: documented in the tool's YAML `description` and this design doc; calling `scrape(mode="js", ...)` without the browser installed surfaces Scrapling's own clear error, not a silent failure.
- **[Risk]** Headless browser processes are expensive; a large `urls` list with `mode="js"`/`"stealth"` could still be heavy even with a concurrency cap → **Mitigation**: cap kept deliberately small (5); `public` group can't reach these modes at all.
- **[Risk]** Scraping is inherently SSRF-adjacent (arbitrary caller-supplied URLs fetched by the server) → **Mitigation**: same exposure `contrib.http:request` already has today; no new mitigation invented here, `public` access still exists (locked to `static`) as `http.yaml`'s `public` group does for plain requests.
- **[Trade-off]** No automated test can exercise real network/browser fetches in CI (the `scraping` extra isn't installed in the default dev/CI dependency group) → tests mock the lazily-imported fetcher classes; this verifies our merging/error-isolation logic but not Scrapling's actual fetch behavior. Accepted as a normal boundary for optional-dependency contrib tools (same boundary `sherlock_search` has).

## Migration Plan

Purely additive: new files, one new settings.yaml entry, one already-applied `pyproject.toml` change. No existing tool, schema, or endpoint is modified. Rollback is deleting the new files and settings.yaml line; no data migration involved.

## Open Questions

- Should a future iteration expose per-call concurrency or a `max_concurrency` param once there's real usage data suggesting the fixed cap of 5 is wrong in practice? Deferred — no evidence yet that it needs to be tunable.
