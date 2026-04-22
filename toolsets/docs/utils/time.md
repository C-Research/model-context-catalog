---
icon: lucide/clock
---

# Time Tools

Date and time utilities. Available to all users in the `public` and `time` groups.

---

## `public.time.now`

Return the current date and time as an ISO 8601 string.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `tz` | str | no | Timezone name (default: `UTC`) |

```
execute("public.time.now", {"tz": "America/New_York"})
→ "2025-04-05T10:30:00-04:00"
```

---

## `public.time.format`

Format an ISO 8601 datetime string using a `strftime` format.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `dt` | str | yes | ISO 8601 datetime string |
| `fmt` | str | yes | `strftime` format string |

```
execute("public.time.format", {"dt": "2025-04-05T10:30:00", "fmt": "%B %d, %Y"})
→ "April 05, 2025"
```

---

## `public.time.delta`

Add a time delta to an ISO 8601 datetime string.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `dt` | str | yes | ISO 8601 datetime string |
| `days` | int | no | Days to add |
| `hours` | int | no | Hours to add |
| `minutes` | int | no | Minutes to add |
| `seconds` | int | no | Seconds to add |

Returns an ISO 8601 string. Use negative values to subtract.

```
execute("public.time.delta", {"dt": "2025-04-05T00:00:00", "days": 7})
→ "2025-04-12T00:00:00"
```
