---
icon: lucide/cpu
---

# System Tools

Shell execution, Python evaluation, environment variable management, and platform info. All restricted to the `admin` and `system` groups.

!!! danger "Makes system calls"
    These tools run with the same privileges as the MCC server process. Only grant them to trusted users.

---

## `admin.system.bash`

Run an arbitrary bash command.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | str | yes | Shell command to execute |

Returns `(returncode, stdout, stderr)`.

```
execute("admin.system.bash", {"command": "df -h"})
```

---

## `admin.system.python`

Execute arbitrary Python code. Receives parameters as JSON on stdin.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | str | yes | Python source code to execute |

Returns `(returncode, stdout, stderr)`. The source runs in a subprocess via `exec()` with full access to the Python environment.

```
execute("admin.system.python", {"source": "print(1 + 1)"})
```

---

## `admin.system.platform`

Return OS, Python version, CPU architecture, and hostname. No parameters.

---

## `admin.system.pythonpath`

Return the current `sys.path`. No parameters.

---

## `admin.system.get_env`

Get one or more environment variables.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `keys` | list | yes | List of variable names to look up |

Returns a dict of `{name: value}`. Unset variables have `null` values.

---

## `admin.system.list_env`

Return all environment variable names. No parameters.

---

## `admin.system.set_env`

Set an environment variable for the current process.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | str | yes | Variable name |
| `value` | str | yes | Value to set |

---

## `admin.system.man`

Look up a command's man page.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `cmd` | str | yes | Command name to look up |

```
execute("admin.system.man", {"cmd": "curl"})
```

---

## `admin.system.uname`

Return OS and architecture information (`uname -a`). No parameters.
