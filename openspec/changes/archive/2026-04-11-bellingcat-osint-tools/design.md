## Context

The OSINT catalog uses two tool delivery mechanisms: curl-based tools defined in YAML (simple HTTP calls via Jinja-templated URLs) and Python callables defined in `.py` files. The catalog already has companies, gov, academic, crypto, infosec, and news YAML files. There are no people or conflict files. `osint/osint.py` does not yet exist. The package has no optional dependency extras.

Sherlock (`sherlock-project`) and gdeltdoc are Python libraries with programmatic APIs — they cannot be expressed as curl tools and require Python callables. All other new tools (Companies House, ICIJ, ImportYeti, OpenSanctions, UCDP, ReliefWeb) are plain HTTP APIs suitable for curl YAML.

## Goals / Non-Goals

**Goals:**
- Add 4 new curl tools to `companies.yaml` covering UK, offshore, trade, and sanctions data
- Create `people.yaml` with a Sherlock-backed callable for username search
- Create `conflict.yaml` with curl tools for UCDP/ReliefWeb and a gdeltdoc-backed callable
- Create `osint/osint.py` with typed stub callables (`sherlock_search`, `gdelt_search`)
- Add `mcc[osint]` optional dependency extra for `sherlock-project` and `gdeltdoc`

**Non-Goals:**
- Full Sherlock/GDELT result processing or normalization
- Authentication/key management for Companies House or OpenSanctions (env vars in `osint.env`)
- ACLED integration (access not available)
- Username tools beyond Sherlock (Maigret, Blackbird excluded for now)

## Decisions

**Sherlock as sole username backend**
Sherlock (`sherlock-project`) is chosen over Maigret (3000+ sites, heavier runtime) and Blackbird (newer, smaller community). Sherlock's 400-site curated list has the best signal-to-noise ratio per lookup time.

**Stubs, not full implementations**
`osint/osint.py` provides typed function signatures with docstrings and `raise NotImplementedError`. This establishes the MCC callable contract and import surface without shipping incomplete logic. Full implementation is a follow-on.

**gdeltdoc over raw GDELT API**
The GDELT 2.0 API returns raw CSV with complex query syntax. `gdeltdoc` wraps it in a clean Python API returning DataFrames. Accepted as a dep since it's isolated behind the `[osint]` extra.

**gdeltdoc DataFrame serialization**
gdeltdoc returns `pandas.DataFrame`. Raw DataFrames are not JSON-serializable and contain pandas-specific types (`Timestamp`, `NaN`, `int64`, etc.) that break standard `json.dumps`. `gdelt_search` SHALL convert the DataFrame before returning using this pipeline:
1. `df.where(pd.notnull(df), None)` — replace `NaN`/`NaT` with `None` (serializes to JSON `null`)
2. `df.to_dict(orient="records")` — row-per-record list of plain dicts
3. Cast any remaining non-serializable types: `Timestamp` → ISO-8601 string via `.isoformat()`, numpy scalars → native Python via `.item()`

Return type is `list[dict]`. Column names come from gdeltdoc directly (e.g. `url`, `title`, `seendate`, `socialimage`, `domain`, `language`, `sourcecountry`, `tone`). No renaming — LLMs handle descriptive column names well and renaming would diverge from gdeltdoc docs.

**Optional extra, not core dep**
`sherlock-project` and `gdeltdoc` are heavy (network-scanning + pandas). Putting them in `[project.optional-dependencies]` keeps the core MCC install lightweight. Users who don't load osint tools don't pay the cost.

**New files for new categories**
`people.yaml` and `conflict.yaml` follow the existing per-category file convention. No new groups are added to the core settings — osint tools load via `settings.local.yaml` tool list.

## Risks / Trade-offs

[Sherlock runtime] Scanning 400+ sites per call can take 30–120s depending on network. Mitigation: document expected latency; consider a `timeout` parameter in the stub.

[Companies House API key] Requires registration at developer.company-information.service.gov.uk. Mitigation: add `COMPANIES_HOUSE_API_KEY` to `osint.env.example` with instructions.

[OpenSanctions rate limits] Free tier is rate-limited. Mitigation: document in tool description; `osint.env` holds key.

[gdeltdoc pandas dep] Pulls in pandas/numpy transitively. Mitigation: confined to `[osint]` extra, not installed by default.

## Open Questions

- Should `sherlock_search` run async (using Sherlock's internal aiohttp) or sync? Async preferred for MCC's async execution model but needs testing.
- Should `gdelt_search` cast numpy scalar columns (e.g. `tone` as `float64`) inline or in a generic post-processing helper shared with any future DataFrame-returning callables?
