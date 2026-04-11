## ADDED Requirements

### Requirement: OpenSecrets legislator lookup
The system SHALL provide an `opensecrets_legislators` tool in `osint/gov.yaml` (group: `gov`) that retrieves a list of current US legislators for a given state from the OpenSecrets API. Requires `OPENSECRETS_API_KEY`.

#### Scenario: Get legislators for a state
- **WHEN** `opensecrets_legislators` is called with `state="CA"`
- **THEN** the tool returns JSON from `https://api.opensecrets.org/?method=getLegislators&id=CA&output=json&apikey={OPENSECRETS_API_KEY}` with a list of current legislators including CRP IDs, party, and district

### Requirement: OpenSecrets campaign contributions search
The system SHALL provide an `opensecrets_contributions` tool in `osint/gov.yaml` (group: `gov`) that retrieves campaign contributions for a given candidate CRP ID from the OpenSecrets API. Requires `OPENSECRETS_API_KEY`.

#### Scenario: Get contributions for a candidate
- **WHEN** `opensecrets_contributions` is called with `cid="N00007360"` and `cycle="2024"`
- **THEN** the tool returns JSON from `https://api.opensecrets.org/?method=candContrib&cid=N00007360&cycle=2024&output=json&apikey={OPENSECRETS_API_KEY}` with top contributors, amounts, and contributor types for that election cycle
