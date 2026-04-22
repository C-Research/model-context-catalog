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
        raise ImportError("gdeltdoc is not installed. Run: pip install mcc[osint]")

    filters = Filters(
        keyword=query,
        start_date=start_date,
        end_date=end_date,
    )

    df = GdeltDoc().article_search(filters)

    if df.empty:
        return []

    fields = [
        "url",
        "title",
        "seendate",
        "domain",
        "language",
        "sourcecountry",
        "tone",
        "socialimage",
    ]
    available = [f for f in fields if f in df.columns]
    return df[available].where(df[available].notna(), other=None).to_dict("records")
