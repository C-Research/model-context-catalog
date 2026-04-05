# Users & Groups

MCC stores users in Elasticsearch. Manage them with the `mcc user` CLI.

## User model

Each user has:

| Field | Description |
|-------|-------------|
| `username` | Unique identifier (GitHub login in OAuth mode) |
| `email` | Used for identity resolution from tokens |
| `groups` | List of group memberships |
| `tools` | List of explicit tool key grants |

## Managing users

### Add a user

```bash
mcc user add alice --email alice@example.com
```

### List users

```bash
mcc user list
```

### Remove a user

```bash
mcc user remove alice
```

## Managing groups

### Grant group membership

```bash
mcc user grant alice -g engineering
mcc user grant alice -g admin        # full access
```

### Revoke group membership

```bash
mcc user revoke alice -g engineering
```

## Explicit tool grants

Grant a user access to a specific tool without adding them to its group:

```bash
mcc user grant alice -t admin.shell
```

Revoke:

```bash
mcc user revoke alice -t admin.shell
```

## Groups in YAML

Tools declare their required groups in YAML. A user needs membership in at least one of the tool's groups (or an explicit grant) to execute it:

```yaml
groups: [data, engineering]   # members of either group can access
tools:
  - fn: mymodule:run_query
```
