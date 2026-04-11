## Requirements

### Requirement: Certificate transparency search
The system SHALL provide a `crtsh` tool in `osint/infosec.yaml` (group: `infosec`) that queries crt.sh for certificates logged for a given domain. No API key required.

#### Scenario: Find certificates for a domain
- **WHEN** `crtsh` is called with `domain="example.com"`
- **THEN** the tool returns a JSON response from `https://crt.sh/?q=example.com&output=json` listing all certificates including SANs, issuer, and expiry

### Requirement: VirusTotal URL/IP/domain/hash lookup
The system SHALL provide a `virustotal` tool in `osint/infosec.yaml` (group: `infosec`) that queries the VirusTotal API v3 for threat intelligence on a given indicator. Requires `VIRUSTOTAL_API_KEY`.

#### Scenario: Look up a file hash
- **WHEN** `virustotal` is called with `indicator="<sha256>"` and `type="file"`
- **THEN** the tool returns JSON from `https://www.virustotal.com/api/v3/files/<sha256>` with multi-engine scan results

#### Scenario: Look up a domain
- **WHEN** `virustotal` is called with `indicator="example.com"` and `type="domain"`
- **THEN** the tool returns JSON from `https://www.virustotal.com/api/v3/domains/example.com`

### Requirement: AbuseIPDB IP reputation check
The system SHALL provide an `abuseipdb` tool in `osint/infosec.yaml` (group: `infosec`) that checks an IP address against the AbuseIPDB database. Requires `ABUSEIPDB_API_KEY`.

#### Scenario: Check an IP address
- **WHEN** `abuseipdb` is called with `ip="1.2.3.4"`
- **THEN** the tool returns a JSON response from `https://api.abuseipdb.com/api/v2/check` with abuse confidence score and report count

### Requirement: NVD CVE lookup
The system SHALL provide an `nvd_cve` tool in `osint/infosec.yaml` (group: `infosec`) that retrieves CVE details from the NIST National Vulnerability Database. No API key required.

#### Scenario: Look up a CVE by ID
- **WHEN** `nvd_cve` is called with `cve_id="CVE-2021-44228"`
- **THEN** the tool returns JSON from `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228` with CVSS scores, description, and affected products

### Requirement: MalwareBazaar hash lookup
The system SHALL provide a `malwarebazaar` tool in `osint/infosec.yaml` (group: `infosec`) that queries MalwareBazaar for known malware sample information by hash. No API key required.

#### Scenario: Look up a file hash
- **WHEN** `malwarebazaar` is called with `hash="<sha256>"`
- **THEN** the tool returns JSON from the MalwareBazaar API with sample metadata, tags, and signature if the hash is known

### Requirement: Wayback Machine availability check
The system SHALL provide a `wayback` tool in `osint/infosec.yaml` (group: `infosec`) that checks whether a URL has been archived by the Wayback Machine and returns the closest snapshot. No API key required.

#### Scenario: Check URL availability
- **WHEN** `wayback` is called with `url="https://example.com/page"`
- **THEN** the tool returns JSON from `http://archive.org/wayback/available?url=...` with the closest available snapshot URL and timestamp

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
