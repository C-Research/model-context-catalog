## ADDED Requirements

### Requirement: NASA FIRMS active fire data
The system SHALL provide a `nasa_firms` tool in `osint/environment.yaml` (group: `environment`) that retrieves active fire and thermal anomaly detections from the NASA Fire Information for Resource Management System (FIRMS). Requires `NASA_FIRMS_API_KEY`.

#### Scenario: Query active fires for a country
- **WHEN** `nasa_firms` is called with `country="UKR"` and `days="1"`
- **THEN** the tool returns CSV data from `https://firms.modaps.eosdis.nasa.gov/api/country/csv/{NASA_FIRMS_API_KEY}/VIIRS_SNPP_NRT/UKR/1` containing fire radiative power, confidence, latitude, longitude, and acquisition time for each detected thermal anomaly

#### Scenario: Query with different satellite source
- **WHEN** `nasa_firms` is called with `source="MODIS_NRT"`, `country="SYR"`, and `days="3"`
- **THEN** the tool fetches from the MODIS NRT endpoint for the specified country and day range

### Requirement: Global Fishing Watch vessel search
The system SHALL provide a `gfw_vessels` tool in `osint/environment.yaml` (group: `environment`) that searches the Global Fishing Watch vessel identity database for vessels matching a name, MMSI, or IMO number. Requires `GFW_API_KEY`.

#### Scenario: Search vessels by name
- **WHEN** `gfw_vessels` is called with `query="OCEAN STAR"`
- **THEN** the tool returns JSON from `https://gateway.api.globalfishingwatch.org/v3/vessels/search?query=OCEAN+STAR&datasets[0]=public-global-vessel-identity:latest` with matching vessel records including flags, gear types, and vessel IDs

#### Scenario: Search vessel by MMSI
- **WHEN** `gfw_vessels` is called with `query="123456789"`
- **THEN** the tool returns vessel identity records matching that MMSI number
