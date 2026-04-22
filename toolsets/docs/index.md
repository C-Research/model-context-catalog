---
icon: lucide/package
---

# Contrib

MCC ships two optional toolsets: **utils** for general-purpose operations and **osint** for open-source intelligence research. Both are disabled by default and loaded via `MCC_SETTINGS_FILES`.

## Utils

General-purpose tools for HTTP, filesystem, shell, text processing, time, and archives.

```bash
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml
```

| Category | Groups | Description |
|----------|--------|-------------|
| [HTTP](utils/http.md) | `public.http`, `admin.http` | Make HTTP requests |
| [Filesystem](utils/fs.md) | `read`, `write` (under `admin.fs`) | Read, write, list, move files |
| [System](utils/system.md) | `admin.system` | Shell, Python, env vars, platform info |
| [Text](utils/text.md) | `public.text` | Encoding, hashing, diff, regex |
| [Time](utils/time.md) | `public.time` | Current time, formatting, date arithmetic |
| [Archive](utils/archive.md) | `admin.archive` | List, extract, create zip/tar archives |

## OSINT

Open-source intelligence tools for research, investigations, and threat analysis. Thin wrappers around public APIs — no scraping, no headless browsers.

```bash
MCC_SETTINGS_FILES=toolsets/osint/settings.yaml
```

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
| [People & Social](people.md) | 2 | Sherlock Project, PIPL |
| [News & Media](news.md) | 2 | Hacker News, Algolia |
| [Academic Research](academic.md) | 4 | arXiv, CrossRef, Semantic Scholar, OpenAlex |
| [Web Archives](search.md) | 1 | Internet Archive |

API keys go in `osint.env` alongside the tool files. Copy `osint.env.example` to get started.
