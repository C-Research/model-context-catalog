---
icon: lucide/package
---

# Contrib Tools

MCC ships with optional built-in tools covering HTTP, filesystem, shell, text processing, time, and archives. They're disabled by default.

## Enabling contrib tools

Contrib tools live in `toolsets/contrib/`. Load them by pointing `MCC_SETTINGS_FILES` at the bundled settings file:

```bash
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml
```

Or add the tools directly to your `settings.local.yaml`:

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

Each contrib category uses its own groups, so you can grant fine-grained access. For example, grant a user read-only filesystem access without system access:

```bash
mcc user grant alice --group read --group fs
```

See [Users & Groups](../auth/users-groups.md) for full details.
