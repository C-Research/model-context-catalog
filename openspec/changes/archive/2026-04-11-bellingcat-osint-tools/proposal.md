## Why

The OSINT catalog covers academic, crypto, gov, infosec, and news sources but has no people-search or conflict-event tooling, and companies coverage is limited to US sources (OpenCorporates, EDGAR, ProPublica). Adding Bellingcat-recommended tools fills these gaps with high-signal, investigator-vetted sources.

## What Changes

- **New curl tools** added to `osint/companies.yaml`:
  - `companies_house_search` — UK official company registry (Companies House API, free + key)
  - `icij_offshore_search` — ICIJ Offshore Leaks database (Panama Papers, Pandora Papers, etc.)
  - `importyeti_search` — US customs import/export records
  - `opensanctions_search` — Sanctions, PEPs, and watchlist screening (OpenSanctions API)
- **New file** `osint/people.yaml` — curl stub + Python callable for username search via Sherlock
- **New file** `osint/conflict.yaml` — curl tools for UCDP and ReliefWeb + Python callable for GDELT via gdeltdoc
- **New file** `osint/osint.py` — typed Python callable stubs: `sherlock_search`, `gdelt_search`
- **New package extra** `mcc[osint]` in `pyproject.toml` with `sherlock-project` and `gdeltdoc`

## Capabilities

### New Capabilities

- `osint-people-tools`: Username and identity search across social platforms via Sherlock; exposes a single MCC callable backed by the `sherlock-project` Python package
- `osint-conflict-tools`: Conflict event querying via UCDP (curl) and GDELT (Python/gdeltdoc), plus humanitarian data via ReliefWeb (curl)

### Modified Capabilities

- `osint-companies-tools`: Extended with UK (Companies House), offshore leaks (ICIJ), trade data (ImportYeti), and sanctions screening (OpenSanctions)

## Impact

- `pyproject.toml`: new `[project.optional-dependencies]` osint extra
- `osint/osint.py`: new file, not imported by core MCC — only loaded when `mcc[osint]` is installed
- `osint/companies.yaml`: 4 new curl tools appended
- `osint/people.yaml`: new file, references Python callable
- `osint/conflict.yaml`: new file, mix of curl + Python callable
- No changes to core MCC auth, search, or transport layers
