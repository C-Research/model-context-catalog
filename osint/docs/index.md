---
icon: lucide/telescope
---

# OSINT Tool Catalog

A collection of open-source intelligence tools for research, investigations, and threat analysis. Each tool is a thin wrapper around a public API or CLI — no scraping, no headless browsers.

## Categories

| Category | Tools | Services |
|----------|------:|---------|
| [Infosec & Network](infosec.md) | 10 | crt.sh, VirusTotal, AbuseIPDB, NIST NVD, MalwareBazaar, DNSDumpster, urlscan.io, ip-api.com, nmap |
| [Companies & Business](companies.md) | 6 | OpenCorporates, ProPublica, Companies House, ICIJ Offshore Leaks, ImportYeti, OpenSanctions |
| [Government & Records](gov.md) | 6 | SEC EDGAR, Congress.gov, USASpending.gov, OpenSecrets, OFAC |
| [Geolocation](geo.md) | 3 | Nominatim, Overpass API (OpenStreetMap) |
| [Transport & Aviation](transport.md) | 2 | OpenSky Network |
| [Environment & Maritime](environment.md) | 2 | NASA FIRMS, Global Fishing Watch |
| [Conflict & Humanitarian](conflict.md) | 3 | UCDP, ReliefWeb, GDELT |
| [Cryptocurrency](crypto.md) | 4 | Blockchain.info, Blockchair |
| [People & Social](people.md) | 1 | Sherlock Project |
| [News & Media](news.md) | 2 | Hacker News, Algolia |
| [Academic Research](academic.md) | 4 | arXiv, CrossRef, Semantic Scholar, OpenAlex |
| [Web Archives](search.md) | 1 | Internet Archive |

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
