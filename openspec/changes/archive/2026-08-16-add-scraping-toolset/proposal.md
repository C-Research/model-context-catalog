## Why

MCC has no way to pull structured data out of a web page — `contrib.http:request` returns raw HTML/JSON but leaves selector-based extraction to the caller. LLM clients doing OSINT or research workflows need a tool that fetches one or more pages and returns just the fields they asked for, via CSS or XPath selectors, without hand-rolling HTML parsing in a shell/exec tool.

## What Changes

- New `toolsets/contrib/scraping.py` module with a single async function `scrape(urls, css, xpath, mode, timeout)` that fetches multiple pages concurrently and extracts named fields per page via CSS and/or XPath selectors, using the `scrapling` library.
- Three fetch tiers exposed via a `mode` param: `static` (default, fast HTTP fetch), `js` (headless-browser JS rendering), `stealth` (headless browser with anti-bot evasion for protected sites).
- Per-URL failure isolation: one bad URL in a batch returns an error string for that URL instead of failing the whole call.
- New `toolsets/contrib/scraping.yaml` registering two tool entries against the same function: an `admin, scraping` entry with full access to all three modes, and a `public, scraping` entry that forces `mode=static` (locking untrusted callers out of headless-browser spin-up).
- `toolsets/contrib/settings.yaml` updated to load the new YAML file.
- New optional dependency group: `scrapling[fetchers]` under `[project.optional-dependencies].scraping` in `pyproject.toml` (already added via `uv add`).
- `scrapling` is imported lazily inside the function body (not at module level) so servers that load the contrib toolset without the `scraping` extra installed don't fail to load the *other* contrib tools.

## Capabilities

### New Capabilities
- `web-scraping-tools`: fetching one or more web pages (optionally with JS rendering or stealth mode) and extracting named fields via CSS/XPath selectors, exposed as MCC contrib tools.

### Modified Capabilities
(none — this only adds new tool definitions, no changes to catalog-loader, tool-groups, or other existing spec behavior)

## Impact

- **New files**: `toolsets/contrib/scraping.py`, `toolsets/contrib/scraping.yaml`, `toolsets/contrib/tests/test_scraping.py`.
- **Modified files**: `toolsets/contrib/settings.yaml` (register new yaml), `pyproject.toml` (already modified — `scraping` extra).
- **Dependencies**: adds `scrapling[fetchers]` (pulls in `curl_cffi`, `playwright`, `patchright`) as an optional extra; `js`/`stealth` modes additionally require `playwright install chromium` on the host, which is a deployment step, not something this change automates.
- **Security/resource surface**: `js`/`stealth` modes spin up headless browser processes — gated to `admin` group only via the YAML `override` mechanism; `public` group is locked to `static`.
- **Testing**: `scrapling` is not in the default dev dependency group, and CI (`uv run pytest`) doesn't install the `scraping` extra, so tests must mock the lazily-imported fetcher classes rather than depend on `scrapling` being installed or hitting real network.
