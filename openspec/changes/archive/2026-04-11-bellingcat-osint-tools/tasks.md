## 1. Package Setup

- [x] 1.1 Add `[project.optional-dependencies]` osint extra to `pyproject.toml` with `sherlock-project` and `gdeltdoc`
- [x] 1.2 Add `COMPANIES_HOUSE_API_KEY` and `OPENSANCTIONS_API_KEY` to `osint/osint.env.example`

## 2. Python Callables

- [x] 2.1 Create `osint/osint.py` with typed stub `sherlock_search(username: str) -> dict` — raises `NotImplementedError`, guarded by `ImportError` if `sherlock-project` not installed
- [x] 2.2 Add typed stub `gdelt_search(query: str, start_date: str, end_date: str) -> list[dict]` to `osint/osint.py` — raises `NotImplementedError`, guarded by `ImportError` if `gdeltdoc` not installed

## 3. Companies YAML

- [x] 3.1 Add `companies_house_search` curl tool to `osint/companies.yaml` using Companies House API with Basic auth from `COMPANIES_HOUSE_API_KEY`
- [x] 3.2 Add `icij_offshore_search` curl tool to `osint/companies.yaml` using ICIJ Offshore Leaks API (no key)
- [x] 3.3 Add `importyeti_search` curl tool to `osint/companies.yaml` using ImportYeti search endpoint (no key)
- [x] 3.4 Add `opensanctions_search` curl tool to `osint/companies.yaml` using OpenSanctions API with `OPENSANCTIONS_API_KEY` header

## 4. People YAML

- [x] 4.1 Create `osint/people.yaml` with group `people`, `env_file: osint.env`, and a `sherlock_search` tool entry pointing at the `osint.osint:sherlock_search` Python callable

## 5. Conflict YAML

- [x] 5.1 Create `osint/conflict.yaml` with group `conflict` and `ucdp_search` curl tool (UCDP GED API, no key, params: `country`, `year_from`, `year_to`)
- [x] 5.2 Add `reliefweb_search` curl tool to `osint/conflict.yaml` (ReliefWeb API, no key, params: `q`, `content_type`)
- [x] 5.3 Add `gdelt_search` tool entry to `osint/conflict.yaml` pointing at the `osint.osint:gdelt_search` Python callable

## 6. Verify

- [x] 6.1 Add `people.yaml` and `conflict.yaml` to `osint/settings.local.yaml` tool list
- [x] 6.2 Smoke-test curl tools with `uv run mcc tool list` and confirm all 9 new tools appear
- [x] 6.3 Confirm `pip install mcc[osint]` resolves without conflicts
