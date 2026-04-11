## 1. Geo Tools (osint/geo.yaml)

- [x] 1.1 Create `osint/geo.yaml` with `nominatim_geocode` curl tool (forward geocode, User-Agent header, `q` + `limit` params)
- [x] 1.2 Add `nominatim_reverse` curl tool to `osint/geo.yaml` (`lat`, `lon` params, reverse endpoint)
- [x] 1.3 Add `overpass_query` curl tool to `osint/geo.yaml` (POST to overpass-api.de, raw `query` param)

## 2. Transport Tools (osint/transport.yaml)

- [x] 2.1 Create `osint/transport.yaml` with `opensky_states` curl tool (bounding box params: `lamin`, `lomin`, `lamax`, `lomax`)
- [x] 2.2 Add `opensky_aircraft` curl tool to `osint/transport.yaml` (`icao24` param)

## 3. urlscan.io Tools (extend osint/infosec.yaml)

- [x] 3.1 Add `urlscan_search` curl tool to `osint/infosec.yaml` (GET search, `q` + `size` params, no key required)
- [x] 3.2 Add `urlscan_submit` curl tool to `osint/infosec.yaml` (POST scan, `url` + `visibility` params, requires `URLSCAN_API_KEY`)

## 4. Environment Tools (osint/environment.yaml)

- [x] 4.1 Create `osint/environment.yaml` with `nasa_firms` curl tool (`source`, `country`, `days` params, requires `NASA_FIRMS_API_KEY`)
- [x] 4.2 Add `gfw_vessels` curl tool to `osint/environment.yaml` (`query` + `limit` params, requires `GFW_API_KEY`)

## 5. OpenSecrets Tools (extend osint/gov.yaml)

- [x] 5.1 Add `opensecrets_legislators` curl tool to `osint/gov.yaml` (`state` param, requires `OPENSECRETS_API_KEY`)
- [x] 5.2 Add `opensecrets_contributions` curl tool to `osint/gov.yaml` (`cid` + `cycle` params, requires `OPENSECRETS_API_KEY`)

## 6. API Key Plumbing

- [x] 6.1 Add `URLSCAN_API_KEY`, `NASA_FIRMS_API_KEY`, `GFW_API_KEY`, `OPENSECRETS_API_KEY` placeholders to `osint/osint.env.example`
- [x] 6.2 Add same keys to `osint/osint.env` (empty values, not committed)
