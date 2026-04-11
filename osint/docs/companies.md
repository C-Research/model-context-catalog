---
icon: lucide/building-2
---

# Companies & Business

Tools for corporate intelligence — company registrations, beneficial ownership, offshore finance, US imports, nonprofit financials, and sanctions screening. Spans 200M+ company records across dozens of jurisdictions.

---

### `opencorporates_search`

Search the [OpenCorporates](https://opencorporates.com) database of 200M+ company registrations worldwide.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Company name or keyword. |
| `jurisdiction_code` | str | No | _(global)_ | Filter by jurisdiction, e.g. `us_de` (Delaware), `gb` (UK), `de` (Germany). |
| `per_page` | int | No | `20` | Results per page (max 100). |

**Returns:** JSON with company names, registration numbers, jurisdictions, registered addresses, and status.  
**Auth:** None for basic search.

---

### `propublica_nonprofit`

Browse IRS 990 returns for US tax-exempt organizations via [ProPublica Nonprofit Explorer](https://projects.propublica.org/nonprofits/).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Organization name, person name, or city. Use `"exact phrase"`, `+required`, `-excluded`. |

**Returns:** JSON with organization names, EINs, revenue, expenses, executive compensation, and filing years.  
**Auth:** None.

---

### `companies_house_search`

Search the [UK Companies House](https://find-and-update.company-information.service.gov.uk) official register of UK-incorporated companies.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Company name or keyword. |
| `per_page` | int | No | `20` | Results to return (max 100). |

**Returns:** JSON with company name, number, status, type, registered address, and incorporation date.  
**Auth:** `COMPANIES_HOUSE_API_KEY` — [register free](https://developer.company-information.service.gov.uk/).

---

### `icij_offshore_search`

Search the [ICIJ Offshore Leaks](https://offshoreleaks.icij.org) database spanning the Panama Papers, Pandora Papers, Paradise Papers, and other offshore finance investigations.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Entity, person, officer, or intermediary name. |
| `country` | str | No | _(global)_ | Filter by country code (e.g. `RU`, `GB`, `CN`). |
| `jurisdiction` | str | No | _(all)_ | Filter by offshore jurisdiction (e.g. `BVI`, `PAN`). |
| `category` | int | No | `0` | `0`=all, `1`=entity, `2`=officer, `3`=intermediary, `4`=address. |

**Returns:** JSON with matching entities, officers, intermediaries, and addresses with source dataset.  
**Auth:** None.

---

### `importyeti_search`

Search US customs import records on [ImportYeti](https://www.importyeti.com) for companies shipping goods into the United States.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Company name to search import records for. |

**Returns:** JSON with matching companies, supplier names, countries of origin, shipment counts, and product descriptions from US Bill of Lading data.  
**Auth:** None.

---

### `opensanctions_search`

Screen individuals and entities against global sanctions lists, PEP (Politically Exposed Persons) databases, and watchlists via [OpenSanctions](https://www.opensanctions.org).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Person or entity name to screen. |
| `limit` | int | No | `10` | Maximum results (max 50). |

**Returns:** JSON with matching entities, sanctioning authority, program, listing date, and aliases.  
**Auth:** `OPENSANCTIONS_API_KEY` — [register free](https://www.opensanctions.org/api/).
