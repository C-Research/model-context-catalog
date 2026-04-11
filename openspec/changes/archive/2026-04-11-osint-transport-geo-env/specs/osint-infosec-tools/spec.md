## ADDED Requirements

### Requirement: urlscan.io scan search
The system SHALL provide a `urlscan_search` tool in `osint/infosec.yaml` (group: `infosec`) that searches the urlscan.io public index for existing website scans matching a query. No API key required for search.

#### Scenario: Search scans by domain
- **WHEN** `urlscan_search` is called with `q="domain:example.com"`
- **THEN** the tool returns JSON from `https://urlscan.io/api/v1/search/?q=domain%3Aexample.com&size=10` with matching scan results including screenshot URLs, page metadata, and detected technologies

#### Scenario: Search scans by IP
- **WHEN** `urlscan_search` is called with `q="ip:1.2.3.4"`
- **THEN** the tool returns scans associated with that IP address

### Requirement: urlscan.io URL submission
The system SHALL provide a `urlscan_submit` tool in `osint/infosec.yaml` (group: `infosec`) that submits a URL to urlscan.io for scanning. Requires `URLSCAN_API_KEY`.

#### Scenario: Submit a URL for scanning
- **WHEN** `urlscan_submit` is called with `url="https://suspicious-site.example.com"` and `visibility="public"`
- **THEN** the tool POSTs to `https://urlscan.io/api/v1/scan/` with the URL and visibility setting and returns JSON containing the scan UUID and result URL where the full report will be available
