# mcc user

Manage users in the MCC user store.

## Commands

### `mcc user add`

Create a new user.

```bash
mcc user add <username> [--email EMAIL]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `username` | Unique username (typically GitHub login) |
| `--email` | User's email address |

**Example:**

```bash
mcc user add alice --email alice@example.com
```

---

### `mcc user list`

List all users with their groups and tool grants.

```bash
mcc user list
```

---

### `mcc user remove`

Delete a user.

```bash
mcc user remove <username>
```

---

### `mcc user grant`

Grant a user group membership or an explicit tool permission.

```bash
mcc user grant <username> -g <group>
mcc user grant <username> -t <tool-key>
```

**Examples:**

```bash
mcc user grant alice -g engineering        # group membership
mcc user grant alice -g admin              # full admin access
mcc user grant alice -t admin.shell        # specific tool
```

---

### `mcc user revoke`

Remove a group membership or tool grant from a user.

```bash
mcc user revoke <username> -g <group>
mcc user revoke <username> -t <tool-key>
```
