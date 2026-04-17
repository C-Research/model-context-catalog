# 30-Min Technical Deep Dive

---

## 1. The Problem (3 min)

- Standard MCP servers expose N tools → N tool definitions in context on every request
- At 30+ tools, a significant chunk of every request is just describing capabilities
- Tool selection degrades with list size; models struggle to choose well from flat manifests

**The fix:** decouple discovery from the tool list — give the model `search` + `execute` and an arbitrarily large catalog behind it

---

## 2. MCC Architecture (7 min)

- **Two MCP tools only:** `search(query)` → ranked results with signatures; `execute(key, params)` → validated, permission-checked execution
- **Stack:** FastMCP · Elasticsearch (hybrid keyword + semantic via FastEmbed) · dynaconf
- **Tool types:**
  - `fn:` — Python callable, runs in-process
  - `exec:` — shell command, any interpreter, with Jinja2 template interpolation (`{{ param | quote }}`) and resource limits (cpu/mem/time)
- **RBAC:** tools declare `groups`, users stored in ES, access via group membership or explicit `tools` grants
- **Auth backends:** GitHub OAuth, GitHub PAT, `dev-admin` (dev)
- **Hot reload** — catalog updates without server restart

---

## 3. OSINT Catalog (8 min)

44 tools across 12 categories — each is a thin wrapper, no scraping, no headless browsers

| Category | Highlights |
|---|---|
| Infosec & Network | `crtsh`, `virustotal`, `abuseipdb`, `nvd_cve`, `malwarebazaar`, `nmap_scan` |
| Companies | `opencorporates_search` (200M+ corps), `icij_offshore_search` (Panama/Pandora Papers), `opensanctions_search` |
| People & Social | `sherlock_search` — 400+ platforms, no auth |
| Geo / Transport / Maritime | IP geolocation, flight tracking, vessel AIS, wildfire/fishing watch |
| Crypto / Gov / Academic | Blockchain explorers, OpenSecrets, arXiv/Semantic Scholar |

- Most require zero API keys; all paid tools have free tiers
- Install via `pip install mcc[osint]`; keys in `osint.env`

---

## 4. Live Demo (10 min)

Scenario: investigate a suspicious domain end-to-end

```
search("certificate transparency")  → crtsh
execute("crtsh", {domain: "%.target.com"})

search("check ip reputation")  → abuseipdb, virustotal
execute("abuseipdb", {ip: "..."})

search("scan open ports")  → nmap_scan
execute("nmap_scan", {target: "...", arguments: "-sV"})
```

- Show ranked search results with relevance scores
- Trigger an RBAC denial on `nmap_scan` (analyst group only), grant access, re-execute
- Hot-reload a new tool YAML mid-session

---

## 5. Open Questions + Next Steps (5 min)

- Missing OSINT categories?
- Auth model fit for your environment?
- Client-side integration needs?
- Deployment topology — single-tenant vs. shared catalog

---

**Pre-demo checklist:** ES running · VirusTotal + AbuseIPDB keys in `osint.env` · target domain/IP prepped · analyst user created with restricted group
