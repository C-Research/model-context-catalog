---
icon: lucide/type
---

# Text Tools

String utilities for encoding, hashing, diffing, and regex. Available to all users in the `public` and `text` groups.

---

## `public.text.base64_encode`

Encode text to base64.

| Param | Type | Required |
|-------|------|----------|
| `text` | str | yes |

---

## `public.text.base64_decode`

Decode a base64-encoded string back to text.

| Param | Type | Required |
|-------|------|----------|
| `text` | str | yes |

---

## `public.text.hash`

Hash text using a named algorithm.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | str | yes | Input text |
| `algo` | str | no | Algorithm name (default: `sha256`). Supports `md5`, `sha1`, `sha256`, `sha512`, etc. |

---

## `public.text.diff`

Produce a unified diff between two strings.

| Param | Type | Required |
|-------|------|----------|
| `a` | str | yes |
| `b` | str | yes |

---

## `public.text.regex_search`

Find all regex matches in a string (`re.findall`).

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | str | yes | Regex pattern |
| `string` | str | yes | Input string |
| `flags` | int | no | `re` module flags (default: `0`) |

---

## `public.text.regex_replace`

Replace regex matches in a string (`re.sub`).

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | str | yes | Regex pattern |
| `repl` | str | yes | Replacement string |
| `string` | str | yes | Input string |
| `flags` | int | no | `re` module flags (default: `0`) |

---

## `public.text.jq`

Process JSON content with [jq](https://jqlang.org/).

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | str | yes | JSON string to process |
| `filter` | str | no | jq filter expression (default: `.content`) |
| `opts` | str | no | Additional jq flags |

```
execute("public.text.jq", {"content": "{\"name\": \"alice\"}", "filter": ".name"})
```

Requires `jq` to be installed on the system.
