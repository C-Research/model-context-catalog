---
icon: lucide/globe
---

# HTTP Tools

Make HTTP requests from the catalog. Two variants are available: a full-featured admin tool and a responsible-by-default public tool.

## `admin.http.request`

Full HTTP client. Restricted to the `admin` and `http` groups.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `method` | str | yes | HTTP method (`GET`, `POST`, etc.) |
| `url` | str | yes | Request URL |
| `params` | dict | no | Query string parameters |
| `headers` | dict | no | Additional request headers |
| `json` | dict | no | JSON request body |
| `content` | str | no | Raw request body |
| `responsible` | bool | no | Use Claude agent user-agent string (default: `true`) |

Returns a dict with `status`, `headers`, and `content` (parsed JSON or raw text).

```
execute("admin.http.request", {"method": "POST", "url": "https://api.example.com/data", "json": {"key": "value"}})
```

## `public.http.responsible-get`

A constrained variant locked to `GET` and `responsible=true`. Available to all users in the `public` and `http` groups.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | str | yes | URL to fetch |
| `params` | dict | no | Query string parameters |
| `headers` | dict | no | Additional request headers |

```
execute("public.http.responsible-get", {"url": "https://example.com"})
```

The responsible flag sets a Claude-identifying user-agent string. This is the default for LLM-initiated requests — it's good practice to identify automated traffic.

