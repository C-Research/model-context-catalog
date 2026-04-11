---
icon: lucide/map-pin
---

# Geolocation

Tools for geocoding, reverse geocoding, and querying geographic features using OpenStreetMap data. All tools are free with no API key required.

---

### `nominatim_geocode`

Forward geocode a place name or address to latitude/longitude coordinates using [Nominatim](https://nominatim.openstreetmap.org) (OpenStreetMap).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Place name, address, or query (e.g. `Berlin, Germany`, `1600 Pennsylvania Ave NW`). |
| `limit` | int | No | `5` | Maximum results to return. |

**Returns:** JSON array of matching places with coordinates, display name, and OSM metadata.  
**Auth:** None. Rate limit: 1 request/second.

---

### `nominatim_reverse`

Reverse geocode a latitude/longitude coordinate to a place name and address using [Nominatim](https://nominatim.openstreetmap.org).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `lat` | str | Yes | — | Latitude in decimal degrees (e.g. `52.5200`). |
| `lon` | str | Yes | — | Longitude in decimal degrees (e.g. `13.4050`). |

**Returns:** JSON with the full address, place name, OSM type, and bounding box.  
**Auth:** None. Rate limit: 1 request/second.

---

### `overpass_query`

Execute a raw [Overpass QL](https://overpass-api.de) query against the OpenStreetMap Overpass API. Useful for finding infrastructure, facilities, or geographic features within a bounding box.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Raw Overpass QL query. Start with `[out:json]` for JSON output. |

**Returns:** JSON (or XML) with matching OSM nodes, ways, and relations.  
**Auth:** None. Include `[timeout:N]` in your query to set a server-side timeout.

??? example "Example queries"

    Find hospitals in a bounding box (Kyiv):
    ```
    [out:json];node["amenity"="hospital"](50.3,30.3,50.6,30.7);out;
    ```

    Find all bridges in a region:
    ```
    [out:json];way["bridge"="yes"](51.4,30.4,51.6,30.6);out geom;
    ```

    Find fuel stations near coordinates:
    ```
    [out:json];node["amenity"="fuel"](around:5000,48.8566,2.3522);out;
    ```
