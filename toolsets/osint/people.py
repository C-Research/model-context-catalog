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
