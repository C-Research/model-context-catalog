---
icon: lucide/lock
---

# Auth & Permissions Overview

MCC uses a layered permission model. Every `execute()` call checks whether the requesting user is allowed to run the target tool.

## Permission hierarchy

Checks run in order — first match wins:

```
1. tool.groups contains "public"  →  always allowed
2. user is in "admin" group       →  always allowed
3. tool.groups ∩ user.groups ≠ ∅  →  allowed (group overlap)
4. tool.key in user.tools         →  allowed (explicit grant)
5. otherwise                      →  denied
```

## Data flow

```
MCP request (with token)
  └─ auth backend resolves token → identity claims
  └─ get_current_user() resolves claims → UserModel from DB
  └─ can_access(user, tool) runs the hierarchy above
```

## Public tools

Any tool in the `public` group is accessible to all users, including unauthenticated requests:

```yaml
groups: [public]
tools:
  - fn: mymodule:open_tool
```

## Admin access

Users in the `admin` group can execute any tool regardless of its groups. Grant admin:

```bash
mcc user grant alice -g admin
```

## Next steps

- [Users & Groups](users-groups.md) — managing users via CLI
- [Auth Backends](backends.md) — GitHub OAuth, PAT, and dev mode
