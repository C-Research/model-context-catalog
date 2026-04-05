# Contrib Tools

MCC ships with optional built-in tools. Enable them in `settings.local.toml`:

```toml
[default]
contrib = true
```

## `public.request`

Makes HTTP requests. Available to all users.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | str | yes | URL to request |
| `method` | str | no | HTTP method (default: `GET`) |
| `headers` | dict | no | Additional request headers |
| `body` | str | no | Request body |

**Example:**

```
execute("public.request", {"url": "https://api.example.com/data"})
```

---

## `admin.shell`

Executes an arbitrary shell command. Restricted to the `admin` group.

!!! danger
    This tool runs commands with the same privileges as the MCC server process. Only grant it to trusted users.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `command` | str | yes | Shell command to execute |

**Example:**

```
execute("admin.shell", {"command": "df -h"})
```

---

## `admin.reload`

Reloads all tool YAML files without restarting the server. Restricted to the `admin` group.

**Parameters:** none

**Example:**

```
execute("admin.reload")
```
