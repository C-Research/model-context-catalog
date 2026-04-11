## Context

The OSINT catalog currently covers academic, news, infosec, gov, companies, crypto, and conflict domains but has no tools for geolocation, transport, or environmental monitoring — all prominent Bellingcat toolkit categories. All new tools follow the existing `curl:` pattern established in the zero-dep batch and bellingcat changes: YAML-defined tools with template-rendered HTTP calls, no new Python dependencies.

## Goals / Non-Goals

**Goals:**
- Add Nominatim (geocoding) and Overpass (OSM queries) in a new `osint/geo.yaml`
- Add OpenSky Network (aviation) in a new `osint/transport.yaml`
- Add NASA FIRMS (fire data) and Global Fishing Watch (vessel search) in a new `osint/environment.yaml`
- Extend `osint/infosec.yaml` with urlscan.io search and submit
- Extend `osint/gov.yaml` with OpenSecrets legislator and contribution lookups
- Add four new API key placeholders to `osint/osint.env`

**Non-Goals:**
- Maritime AIS beyond GFW (MarineTraffic is paid)
- Flightradar24 / FlightAware (no free public API)
- Facial recognition or social media scraping
- Any new Python packages

## Decisions

**All tools as `curl:` stubs** — Every new tool fits the curl template pattern. OpenSky returns JSON without auth; Nominatim and Overpass are open. Tools requiring API keys (FIRMS, GFW, OpenSecrets, urlscan submit) use `env_file: osint.env` already established in the catalog.

**Overpass as raw query parameter** — Overpass QL queries can be complex. Rather than parameterizing individual filters, the `overpass_query` tool accepts a raw `query` string. This matches how investigators actually use Overpass (composing QL manually) and avoids premature abstraction.

**OpenSky two-tool split** — Bounding-box queries (`opensky_states`) and per-aircraft queries (`opensky_aircraft`) serve different investigative workflows: area surveillance vs. tail-number tracking. Splitting keeps each tool focused.

**urlscan submit vs. search** — Submit creates a new scan (side effect, requires API key); search queries the public index (read-only, no key needed). Keeping them as separate tools makes the distinction clear and allows unauthenticated search without requiring the key.

## Risks / Trade-offs

- **Nominatim rate limits** → Nominatim enforces 1 req/sec and requires a valid `User-Agent`. The curl template should set `User-Agent: mcc-osint/1.0`. Heavy use should migrate to a self-hosted instance.
- **OpenSky anonymous limits** → Anonymous users are rate-limited to ~400 requests/day. For production use, OpenSky credentials can be added via env vars.
- **GFW API stability** → Global Fishing Watch's v3 API is relatively new; endpoint paths may change. The spec pins the current path.
- **NASA FIRMS CSV format** → FIRMS returns CSV, not JSON. The tool returns the raw CSV string; callers must parse it.
