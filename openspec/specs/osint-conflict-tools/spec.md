## Requirements

### Requirement: UCDP conflict event search
The system SHALL provide a `ucdp_search` curl tool in `osint/conflict.yaml` (group: `conflict`) that queries the Uppsala Conflict Data Program API for georeferenced conflict events. No API key required.

#### Scenario: Search by country
- **WHEN** `ucdp_search` is called with `country="Ukraine"`
- **THEN** the tool returns conflict events from the UCDP GED API for the specified country including date, actor names, fatalities, and coordinates

#### Scenario: Search by year range
- **WHEN** `ucdp_search` is called with `year_from=2022` and `year_to=2024`
- **THEN** only events within that date range are returned

### Requirement: ReliefWeb humanitarian data search
The system SHALL provide a `reliefweb_search` curl tool in `osint/conflict.yaml` (group: `conflict`) that queries the ReliefWeb API for humanitarian reports, news, and crisis data. No API key required.

#### Scenario: Search by keyword
- **WHEN** `reliefweb_search` is called with `q="Sudan famine"`
- **THEN** the tool returns matching humanitarian reports and situation reports from ReliefWeb including title, date, source, and URL

#### Scenario: Filter by content type
- **WHEN** `reliefweb_search` is called with `q="earthquake"` and `content_type="report"`
- **THEN** only report-type documents are returned

### Requirement: GDELT conflict event query callable
The system SHALL provide a `gdelt_search` Python callable in `osint/osint.py` that queries the GDELT 2.0 dataset for conflict-related events using the `gdeltdoc` library. The callable SHALL be referenced by `osint/conflict.yaml` (group: `conflict`).

#### Scenario: Search by keyword and date range
- **WHEN** `gdelt_search` is called with `query="military strike"`, `start_date="2024-01-01"`, and `end_date="2024-03-31"`
- **THEN** the callable returns a `list[dict]` of matching event records where every value is a JSON-native Python type (str, int, float, bool, or None) — no pandas `Timestamp`, `NaN`, or numpy scalar types. Date fields SHALL be ISO-8601 strings.

#### Scenario: Empty result set
- **WHEN** `gdelt_search` returns no matching articles
- **THEN** the callable returns an empty list `[]`, not an empty DataFrame or None

#### Scenario: Missing optional dep
- **WHEN** `gdelt_search` is called but `gdeltdoc` is not installed
- **THEN** the callable raises `ImportError` with a message directing the user to `pip install mcc[osint]`
