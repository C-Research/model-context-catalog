## Why

The MCC OSINT catalog has zero coverage for transport (aviation/maritime), geolocation, and environment — all major Bellingcat toolkit categories. Adding free/open REST APIs for these fills the gap with no new Python dependencies.

## What Changes

- **New file** `osint/geo.yaml` — Nominatim forward/reverse geocoding and Overpass OSM queries (no auth)
- **New file** `osint/transport.yaml` — OpenSky Network live and historical flight state lookups (no auth)
- **Extended** `osint/infosec.yaml` — urlscan.io search and submit (free, search requires no key; submit requires key)
- **New file** `osint/environment.yaml` — NASA FIRMS active fire/thermal anomaly data (free key), Global Fishing Watch vessel search (free key)
- **Extended** `osint/gov.yaml` — OpenSecrets campaign finance (legislators + contributions, free key)
- **Extended** `osint/osint.env` / `osint/osint.env.example` — new key placeholders: `NASA_FIRMS_API_KEY`, `GFW_API_KEY`, `OPENSECRETS_API_KEY`, `URLSCAN_API_KEY`

## Capabilities

### New Capabilities
- `osint-geo-tools`: Forward and reverse geocoding via Nominatim (OSM) and spatial queries via Overpass API
- `osint-transport-tools`: Live aircraft state lookup and bounding-box flight queries via OpenSky Network
- `osint-environment-tools`: Active fire/thermal anomaly data (NASA FIRMS) and fishing vessel search (Global Fishing Watch)

### Modified Capabilities
- `osint-infosec-tools`: Two new urlscan.io tools (search existing scans, submit new URL for scanning)
- `osint-gov-tools`: Two new OpenSecrets tools (legislator lookup, campaign contribution search)

## Impact

- `osint/geo.yaml`: new file, 3 curl tools (nominatim_geocode, nominatim_reverse, overpass_query)
- `osint/transport.yaml`: new file, 2 curl tools (opensky_states, opensky_aircraft)
- `osint/environment.yaml`: new file, 2 curl tools (nasa_firms, gfw_vessels)
- `osint/infosec.yaml`: 2 tools appended (urlscan_search, urlscan_submit)
- `osint/gov.yaml`: 2 tools appended (opensecrets_legislators, opensecrets_contributions)
- `osint/osint.env` + `osint/osint.env.example`: 4 new key placeholders
- No changes to MCC core; no new Python packages
