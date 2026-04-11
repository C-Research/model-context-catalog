## Context

MCC's `curl:` shorthand renders a Jinja2 template and executes it as a shell command, returning stdout. This makes any REST API expressible as a zero-Python tool definition. The OSINT space has dozens of high-quality free/open APIs that are trivially wrappable this way. The current `osint/search.yaml` mixes Python `fn:` tools and `curl:` tools in one file; as the catalog grows this becomes unwieldy.

## Goals / Non-Goals

**Goals:**
- One YAML file per domain (news, academic, gov, infosec, companies, crypto)
- Zero new Python dependencies — all new tools use `curl:` only
- Tools discoverable by group (each file declares its own group)
- API keys managed via `env_file: osint.env` at the file level (requires `file-level-env-in-yaml`)
- `search.yaml` trimmed to Python-only tools after moving `curl:` tools out

**Non-Goals:**
- Response parsing / post-processing beyond what the raw API returns
- Pagination helpers or result normalisation
- Tools requiring OAuth flows (e.g. Twitter/X, LinkedIn)
- Paid-only services (Shodan deep access, Dehashed, DarkOwl)

## Decisions

### One file per domain, not one file per provider

**Decision**: Group by domain (infosec, academic, gov) not by provider (VirusTotal, arXiv, etc.).

**Why**: An LLM searching `group=infosec` gets a coherent toolset. Provider-per-file would create many small files with one or two tools each. Domain files stay manageable (5–10 tools each) and map naturally to RBAC groups.

### curl: template design — URL params vs stdin

**Decision**: Prefer URL-param style (`curl "https://api.example.com?q={{ q | urlencode }}"`) for GET APIs. For the few POST APIs (OFAC, VirusTotal scan submit), use `-d` or `-F` flags in the template.

**Why**: GET APIs are the norm for search/lookup. URL params are transparent, logged, and easier to debug. The `urlencode` Jinja2 filter handles unsafe chars.

### Key injection via file-level env_file

**Decision**: All new YAML files declare `env_file: osint.env` at the top level. Tools reference `${KEY_NAME}` in their curl template or `override:` field.

**Why**: Assumes `file-level-env-in-yaml` is in place. If it isn't yet, the fallback is per-tool `env_file: osint.env` — identical behaviour, more repetition.

### Groups per file

| File | Group |
|------|-------|
| news.yaml | `[news]` |
| academic.yaml | `[academic]` |
| gov.yaml | `[gov]` |
| infosec.yaml | `[infosec]` |
| companies.yaml | `[companies]` |
| crypto.yaml | `[crypto]` |
| search.yaml | `[web, search]` (unchanged) |

### search.yaml refactor

The three blockchain tools, OFAC, and ProPublica move to their domain files. `search.yaml` retains only `serpapi_search` and `gdelt` (both `fn:` tools). This keeps the split clean: `search.yaml` = Python wrappers, everything else = curl catalogs.

## Risks / Trade-offs

- **API shape changes** → curl tools return raw JSON; if an API changes its response schema, the tool still "works" but callers get unexpected output. Mitigation: document expected response shape in tool descriptions.
- **Rate limits on open APIs** → arXiv, CrossRef, and Semantic Scholar have soft rate limits. Mitigation: note in tool descriptions; no retry logic needed at this layer.
- **VirusTotal / AbuseIPDB key exposure** → keys are in `osint.env` which must stay gitignored. Mitigation: `osint.env` is already gitignored; add placeholder entries to a committed `osint.env.example`.
- **OFAC POST body** → OFAC's search endpoint takes a JSON body, which doesn't fit the simple `curl:` URL template pattern cleanly. Already handled in current `search.yaml` via `stdin: true` — keep that pattern.

## Open Questions

- Should `blockchair` be added to `crypto.yaml`? It supports BTC, ETH, and a dozen other chains via a unified API and is free for basic lookups. **Tentative yes** — adds meaningful multi-chain coverage at zero cost.
- `osint.env.example` committed with placeholders — yes/no? **Yes**, makes onboarding obvious.
