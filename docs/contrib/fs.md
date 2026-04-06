# Filesystem Tools

Read and write files on the server's filesystem. Split into two sub-groups for fine-grained access control.

## Groups

- **`read`** (also `admin.fs`) — `read_file`, `stat`, `list_dir`
- **`write`** (also `admin.fs`) — `move`, `write_file`

Grant read-only access:

```bash
mcc user add alice --groups read
```

Grant read and write:

```bash
mcc user add bob --groups read,write
```

---

## `read.stat`

Return metadata for a path.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | str | yes | Path to inspect |

Returns a dict with `exists`, `is_file`, `is_dir`, `size`, `mtime`, `atime`, `ctime`. If the path doesn't exist, returns `{"exists": false, "path": "..."}`.

---

## `read.list_dir`

List entries in a directory matching a glob pattern.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | str | yes | Directory path |
| `pattern` | str | no | Glob pattern (default: `*`) |
| `recursive` | bool | no | Recurse into subdirectories (default: `false`) |

Returns a list of `Path` objects.

---

## `read.read_file`

Read the contents of a file.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | str | yes | File path to read |
| `mode` | str | no | File mode (default: `r`) |

Returns the file contents as a string.

---

## `write.write_file`

Write content to a file, creating parent directories as needed.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | str | yes | File path to write |
| `content` | str | yes | Content to write |
| `mode` | str | no | File mode — `w` to overwrite (default), `a` to append |

---

## `write.move`

Move or rename a file or directory.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | str | yes | Source path |
| `destination` | str | yes | Destination path |

Returns the destination path as a string. Raises `FileNotFoundError` if the source doesn't exist.
