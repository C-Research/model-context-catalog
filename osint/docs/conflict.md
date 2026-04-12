---
icon: lucide/alert-triangle
---

# Conflict & Humanitarian

Tools for conflict data, humanitarian reporting, and global news event analysis. Covers political violence events from 1989 to present, UN/NGO situation reports, and georeferenced news.

---

### `ucdp_search`

Search the [Uppsala Conflict Data Program (UCDP)](https://ucdp.uu.se) Georeferenced Event Dataset (GED) for political violence events worldwide. Covers state-based conflict, non-state conflict, and one-sided violence.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `country` | str | Yes | — | Country name (e.g. `Ukraine`, `Sudan`, `Myanmar`). |
| `year_from` | int | No | _(none)_ | Start year filter, inclusive. Leave `0` for no lower bound. |
| `year_to` | int | No | _(none)_ | End year filter, inclusive. Leave `0` for no upper bound. |
| `pagesize` | int | No | `50` | Results per page (max 1000). |

**Returns:** JSON with conflict events — date, latitude/longitude, actor names, fatality estimates (best/low/high), and conflict type.  
**Auth:** None. Covers 1989 to present.

??? example "Usage examples"
    Get all recorded conflict events in Ukraine since 2022:
    ```
    ucdp_search(country="Ukraine", year_from=2022)
    ```

    Get conflict events in Sudan for a specific year range:
    ```
    ucdp_search(country="Sudan", year_from=2023, year_to=2024)
    ```

---

### `reliefweb_search`

Search [ReliefWeb](https://reliefweb.int) for humanitarian reports, situation reports, maps, and crisis news from UN agencies, NGOs, and governments.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Keyword or phrase (e.g. `Sudan famine`, `earthquake response`). |
| `content_type` | str | No | _(all)_ | Filter by type: `report`, `news`, `map`, `infographic`, `assessment`. |
| `limit` | int | No | `20` | Maximum results (max 1000). |

**Returns:** JSON with title, publication date, source organization, URL, and primary country.  
**Auth:** None.

??? example "Usage examples"
    Search for humanitarian reports on a crisis:
    ```
    reliefweb_search(q="Gaza humanitarian")
    ```

    Find situation reports only:
    ```
    reliefweb_search(q="Sudan famine", content_type="report")
    ```

---

### `gdelt_search`

Search the [GDELT Project](https://www.gdeltproject.org) 2.0 event database for news articles covering a topic across global media. GDELT monitors broadcast, print, and web news in over 100 languages.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Keyword or phrase to search across global news. |
| `start_date` | str | Yes | — | Start date in `YYYY-MM-DD` format. |
| `end_date` | str | Yes | — | End date in `YYYY-MM-DD` format. |

**Returns:** List of article records with `url`, `title`, `seendate`, `domain`, `language`, `sourcecountry`, `tone`, and `socialimage`.  
**Auth:** None. Requires `gdeltdoc` Python library (`pip install mcc[osint]`).

??? example "Usage examples"
    Search global news coverage of a topic over a year:
    ```
    gdelt_search(query="Wagner Group Africa", start_date="2023-01-01", end_date="2023-12-31")
    ```

    Search coverage of a specific incident:
    ```
    gdelt_search(query="Zaporizhzhia nuclear", start_date="2022-03-01", end_date="2022-04-01")
    ```
