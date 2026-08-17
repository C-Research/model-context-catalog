import asyncio

_VALID_MODES = ("static", "js", "stealth")
_MAX_CONCURRENCY = 5


async def scrape(
    urls: list[str],
    css: dict[str, str] | None = None,
    xpath: dict[str, str] | None = None,
    mode: str = "static",
    timeout: float = 30,
) -> dict[str, dict[str, list[str]] | str]:
    """
    Fetch one or more pages and extract named fields via CSS and/or XPath selectors.

    css/xpath map a field name to a selector; at least one is required. Both can
    be given in the same call and their extracted fields are merged per page.
    Selectors support Scrapy-style pseudo-selectors inline (e.g. "a::attr(href)",
    "h1::text") to target attributes or text directly.

    mode selects the fetcher: "static" (fast HTTP fetch, default), "js" (renders
    JavaScript via a headless browser), or "stealth" (headless browser with
    anti-bot-detection evasion, e.g. for Cloudflare-protected pages). "js" and
    "stealth" require Chromium to be installed (playwright install chromium).

    Returns a dict keyed by URL. Each value is either a dict of field name to
    matched strings, or an error string if that page failed to fetch.
    """
    try:
        from scrapling import AsyncFetcher, DynamicFetcher, StealthyFetcher
    except ImportError:
        raise ImportError("scrapling is not installed. Run: pip install model-context-catalog[scraping]")

    if not css and not xpath:
        raise ValueError("At least one of 'css' or 'xpath' is required")
    if mode not in _VALID_MODES:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {_VALID_MODES}")

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    if mode == "static":
        caller = AsyncFetcher.get
    elif mode == "js":
        caller = DynamicFetcher.async_fetch
    else:
        caller = StealthyFetcher.async_fetch

    async def fetch_one(url: str) -> tuple[str, dict[str, list[str]] | str]:
        async with semaphore:
            try:
                page = await caller(url, timeout=timeout)
            except Exception as exc:
                return url, f"{type(exc).__name__}: {exc}"
            fields: dict[str, list[str]] = {}
            for name, selector in (css or {}).items():
                fields[name] = page.css(selector).getall()
            for name, selector in (xpath or {}).items():
                fields[name] = page.xpath(selector).getall()
            return url, fields

    results = await asyncio.gather(*(fetch_one(url) for url in urls))
    return dict(results)
