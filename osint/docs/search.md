---
icon: lucide/archive
---

# Web Archives

Tools for accessing historical snapshots of web content via the [Internet Archive](https://archive.org).

---

### `wayback`

Check whether a URL has been archived by the [Wayback Machine](https://web.archive.org) and retrieve the closest available snapshot.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `url` | str | Yes | — | The URL to look up in the Wayback Machine. |
| `timestamp` | str | No | _(latest)_ | Target timestamp in `YYYYMMDDhhmmss` format to find the closest snapshot. |

**Returns:** JSON with the closest available snapshot URL and its capture timestamp. Returns an empty `archived_snapshots` object if the URL has not been archived.  
**Auth:** None.

??? example "Usage examples"
    Check if a page exists in the archive:
    ```
    wayback(url="https://example.com/page")
    ```

    Find the closest snapshot to a specific date:
    ```
    wayback(url="https://example.com/page", timestamp="20200101000000")
    ```

!!! tip "Browsing archives directly"
    To browse all snapshots for a URL, visit `https://web.archive.org/web/*/URL` directly in a browser. The API only returns the single closest snapshot to the requested timestamp.
