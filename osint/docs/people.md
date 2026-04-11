---
icon: lucide/user
---

# People & Social

Tools for cross-platform username reconnaissance and social media footprint analysis.

---

### `sherlock_search`

Search 400+ social platforms and websites for accounts matching a username using the [Sherlock Project](https://github.com/sherlock-project/sherlock).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `username` | str | Yes | — | Username to search across social platforms. |

**Returns:** A dict mapping platform name to profile URL for each account found. Platforms where no account exists are omitted.  
**Auth:** None. Requires `sherlock-project` Python library (`pip install mcc[osint]`).

!!! note "Performance"
    Scans are network-bound and typically take 30–120 seconds, depending on platform response times and network conditions.

!!! tip "Covered platforms"
    Includes Twitter/X, Instagram, TikTok, Reddit, GitHub, GitLab, LinkedIn, YouTube, Twitch, Spotify, Steam, Pinterest, Snapchat, Telegram, and 380+ more. See the [full site list](https://github.com/sherlock-project/sherlock/blob/master/sherlock_project/resources/data.json).
