## ADDED Requirements

### Requirement: Nominatim forward geocoding
The system SHALL provide a `nominatim_geocode` tool in `osint/geo.yaml` (group: `geo`) that geocodes a place name or address to coordinates using the Nominatim OpenStreetMap API. No API key required. The request MUST include a `User-Agent: mcc-osint/1.0` header.

#### Scenario: Geocode a city name
- **WHEN** `nominatim_geocode` is called with `q="Berlin, Germany"`
- **THEN** the tool returns a JSON array from `https://nominatim.openstreetmap.org/search?q=Berlin%2C+Germany&format=json&limit=5` with place names, lat/lon coordinates, and OSM IDs

#### Scenario: Geocode a street address
- **WHEN** `nominatim_geocode` is called with `q="1600 Pennsylvania Ave NW, Washington DC"`
- **THEN** the tool returns matching geocoded results with coordinates

### Requirement: Nominatim reverse geocoding
The system SHALL provide a `nominatim_reverse` tool in `osint/geo.yaml` (group: `geo`) that resolves a latitude/longitude coordinate to a place name and address. No API key required. The request MUST include a `User-Agent: mcc-osint/1.0` header.

#### Scenario: Reverse geocode a coordinate
- **WHEN** `nominatim_reverse` is called with `lat="52.5200"` and `lon="13.4050"`
- **THEN** the tool returns JSON from `https://nominatim.openstreetmap.org/reverse?lat=52.5200&lon=13.4050&format=json` with the address, place name, and OSM metadata

### Requirement: Overpass OSM query
The system SHALL provide an `overpass_query` tool in `osint/geo.yaml` (group: `geo`) that executes a raw Overpass QL query against the OpenStreetMap Overpass API. No API key required.

#### Scenario: Query OSM nodes by tag
- **WHEN** `overpass_query` is called with `query='[out:json];node["amenity"="hospital"](51.4,30.4,51.6,30.6);out;'`
- **THEN** the tool POSTs the query to `https://overpass-api.de/api/interpreter` and returns the JSON response with matching OSM elements

#### Scenario: Query with timeout
- **WHEN** `overpass_query` is called with a query containing `[timeout:30]`
- **THEN** the Overpass API respects the timeout directive and returns results or a timeout error
