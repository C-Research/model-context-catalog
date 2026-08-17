## ADDED Requirements

### Requirement: scrape callable
The system SHALL provide an async `scrape` Python callable in `toolsets/contrib/scraping.py` with signature `scrape(urls: list[str], css: dict[str, str] | None = None, xpath: dict[str, str] | None = None, mode: str = "static", timeout: float = 30) -> dict[str, dict[str, list[str]] | str]`, using the `scrapling` library to fetch each URL and extract named fields via CSS and/or XPath selectors. It SHALL be referenced by `toolsets/contrib/scraping.yaml`.

#### Scenario: Single page, CSS fields
- **WHEN** `scrape` is called with `urls=["https://example.com"]` and `css={"title": "h1::text"}`
- **THEN** the callable returns `{"https://example.com": {"title": ["Example Domain"]}}` (or the page's actual `h1` text)

#### Scenario: CSS and XPath combined
- **WHEN** `scrape` is called with both `css={"title": "h1::text"}` and `xpath={"links": "//a/@href"}` for the same URL
- **THEN** the returned fields dict for that URL contains both the `title` and `links` keys, each with the matches from their respective selector language

#### Scenario: Neither selector given
- **WHEN** `scrape` is called with `css=None` and `xpath=None` (or both empty)
- **THEN** the callable raises `ValueError` indicating at least one of `css` or `xpath` is required

### Requirement: Multi-page concurrent fetch with per-URL failure isolation
The system SHALL fetch all URLs in a `scrape` call concurrently (bounded by a fixed internal concurrency cap, not a caller-controlled parameter) and SHALL isolate per-URL failures so that one failing URL does not prevent results from being returned for the others.

#### Scenario: One URL fails, others succeed
- **WHEN** `scrape` is called with multiple `urls` and one URL raises during fetch (timeout, connection error, etc.)
- **THEN** the returned dict has an entry for every URL; the failing URL's value is a string describing the error, and every other URL's value is its normal fields dict

#### Scenario: All URLs succeed
- **WHEN** `scrape` is called with multiple `urls` that all fetch successfully
- **THEN** every URL's value in the returned dict is a fields dict (not an error string)

### Requirement: Selectable fetch mode
The system SHALL support a `mode` parameter with exactly three valid values — `"static"` (default), `"js"`, and `"stealth"` — selecting Scrapling's `AsyncFetcher`, `DynamicFetcher`, and `StealthyFetcher` respectively. An invalid `mode` value SHALL raise `ValueError`.

#### Scenario: Default static fetch
- **WHEN** `scrape` is called without specifying `mode`
- **THEN** pages are fetched via Scrapling's `AsyncFetcher` (no headless browser involved)

#### Scenario: JS rendering mode
- **WHEN** `scrape` is called with `mode="js"`
- **THEN** pages are fetched via Scrapling's `DynamicFetcher`, rendering JavaScript before selectors are applied

#### Scenario: Stealth mode
- **WHEN** `scrape` is called with `mode="stealth"`
- **THEN** pages are fetched via Scrapling's `StealthyFetcher`, using its anti-bot-detection evasion

#### Scenario: Invalid mode
- **WHEN** `scrape` is called with `mode="not-a-real-mode"`
- **THEN** the callable raises `ValueError` naming the invalid value and the three valid options

### Requirement: Missing optional dependency
The system SHALL raise `ImportError` with a message directing the user to `pip install mcc[scraping]` when `scrape` is called but `scrapling` is not installed, and SHALL NOT import `scrapling` at module level (so that `toolsets/contrib/scraping.py` remains importable, and the rest of the contrib toolset loadable, without the `scraping` extra installed).

#### Scenario: scrapling not installed
- **WHEN** `scrape` is called but `scrapling` is not installed
- **THEN** the callable raises `ImportError` with a message directing the user to `pip install mcc[scraping]`

#### Scenario: Module import without scrapling installed
- **WHEN** `toolsets/contrib/scraping.py` is imported (e.g. during tool introspection) without `scrapling` installed
- **THEN** the import succeeds without error

### Requirement: admin/public group split
The system SHALL register two tool entries in `toolsets/contrib/scraping.yaml` against the `scrape` callable: one in groups `[admin, scraping]` with unrestricted access to all three `mode` values, and one in groups `[public, scraping]` with `mode` forced to `"static"` via the tool definition's `override` mechanism, so callers in the `public` group cannot select `js` or `stealth` mode.

#### Scenario: Admin can use any mode
- **WHEN** a user in the `admin` group calls the `admin`-group `scrape` tool entry with `mode="stealth"`
- **THEN** the call proceeds using `StealthyFetcher`

#### Scenario: Public is locked to static mode
- **WHEN** a user in the `public` group calls the `public`-group `scrape` tool entry, even if they pass `mode="js"`
- **THEN** the overridden `mode` value (`"static"`) is used instead, regardless of caller input

### Requirement: scraping package extra
The system SHALL declare a `scraping` optional dependency group in `pyproject.toml` containing `scrapling[fetchers]`, so users can install web-scraping support with `pip install mcc[scraping]`.

#### Scenario: Install scraping extra
- **WHEN** a user runs `pip install mcc[scraping]`
- **THEN** `scrapling` and its `fetchers` extra (`curl_cffi`, `playwright`, `patchright`, etc.) are installed as dependencies

#### Scenario: Contrib toolset loads without scraping extra
- **WHEN** `toolsets/contrib/settings.yaml` is loaded (contrib tools enabled) but `mcc[scraping]` is not installed
- **THEN** every other contrib tool still loads and registers successfully; only calling `scrape` itself fails, with the `ImportError` described above
