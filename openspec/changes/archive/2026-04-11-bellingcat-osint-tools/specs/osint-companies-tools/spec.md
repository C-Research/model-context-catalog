## ADDED Requirements

### Requirement: Companies House UK company search
The system SHALL provide a `companies_house_search` curl tool in `osint/companies.yaml` (group: `companies`) that searches the UK Companies House official register. Requires a `COMPANIES_HOUSE_API_KEY` environment variable in `osint.env`.

#### Scenario: Search by company name
- **WHEN** `companies_house_search` is called with `q="Acme Ltd"`
- **THEN** the tool returns matching UK-registered companies including company number, status, registered address, and incorporation date from the Companies House API

#### Scenario: Missing API key
- **WHEN** `COMPANIES_HOUSE_API_KEY` is not set
- **THEN** the API returns a 401 response (documented behavior, not handled in curl layer)

### Requirement: ICIJ Offshore Leaks search
The system SHALL provide an `icij_offshore_search` curl tool in `osint/companies.yaml` (group: `companies`) that searches the ICIJ Offshore Leaks database covering the Panama Papers, Pandora Papers, and related investigations. No API key required.

#### Scenario: Search by entity name
- **WHEN** `icij_offshore_search` is called with `q="Mossack Fonseca"`
- **THEN** the tool returns matching offshore entities, officers, and intermediaries from the ICIJ database including jurisdiction, linked addresses, and dataset source

### Requirement: ImportYeti US trade data search
The system SHALL provide an `importyeti_search` curl tool in `osint/companies.yaml` (group: `companies`) that searches US customs import records. No API key required.

#### Scenario: Search by company name
- **WHEN** `importyeti_search` is called with `q="Apple Inc"`
- **THEN** the tool returns US import shipment records for matching companies including supplier names, product descriptions, and shipment counts

### Requirement: OpenSanctions entity screening
The system SHALL provide an `opensanctions_search` curl tool in `osint/companies.yaml` (group: `companies`) that screens entities against sanctions lists, PEP databases, and watchlists via the OpenSanctions API. Requires an `OPENSANCTIONS_API_KEY` environment variable in `osint.env`.

#### Scenario: Screen a person or entity
- **WHEN** `opensanctions_search` is called with `q="Vladimir Petrov"`
- **THEN** the tool returns any matching sanctioned individuals or entities including the sanctioning authority, program, and listing date

#### Scenario: No matches found
- **WHEN** `opensanctions_search` is called with a name not on any watchlist
- **THEN** the tool returns an empty results list with a 200 status
