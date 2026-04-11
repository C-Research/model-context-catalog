## Requirements

### Requirement: OpenSky live aircraft states by bounding box
The system SHALL provide an `opensky_states` tool in `osint/transport.yaml` (group: `transport`) that retrieves live aircraft transponder states within a geographic bounding box from the OpenSky Network API. No API key required for anonymous access.

#### Scenario: Query aircraft in a bounding box
- **WHEN** `opensky_states` is called with `lamin="51.0"`, `lomin="-1.0"`, `lamax="52.0"`, `lomax="1.0"`
- **THEN** the tool returns JSON from `https://opensky-network.org/api/states/all?lamin=51.0&lomin=-1.0&lamax=52.0&lomax=1.0` with an array of aircraft states including ICAO24 transponder code, callsign, origin country, altitude, velocity, and heading

#### Scenario: No aircraft in bounding box
- **WHEN** `opensky_states` is called with a bounding box over an area with no current flights
- **THEN** the tool returns a JSON response with `states: null`

### Requirement: OpenSky aircraft state by ICAO24
The system SHALL provide an `opensky_aircraft` tool in `osint/transport.yaml` (group: `transport`) that retrieves the current transponder state for a specific aircraft by its ICAO24 hex identifier. No API key required.

#### Scenario: Look up a specific aircraft
- **WHEN** `opensky_aircraft` is called with `icao24="3c6444"`
- **THEN** the tool returns JSON from `https://opensky-network.org/api/states/all?icao24=3c6444` with the current state vector for that aircraft if it is currently airborne, or `states: null` if it is not
