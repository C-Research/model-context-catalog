---
icon: lucide/user
---

# People & Social

Tools for cross-platform username reconnaissance, social media footprint analysis, and people search.

| Tool | Description |
|------|-------------|
| [`sherlock_search`](#sherlock_search) | Search 400+ social platforms for accounts matching a username. |
| [`pipl_search`](#pipl_search) | Search the PIPL people search API by name, email, phone, username, or address. |

---

### `sherlock_search`

Search 400+ social platforms and websites for accounts matching a username using the [Sherlock Project](https://github.com/sherlock-project/sherlock).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `username` | str | Yes | — | Username to search across social platforms. |

**Returns:** A dict mapping platform name to profile URL for each account found. Platforms where no account exists are omitted.  
**Auth:** None. Requires `sherlock-project` Python library (`pip install mcc[osint]`).

??? example "Usage examples"
    Search for accounts matching a username across 400+ platforms:
    ```
    sherlock_search(username="johndoe")
    ```

    Investigate a handle seen on one platform:
    ```
    sherlock_search(username="target_handle")
    ```

!!! note "Performance"
    Scans are network-bound and typically take 30–120 seconds, depending on platform response times and network conditions.

!!! tip "Covered platforms"
    Includes Twitter/X, Instagram, TikTok, Reddit, GitHub, GitLab, LinkedIn, YouTube, Twitch, Spotify, Steam, Pinterest, Snapchat, Telegram, and 380+ more. See the [full site list](https://github.com/sherlock-project/sherlock/blob/master/sherlock_project/resources/data.json).

---

### `pipl_search`

Search the [PIPL people search API](https://pipl.com/) by any combination of name, email, phone, username, user ID, URL, or address. At least one identifying field is required.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `first_name` | str | | — | First name. |
| `middle_name` | str | | — | Middle name. |
| `last_name` | str | | — | Last name. |
| `raw_name` | str | | — | Full name as a single string (alternative to first/middle/last). |
| `email` | str | | — | Email address. |
| `phone` | str | | — | Phone number. |
| `username` | str | | — | Username or handle. |
| `user_id` | str | | — | User ID on a social platform. |
| `url` | str | | — | Profile or website URL. |
| `age` | str | | — | Age or age range (e.g. `"30"` or `"25-35"`). |
| `house` | str | | — | House number. |
| `street` | str | | — | Street name. |
| `city` | str | | — | City. |
| `state` | str | | — | State (2-letter code recommended). |
| `zipcode` | str | | — | ZIP or postal code. |
| `country` | str | | — | Country code (e.g. `"US"`). |
| `raw_address` | str | | — | Full address as a single string. |
| `minimum_probability` | str | | `"0.9"` | 0–1. Minimum probability for inferred data. |
| `minimum_match` | str | | `"0"` | 0–1. Minimum match score for possible persons. |
| `show_sources` | str | | `"false"` | `all`, `matching`/`true`, or `false`. |
| `live_feeds` | str | | `"true"` | Whether to use live data sources. |
| `top_match` | str | | `"false"` | Return only the single best high-probability match. |
| `hide_sponsored` | str | | `"false"` | Omit results marked as sponsored. |
| `match_requirements` | str | | — | Condition specifying fields that must be returned; empty responses won't be charged. |
| `source_category_requirements` | str | | — | Condition specifying source categories that must be returned; empty responses won't be charged. |

**Returns:** PIPL API JSON response containing matched person records with aggregated data from public sources.  
**Auth:** Requires `PIPL_API_KEY` in `osint.env`.

??? example "Usage examples"
    Search by email:
    ```
    pipl_search(email="clark.kent@example.com")
    ```

    Search by name and location:
    ```
    pipl_search(first_name="Clark", last_name="Kent", city="Metropolis", state="NY")
    ```

    Return only the top match:
    ```
    pipl_search(username="ckent", top_match="true")
    ```
