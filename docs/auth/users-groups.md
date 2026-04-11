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
