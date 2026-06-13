---
icon: lucide/users
---

# Users & Groups

MCC stores users in Elasticsearch. These operations are available via the `mcc user` CLI or from an LLM by calling `execute` with the tool key shown below.

## User model

Each user has:

| Field | Description |
|-------|-------------|
| `username` | Unique identifier  |
| `email` | Used for identity resolution from tokens |
| `groups` | List of group memberships |
| `tools` | List of explicit tool key grants |

## Managing users

### Add a user

tool key: `admin.auth.users.create_user`

```bash
mcc user add alice --email alice@example.com
```

### List users

tool key: `admin.auth.users.list_users`

```bash
mcc user list
```

### Remove a user

tool key: `admin.auth.users.delete_user`

```bash
mcc user remove alice
```

## Managing groups

### Grant group membership

tool key: `admin.auth.groups.add_group`

```bash
mcc user grant alice -g engineering
mcc user grant alice -g admin        # full access
```

### Revoke group membership

tool key: `admin.auth.groups.remove_group`

```bash
mcc user revoke alice -g engineering
```

## Explicit tool grants

Grant a user access to a specific tool without adding them to its group:

tool key: `admin.auth.tools.add_tool` /  `admin.auth.tools.remove_tool`

```bash
mcc user grant alice -t admin.shell
mcc user revoke alice -t admin.shell
```

## API keys

When the [`api_key`](backends.md#api-key-api_key) backend is active, each user
may hold a single API key. A key is a bearer credential that resolves to its
user — it grants exactly that user's tools/groups and carries no scope of its
own. Model a script or agent as its own narrow user, then mint a key for it.

### Mint a key

```bash
mcc user key add ci-bot                 # default TTL (~90 days)
mcc user key add ci-bot --expires 30    # expires in 30 days
mcc user key add ci-bot --expires never # never expires
```

Verifies the user exists, replaces any existing key, and prints the raw key
**exactly once** — copy it immediately, it cannot be recovered. Without
`--expires` the key uses the configured `api_key.default_ttl_days` (~90 days);
pass a positive number of days, or `never` for a non-expiring key.

### List keys

```bash
mcc user key list
```

Shows each key's username, prefix, and created/expiry timestamps only — never
the hash or raw key.

### Revoke a key

```bash
mcc user key revoke ci-bot
```

Deletes the key record. Revocation is instant — the very next request with that
key is rejected. Narrowing the bound user's grants likewise takes effect
immediately, without re-minting.

## Reserved groups

| Group | Behavior |
|-------|----------|
| `public` | Any user (including unauthenticated) can access tools in this group |
| `admin` | Full access to all tools regardless of their declared groups |

Users in `admin` bypass all group checks — they can execute any tool in the catalog.

## Groups in YAML

Tools declare their required groups in YAML. A user needs membership in at least one of the tool's groups (or an explicit grant) to execute it:

```yaml
groups: [data, engineering]   # members of either group can access
tools:
  - fn: mymodule:run_query
```
