## 1. Setup

- [x] 1.1 Add `VIRUSTOTAL_API_KEY=` and `ABUSEIPDB_API_KEY=` placeholder lines to `osint/osint.env`
- [x] 1.2 Create `osint/osint.env.example` with all key placeholders (committed, no real values)

## 2. news.yaml

- [x] 2.1 Create `osint/news.yaml` with `env_file: osint.env` and `groups: [news]`
- [x] 2.2 Add `hn_search` tool — Algolia HN search with `q` and optional `tags` params
- [x] 2.3 Add `hn_item` tool — Firebase HN item lookup with `item_id` param

## 3. academic.yaml

- [x] 3.1 Create `osint/academic.yaml` with `env_file: osint.env` and `groups: [academic]`
- [x] 3.2 Add `arxiv_search` tool — arXiv API with `query` and `max_results` params
- [x] 3.3 Add `crossref_search` tool — CrossRef works API with `query` param
- [x] 3.4 Add `semantic_scholar_search` tool — Semantic Scholar paper search with `query` param
- [x] 3.5 Add `openalex_search` tool — OpenAlex works API with `query` param

## 4. gov.yaml

- [x] 4.1 Create `osint/gov.yaml` with `env_file: osint.env` and `groups: [gov]`
- [x] 4.2 Add `edgar_search` tool — SEC EDGAR full-text search with `q` and optional `form_type` params
- [x] 4.3 Add `congress_search` tool — Congress.gov bill search with `query` param
- [x] 4.4 Add `usaspending_search` tool — USASpending awards search with `keyword` and `award_type` params
- [x] 4.5 Move `ofac` tool from `search.yaml` into `gov.yaml` (no functional changes)

## 5. infosec.yaml

- [x] 5.1 Create `osint/infosec.yaml` with `env_file: osint.env` and `groups: [infosec]`
- [x] 5.2 Add `crtsh` tool — crt.sh cert transparency search with `domain` param
- [x] 5.3 Add `virustotal` tool — VT API v3 with `indicator` and `type` params; `override: ${VIRUSTOTAL_API_KEY}` header
- [x] 5.4 Add `abuseipdb` tool — AbuseIPDB check with `ip` param; `override: ${ABUSEIPDB_API_KEY}` header
- [x] 5.5 Add `nvd_cve` tool — NIST NVD CVE lookup with `cve_id` param
- [x] 5.6 Add `malwarebazaar` tool — MalwareBazaar hash lookup with `hash` param (POST)
- [x] 5.7 Add `wayback` tool — Wayback Machine availability check with `url` param

## 6. companies.yaml

- [x] 6.1 Create `osint/companies.yaml` with `env_file: osint.env` and `groups: [companies]`
- [x] 6.2 Add `opencorporates_search` tool — company search with `q` and optional `jurisdiction_code` params
- [x] 6.3 Move `propublica_nonprofit` tool from `search.yaml` into `companies.yaml` (no functional changes)

## 7. crypto.yaml

- [x] 7.1 Create `osint/crypto.yaml` with `env_file: osint.env` and `groups: [crypto]`
- [x] 7.2 Move `blockchain_rawtx`, `blockchain_rawblock`, `blockchain_rawaddr` from `search.yaml` (no functional changes)
- [x] 7.3 Add `blockchair` tool — multi-chain lookup with `chain` and `query` params

## 8. Refactor search.yaml

- [x] 8.1 Remove `ofac`, `propublica_nonprofit`, and all three `blockchain_*` tools from `search.yaml`
- [x] 8.2 Remove `dnsdumpster` from `search.yaml` — moved to a future `dns.yaml` or leave in place if desired (kept in search.yaml with infosec group, pending dns.yaml)
- [x] 8.3 Verify `search.yaml` contains only `serpapi_search`, `gdelt`, and `dnsdumpster` after cleanup
