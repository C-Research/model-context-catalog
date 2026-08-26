---
icon: lucide/globe
---

# HTTP API

Alongside the MCP interface, MCC exposes a small set of plain HTTP routes — health checks, a REST mirror of the tool catalog, user listing, and Prometheus metrics. These are ordinary Starlette routes registered on the same server, so they share its host and port.

## Authentication

Routes authenticate the same way: an API key resolved from, in priority order:

1. `X-API-Key: <key>` header
2. `Authorization: Bearer <key>` header
3. `api-key=<key>` query parameter

A header always wins over the query parameter when both are present — prefer a header where possible, since query parameters are more likely to end up in access logs, proxy logs, or browser history. See [API Key backend](auth/backends.md#api-key-api_key) for how keys are minted and revoked.

Each route falls into one of four auth modes:

| Mode | Behavior |
|------|----------|
| **required** (default) | A valid key must resolve to a user. `401 {"error": "unauthorized"}` if missing, invalid, or expired. |
| **optional** | A key is resolved if present, but never required — an unauthenticated request proceeds with `user = None`, scoped to public tools. |
| **anonymous** | No key resolution is attempted at all; the route never sees a user. |
| **admin** | Same as required, plus the resolved user must be in the `admin` group. `401` otherwise. |

## GET /healthz

**Mode:** anonymous

Liveness check — confirms the process can handle an HTTP request. Makes no backend calls.

```json
{"status": "ok"}
```

## GET /readyz

**Mode:** anonymous

Readiness check — confirms the search backend, cache backend, and tool loader are all reachable, each bounded by a short timeout so a hung backend fails fast rather than hanging the probe. Returns `200 {"status": "ok"}` if every check passes, or `503 {"status": "degraded"}` if any fails. The specific failing backend is logged server-side only; the response body never names it, so an unauthenticated caller can't fingerprint internal topology.

## GET /whoami

**Mode:** required

Identity and accessible-tools check — the HTTP counterpart to the `whoami` MCP tool, same fields via `whoami_info`, returned as JSON here instead of text.

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "groups": ["admin", "osint"],
  "tools": ["admin.shell", "osint.whois", "public.request"]
}
```

## GET /tools

**Mode:** optional

Lists the caller's accessible tools, sorted by key. An unauthenticated request gets public tools only — the same scoping `search()`/`describe_tools()` apply as MCP tools.

**Query parameters:**

| Parameter | Description |
|-----------|--------------|
| `format` | `json` (default), `md`, or `html`. `md`/`html` render each tool's signature block (the same form `search()` results use) as markdown or rendered HTML. |

JSON entries (`format=json`, the default) have the shape:

```json
{
  "key": "public.request",
  "groups": ["public"],
  "params": [
    {
      "name": "url",
      "type": "str",
      "required": true,
      "default": null,
      "description": "URL to request.",
      "example": "https://example.com"
    }
  ],
  "return_type": "str",
  "description": "Make an HTTP request and return the response.",
  "example": "public.request(url=\"https://example.com\")"
}
```

`return_type` is `"str | (int, str, str)"` for `exec:` tools (stdout on success, or `(code, stdout, stderr)` on failure), otherwise the tool's declared return type or `"unknown"`.

## GET /tools/{key}

**Mode:** optional

A single tool's detail, same shape as one `GET /tools` entry. Returns `404 {"error": "not found"}` for both an unknown key and one the caller can't access — indistinguishable, so probing keys can't be used to enumerate gated tools.

## POST /tools/{key}

**Mode:** optional

Executes a tool with the JSON request body as its parameters, returning the result as plain text. Shares the same 404 masking as `GET /tools/{key}` for an unknown or inaccessible key, and the same per-`(user, tool)` rate-limit bucket as the MCP `execute` tool (`rate_limit.enabled` in settings).

**Request body:** a JSON object of parameter name → value, or an empty body for a tool with no required parameters.

**Responses:**

| Status | Body |
|--------|------|
| `200` | The tool's result, coerced to plain text |
| `400` | Malformed JSON, a non-object body, or a parameter validation error |
| `404` | Unknown or inaccessible tool key |
| `429` | Rate limit exceeded — body includes the retry-after seconds |
| `500` | The tool raised during execution |

Error bodies are plain text: the full traceback when `settings.DEBUG` is true, otherwise a one-line `Type: message` summary.

This path runs with an identity-only context — there is no HTTP session equivalent to the MCP session store, so [`get_session`/`set_session`](tools/session.md) values are not available and nothing is written back.

## GET /users

**Mode:** admin

Lists all users.

**Query parameters:**

| Parameter | Description |
|-----------|--------------|
| `keys` | `true` to include each user's `.key` metadata (`{"prefix", "created_at", "expires_at"}` — never the hash or raw key). Omitted by default. |

## GET /metrics

**Mode:** anonymous

Prometheus text-exposition of tool-call counters and duration histograms (`mcc_tool_calls_total`, `mcc_tool_call_duration_seconds`), fed by both the MCP `execute` path and `POST /tools/{key}` — a call to the same tool key is counted once regardless of which transport made it.
