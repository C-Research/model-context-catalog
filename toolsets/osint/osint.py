"""
Python callables for OSINT tools that require library dependencies.

Install deps with: pip install mcc[osint]
"""


def sherlock_search(username: str) -> dict:
    """
    Search 400+ social platforms and websites for accounts matching a username.

    Returns a dict mapping platform name to profile URL for each found account.
    Unregistered or unavailable platforms are omitted from the result.

    Note: scans are network-bound and typically take 30–120 seconds.
    """
    try:
        from sherlock_project.notify import QueryNotify
        from sherlock_project.result import QueryStatus
        from sherlock_project.sherlock import sherlock
        from sherlock_project.sites import SitesInformation
    except ImportError:
        raise ImportError(
            "sherlock-project is not installed. Run: pip install mcc[osint]"
        )

    class _SilentNotify(QueryNotify):
        def start(self, message=None):
            pass

        def update(self, message=None):
            pass

        def finish(self, message=None):
            pass

    sites_info = SitesInformation()
    site_data = {site.name: site.information for site in sites_info}

    results = sherlock(
        username=username,
        site_data=site_data,
        query_notify=_SilentNotify(),
        timeout=60,
    )

    return {
        site: info["url_user"]
        for site, info in results.items()
        if info["status"].status == QueryStatus.CLAIMED
    }


def gdelt_search(query: str, start_date: str, end_date: str) -> list[dict]:
    """
    Search the GDELT 2.0 event database for news articles matching a query.

    Returns a list of article records. All values are JSON-native Python types
    (str, int, float, bool, or None). Date fields are ISO-8601 strings.
    Fields include: url, title, seendate, domain, language, sourcecountry,
    tone, socialimage.

    start_date and end_date must be in YYYY-MM-DD format (e.g. "2024-01-15").
    """
    try:
        from gdeltdoc import Filters, GdeltDoc
    except ImportError:
        raise ImportError(
            "gdeltdoc is not installed. Run: pip install mcc[osint]"
        )

    filters = Filters(
        keyword=query,
        start_date=start_date,
        end_date=end_date,
    )

    df = GdeltDoc().article_search(filters)

    if df.empty:
        return []

    fields = ["url", "title", "seendate", "domain", "language", "sourcecountry", "tone", "socialimage"]
    available = [f for f in fields if f in df.columns]
    return df[available].where(df[available].notna(), other=None).to_dict("records")
