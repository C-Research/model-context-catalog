## Why

The MCC OSINT catalog currently has a handful of ad-hoc tools mixed into a single `search.yaml`. Dozens of high-value, freely accessible OSINT APIs (news, academic, government, infosec, crypto, company registries) can be wired up as `curl:` tools with zero new Python dependencies — they're pure REST calls that fit naturally into MCC's template-render-and-execute model.

## What Changes

- **New**: `osint/news.yaml` — Hacker News search (Algolia, free/open)
- **New**: `osint/academic.yaml` — arXiv, CrossRef, Semantic Scholar, OpenAlex (all free/open, no keys)
- **New**: `osint/gov.yaml` — SEC EDGAR full-text search, Congress.gov bill search, USASpending.gov awards (all free/open)
- **New**: `osint/infosec.yaml` — crt.sh certificate transparency, VirusTotal URL/IP/hash lookup, AbuseIPDB IP check, NVD CVE lookup, MalwareBazaar hash lookup, Wayback Machine availability (mix of open and key-required)
- **New**: `osint/companies.yaml` — OpenCorporates company search (free/open)
- **New**: `osint/crypto.yaml` — Blockchain.info raw tx/block/addr (moved), Blockchair multi-chain lookup
- **Refactor**: `osint/search.yaml` — remove curl: tools that move to dedicated files; keep only the Python `fn:` tools (`serpapi_search`, `gdelt`); move OFAC and ProPublica to `gov.yaml` and `companies.yaml` respectively; move blockchain tools to `crypto.yaml`
- **New**: two API keys added to `osint/osint.env` — `VIRUSTOTAL_API_KEY`, `ABUSEIPDB_API_KEY`
- All new files use file-level `env_file: osint.env` (per the `file-level-env-in-yaml` change)

## Capabilities

### New Capabilities
- `osint-news-tools`: curl-based news and discussion search tools (HN)
- `osint-academic-tools`: curl-based academic paper and citation lookup tools
- `osint-gov-tools`: curl-based government data and public records tools
- `osint-infosec-tools`: curl-based infrastructure, threat intel, and vulnerability tools
- `osint-companies-tools`: curl-based company registry and nonprofit lookup tools
- `osint-crypto-tools`: curl-based blockchain transaction and address tools

### Modified Capabilities
- None — `search.yaml` refactor is an implementation detail, not a spec-level behavior change

## Impact

- `osint/` directory: 6 new YAML files, `search.yaml` trimmed
- `osint/osint.env`: 2 new key placeholders added
- No changes to MCC core (`mcc/`)
- No new Python packages in `osint/pyproject.toml`
- Assumes `file-level-env-in-yaml` is implemented; if not, each `fn:` tool in the new files needs explicit `env_file: osint.env`
