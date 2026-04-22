---
icon: lucide/wrench
---

# Utils

General-purpose utility tools covering HTTP, filesystem, shell, text processing, time, and archives. Disabled by default.

## Enabling utils

Load the bundled settings file via `MCC_SETTINGS_FILES`:

```bash
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml
```

Or add individual tool files to `settings.local.yaml`:

```yaml
tools:
  - toolsets/contrib/http.yaml
  - toolsets/contrib/fs.yaml
  # ... add only what you need
```

## Categories

| Category | Groups | Description |
|----------|--------|-------------|
| [HTTP](http.md) | `public.http`, `admin.http` | Make HTTP requests |
| [Filesystem](fs.md) | `read`, `write` (under `admin.fs`) | Read, write, list, move files |
| [System](system.md) | `admin.system` | Shell, Python, env vars, platform info |
| [Text](text.md) | `public.text` | Encoding, hashing, diff, regex |
| [Time](time.md) | `public.time` | Current time, formatting, date arithmetic |
| [Archive](archive.md) | `admin.archive` | List, extract, create zip/tar archives |

## Groups and access

Each category uses its own groups for fine-grained access control. For example, grant a user read-only filesystem access without system access:

```bash
mcc user grant alice --group read --group fs
```
