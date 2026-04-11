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
        import sherlock_project  # noqa: F401
    except ImportError:
        raise ImportError(
            "sherlock-project is not installed. Run: pip install mcc[osint]"
        )
    raise NotImplementedError


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
        import gdeltdoc  # noqa: F401
        import pandas as pd  # noqa: F401
    except ImportError:
        raise ImportError(
            "gdeltdoc is not installed. Run: pip install mcc[osint]"
        )
    raise NotImplementedError
