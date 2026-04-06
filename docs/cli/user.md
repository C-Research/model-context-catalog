# mcc user

Manage users and their permissions.


## `add`

Create a new user.

```bash
mcc user add -u <username> [--email EMAIL] [-g GROUP ...] [-t TOOL ...]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-u`, `--username` | GitHub username (required) |
| `-e`, `--email` | User's email address |
| `-g`, `--group` | Group to grant (repeatable) |
| `-t`, `--tool` | Tool key to grant (repeatable) |

**Example:**

```bash
mcc user add -u alice --email alice@example.com -g engineering
```

---

## `list`

List all users with their groups and tool grants.

```bash
mcc user list
```

---

## `remove`

Delete a user.

```bash
mcc user remove <username>
```

---

## `grant`

Grant a user group membership or an explicit tool permission.

```bash
mcc user grant <username> [-g GROUP ...] [-t TOOL ...]
```

At least one `-g` or `-t` is required. Both flags are repeatable.

**Examples:**

```bash
mcc user grant alice -g engineering        # group membership
mcc user grant alice -g admin              # full admin access
mcc user grant alice -t admin.shell        # specific tool
mcc user grant alice -g data -g ml         # multiple groups at once
```

---

## `revoke`

Remove group membership or tool grants from a user.

```bash
mcc user revoke <username> [-g GROUP ...] [-t TOOL ...]
```

At least one `-g` or `-t` is required. Both flags are repeatable.
