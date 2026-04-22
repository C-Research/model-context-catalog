---
icon: lucide/archive
---

# Archive Tools

List, extract, and create zip and tar archives. Restricted to the `admin` and `archive` groups.

---

## `admin.archive.list`

List the contents of a zip or tar archive.

| Param | Type | Required |
|-------|------|----------|
| `path` | str | yes |

Returns a list of entry names.

---

## `admin.archive.extract`

Extract a zip or tar archive to a destination directory.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | str | yes | Path to the archive |
| `dest` | str | yes | Directory to extract into |

Returns a list of extracted paths.

---

## `admin.archive.create`

Create a zip or tar.gz archive from a list of file paths. The format is inferred from the destination file extension (`.zip` or `.tar.gz`).

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `dest` | str | yes | Output archive path (`.zip` or `.tar.gz`) |
| `files` | list | yes | List of file paths to include |

Returns the destination path.
