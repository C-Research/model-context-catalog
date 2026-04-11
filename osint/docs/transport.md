---
icon: lucide/plane
---

# Transport & Aviation

Tools for live aircraft tracking using [OpenSky Network](https://opensky-network.org) ADS-B transponder data. All data is sourced from a global network of volunteer receivers.

---

### `opensky_states`

Retrieve live aircraft transponder states within a geographic bounding box.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `lamin` | str | Yes | — | Minimum latitude (south boundary) in decimal degrees. |
| `lomin` | str | Yes | — | Minimum longitude (west boundary) in decimal degrees. |
| `lamax` | str | Yes | — | Maximum latitude (north boundary) in decimal degrees. |
| `lomax` | str | Yes | — | Maximum longitude (east boundary) in decimal degrees. |

**Returns:** JSON array of state vectors — ICAO24 code, callsign, origin country, position timestamp, longitude, latitude, altitude (meters), on-ground flag, velocity (m/s), heading (degrees), vertical rate (m/s), and squawk code. Returns `states: null` if no aircraft are in the box.  
**Auth:** None (~400 req/day anonymous).

??? example "Bounding box examples"

    | Region | lamin | lomin | lamax | lomax |
    |--------|-------|-------|-------|-------|
    | Ukraine | 44.0 | 22.0 | 52.5 | 40.2 |
    | UK & Ireland | 49.5 | -10.5 | 59.5 | 2.0 |
    | Continental US | 24.0 | -125.0 | 49.5 | -66.5 |
    | Persian Gulf | 22.0 | 48.0 | 27.0 | 60.0 |

---

### `opensky_aircraft`

Look up the current transponder state for a specific aircraft by its [ICAO24](https://www.icao.int/publications/doc8643/pages/search.aspx) hex identifier.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `icao24` | str | Yes | — | 6-character ICAO24 hex transponder code (e.g. `3c6444`). Case-insensitive. |

**Returns:** JSON with the aircraft's current state vector if airborne, or `states: null` if not currently tracked.  
**Auth:** None.
