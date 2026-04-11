## ADDED Requirements

### Requirement: OpenCorporates company search
The system SHALL provide an `opencorporates_search` tool in `osint/companies.yaml` (group: `companies`) that searches the OpenCorporates database for company registrations by name. No API key required for basic search.

#### Scenario: Search by company name
- **WHEN** `opencorporates_search` is called with `q="Acme Corp"`
- **THEN** the tool returns a JSON response from `https://api.opencorporates.com/v0.4/companies/search?q=Acme+Corp` with matching companies including jurisdiction, registration number, and status

#### Scenario: Filter by jurisdiction
- **WHEN** `opencorporates_search` is called with `q="Acme"` and `jurisdiction_code="us_de"`
- **THEN** only companies registered in Delaware are returned

### Requirement: ProPublica nonprofit search (moved from search.yaml)
The system SHALL provide a `propublica_nonprofit` tool in `osint/companies.yaml` (group: `companies`). This tool is moved from `osint/search.yaml` with no functional changes — it searches ProPublica's Nonprofit Explorer for IRS 990 filings.

#### Scenario: Search nonprofits by name or keyword
- **WHEN** `propublica_nonprofit` is called with `q="Red Cross"`
- **THEN** the tool returns matching nonprofit organizations with financial data from ProPublica's API
