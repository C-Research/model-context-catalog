---
icon: lucide/landmark
---

# Government & Records

Tools for searching public government data — SEC filings, US legislation, federal spending, campaign finance, and sanctions. All sources are official government or non-profit APIs.

---

### `edgar_search`

Full-text search of [SEC EDGAR](https://efts.sec.gov) filings from US public companies. Covers 10-K, 10-Q, 8-K, DEF 14A, and all other form types.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Full-text search query. Supports quoted phrases and boolean operators. |
| `form_type` | str | No | _(all)_ | SEC form type filter, e.g. `10-K`, `8-K`, `DEF 14A`. |

**Returns:** JSON with filing metadata — company name, form type, date, and business location.  
**Auth:** None.

??? example "Usage examples"
    Full-text search across all SEC filings:
    ```
    edgar_search(q="climate risk")
    ```

    Find 8-K filings mentioning a company in distress:
    ```
    edgar_search(q="FTX", form_type="8-K")
    ```

    Search for related party disclosures in annual reports:
    ```
    edgar_search(q="related party transactions", form_type="10-K")
    ```

---

### `congress_search`

Search US bills and resolutions via the [Congress.gov API](https://api.congress.gov).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Keyword search for bill titles and text. |
| `limit` | int | No | `20` | Number of results (max 250). |

**Returns:** JSON with bill numbers, titles, sponsors, latest action, and chamber.  
**Auth:** None.

??? example "Usage examples"
    Search for bills on a topic:
    ```
    congress_search(query="artificial intelligence")
    ```

    Find recent legislation mentioning a platform:
    ```
    congress_search(query="TikTok ban", limit=10)
    ```

---

### `usaspending_search`

Search [USASpending.gov](https://www.usaspending.gov) for federal contracts, grants, loans, and other awards.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `keyword` | str | Yes | — | Keyword across award descriptions and recipient names. |
| `award_types` | str | No | contracts + grants | JSON array of award type codes. Contracts: `["A","B","C","D"]`, grants: `["02","03","04","05"]`. |
| `limit` | int | No | `20` | Number of results. |

**Returns:** JSON with recipient names, award amounts, awarding agencies, and date ranges.  
**Auth:** None.

??? example "Usage examples"
    Find federal contracts awarded to a company:
    ```
    usaspending_search(keyword="Palantir")
    ```

    Search grants related to a program:
    ```
    usaspending_search(keyword="border security", award_types=["02","03","04","05"])
    ```

---

### `opensecrets_legislators`

Retrieve current US legislators for a state from [OpenSecrets](https://www.opensecrets.org). The returned CRP IDs can be passed to `opensecrets_contributions`.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `state` | str | Yes | — | Two-letter US state abbreviation (e.g. `CA`, `TX`, `NY`). |

**Returns:** JSON with legislator names, CRP IDs, party, chamber, district, and first elected year.  
**Auth:** `OPENSECRETS_API_KEY` — [register free](https://www.opensecrets.org/api/admin/index.php).

??? example "Usage examples"
    Get all current legislators for California:
    ```
    opensecrets_legislators(state="CA")
    ```

    Look up Texas legislators to find CRP IDs for contribution lookup:
    ```
    opensecrets_legislators(state="TX")
    ```

---

### `opensecrets_contributions`

Retrieve top campaign contributors for a US candidate by CRP ID and election cycle from [OpenSecrets](https://www.opensecrets.org).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `cid` | str | Yes | — | OpenSecrets CRP candidate ID (e.g. `N00007360`). Use `opensecrets_legislators` to find IDs. |
| `cycle` | str | No | `2024` | Election cycle year (e.g. `2024`, `2022`, `2020`). |

**Returns:** JSON with contributor names, total amounts, and contributor types (PAC vs. individual).  
**Auth:** `OPENSECRETS_API_KEY` — [register free](https://www.opensecrets.org/api/admin/index.php).

??? example "Usage examples"
    Get top campaign contributors for a candidate (use opensecrets_legislators to find the CRP ID):
    ```
    opensecrets_contributions(cid="N00007360")
    ```

    Get contributions for a specific election cycle:
    ```
    opensecrets_contributions(cid="N00007360", cycle="2022")
    ```

---

### `ofac`

Search the [OFAC Specially Designated Nationals (SDN)](https://ofac.treasury.gov/sanctions-list-service) list for individuals, entities, and vessels subject to US sanctions.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `name` | str | No | — | Person or entity name. |
| `city` | str | No | — | City of residence or registration. |
| `idNumber` | str | No | — | Passport, national ID, or registration number. |
| `stateProvince` | str | No | — | State or province. |
| `nameScore` | int | No | `100` | Fuzzy match threshold (0–100, 100=exact). |
| `country` | str | No | — | Country code. |
| `programs` | list | No | `[]` | Filter by sanctions programs (e.g. `["UKRAINE-EO13661"]`). |
| `type` | str | No | `Entity` | Record type: `Entity`, `Individual`, `Vessel`, `Aircraft`. |
| `address` | str | No | — | Street address. |

**Returns:** JSON with matching SDN entries and associated sanctions program details.  
**Auth:** None.

??? example "Usage examples"
    Screen an individual by name:
    ```
    ofac(name="Viktor Vekselberg")
    ```

    Search for a sanctioned entity:
    ```
    ofac(name="Wagner", type="Entity")
    ```

    Look up by passport or ID number:
    ```
    ofac(idNumber="PA1234567")
    ```

    Fuzzy name match with lower threshold:
    ```
    ofac(name="Rotenberg", nameScore=80)
    ```
