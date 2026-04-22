---
icon: lucide/leaf
---

# Environment & Maritime

Tools for satellite-based environmental monitoring and maritime vessel tracking. Useful for conflict monitoring, sanctions enforcement research, and environmental journalism.

---

### `nasa_firms`

Retrieve active fire and thermal anomaly detections from [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) (Fire Information for Resource Management System), sourced from polar-orbiting satellites.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `country` | str | Yes | — | ISO 3166-1 alpha-3 country code (e.g. `UKR`, `SYR`, `SDN`, `BRA`). |
| `days` | int | No | `1` | Days of data to retrieve (1–10). |
| `source` | str | No | `VIIRS_SNPP_NRT` | Satellite/instrument. Options: `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT`, `MODIS_SP`. |

**Returns:** CSV with fire radiative power, confidence level, latitude, longitude, brightness temperature, satellite, instrument, and acquisition timestamp for each detected hotspot.  
**Auth:** `NASA_FIRMS_API_KEY` — [register free](https://firms.modaps.eosdis.nasa.gov/api/map_key/).

??? example "Usage examples"
    Get active fires in Ukraine over the last 3 days:
    ```
    nasa_firms(country="UKR", days=3)
    ```

    Get Amazon deforestation fire detections using high-resolution VIIRS:
    ```
    nasa_firms(country="BRA", source="VIIRS_SNPP_NRT", days=7)
    ```

!!! note "Source selection"
    VIIRS (375m resolution) provides finer spatial detail than MODIS (1km). `_NRT` sources are near-real-time (within hours); `MODIS_SP` is a science-grade reprocessed product.

---

### `gfw_vessels`

Search the [Global Fishing Watch](https://globalfishingwatch.org) vessel identity database for fishing vessels by name, MMSI, or IMO number.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Vessel name, MMSI number, IMO number, or call sign. |
| `limit` | int | No | `10` | Maximum vessel records to return. |

**Returns:** JSON with matching vessel records including flags, gear types, vessel IDs, and identity sources.  
**Auth:** `GFW_API_KEY` — [register free](https://globalfishingwatch.org/our-apis/).

??? example "Usage examples"
    Search for a vessel by name:
    ```
    gfw_vessels(query="Andromeda")
    ```

    Look up a vessel by MMSI number:
    ```
    gfw_vessels(query="636012345")
    ```

    Search by IMO number:
    ```
    gfw_vessels(query="IMO9234567")
    ```

!!! tip "Use cases"
    - Track vessels implicated in IUU (illegal, unreported, unregulated) fishing
    - Identify flag-of-convenience registrations
    - Cross-reference vessels operating near conflict zones or under sanctions
