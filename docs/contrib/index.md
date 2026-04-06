# Contrib Tools

MCC ships with optional built-in tools covering HTTP, filesystem, shell, text processing, time, and archives. They're disabled by default.

## Enabling contrib tools

Add to `settings.local.yaml`:

```yaml
contrib: true
```

Or set the environment variable:

```bash
MCC_CONTRIB=true
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
