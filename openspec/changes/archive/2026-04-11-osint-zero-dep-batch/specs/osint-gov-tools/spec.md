## ADDED Requirements

### Requirement: SEC EDGAR full-text search
The system SHALL provide an `edgar_search` tool in `osint/gov.yaml` (group: `gov`) that queries the SEC EDGAR full-text search API for filings. No API key required.

#### Scenario: Search filings by keyword
- **WHEN** `edgar_search` is called with `q="climate risk disclosure"`
- **THEN** the tool returns a JSON response from `https://efts.sec.gov/LATEST/search-index?q=...` with matching SEC filings

#### Scenario: Filter by form type
- **WHEN** `edgar_search` is called with `q="executive compensation"` and `form_type="DEF 14A"`
- **THEN** only proxy statement filings are returned

### Requirement: Congress.gov bill search
The system SHALL provide a `congress_search` tool in `osint/gov.yaml` (group: `gov`) that queries the Congress.gov API for bills and legislation. No API key required for open access.

#### Scenario: Search bills by keyword
- **WHEN** `congress_search` is called with `query="artificial intelligence"`
- **THEN** the tool returns a JSON response from `https://api.congress.gov/v3/bill` with matching bills including sponsor, status, and chamber

### Requirement: USASpending federal awards search
The system SHALL provide a `usaspending_search` tool in `osint/gov.yaml` (group: `gov`) that queries the USASpending.gov API for federal contracts and grants. No API key required.

#### Scenario: Search awards by keyword
- **WHEN** `usaspending_search` is called with `keyword="cybersecurity"` and `award_type="contracts"`
- **THEN** the tool returns a JSON response from `https://api.usaspending.gov/api/v2/search/spending_by_award/` with matching federal awards

### Requirement: OFAC sanctions search (moved from search.yaml)
The system SHALL provide an `ofac` tool in `osint/gov.yaml` (group: `gov`). This tool is moved from `osint/search.yaml` with no functional changes — it queries the OFAC SDN sanctions list search API.

#### Scenario: Search by name
- **WHEN** `ofac` is called with `name="some entity"`
- **THEN** the tool returns sanctions list matches from the OFAC API
