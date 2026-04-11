---
icon: lucide/telescope
---

# OSINT Tool Catalog

A collection of open-source intelligence tools for research, investigations, and threat analysis. Each tool is a thin wrapper around a public API or CLI — no scraping, no headless browsers.

## Categories

| Category | Tools | Auth |
|----------|------:|------|
| [Infosec & Network](infosec.md) | 10 | VirusTotal, AbuseIPDB, DNSDumpster, urlscan |
| [Companies & Business](companies.md) | 6 | Companies House, OpenSanctions |
| [Government & Records](gov.md) | 6 | OpenSecrets |
| [Geolocation](geo.md) | 3 | None |
| [Transport & Aviation](transport.md) | 2 | None |
| [Environment & Maritime](environment.md) | 2 | NASA FIRMS, Global Fishing Watch |
| [Conflict & Humanitarian](conflict.md) | 3 | None |
| [Cryptocurrency](crypto.md) | 4 | None |
| [People & Social](people.md) | 1 | None |
| [News & Media](news.md) | 2 | None |
| [Academic Research](academic.md) | 4 | None |
| [Web Archives](search.md) | 1 | None |

## Setup

API keys go in `osint.env` alongside the tool files. Copy `osint.env.example` to get started.

```env
VIRUSTOTAL_API_KEY=
ABUSEIPDB_API_KEY=
DNSDUMPSTER_API_KEY=
URLSCAN_API_KEY=
COMPANIES_HOUSE_API_KEY=
OPENSANCTIONS_API_KEY=
NASA_FIRMS_API_KEY=
GFW_API_KEY=
OPENSECRETS_API_KEY=
```

Most tools work without any API keys. All keys that are required have free tiers.
