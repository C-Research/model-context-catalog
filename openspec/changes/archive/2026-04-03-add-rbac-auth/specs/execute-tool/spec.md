## ADDED Requirements

### Requirement: RBAC enforcement before dispatch
The `execute` MCP tool SHALL check whether the caller is authorized to execute the requested tool before dispatching. Authorization SHALL be determined by `can_access(user, tool_name, tool_entry)`: returns `True` if the tool's group is `"public"`, or if the user is not `None` and the tool's group is in `user["groups"]`, or if the tool's name is in `user["tools"]`. If the caller is not authorized, `execute` SHALL return `"Unauthorized"` without dispatching the function.

#### Scenario: Public tool accessible without auth
- **WHEN** execute is called for a tool with `group: public` and no bearer token was provided
- **THEN** the tool is dispatched normally

#### Scenario: Authorized user can execute tool in their group
- **WHEN** execute is called by a user whose groups include the tool's group
- **THEN** the tool is dispatched normally

#### Scenario: Authorized user can execute explicitly granted tool
- **WHEN** execute is called by a user who has the tool name in their explicit tools list
- **THEN** the tool is dispatched normally

#### Scenario: Unauthenticated caller blocked from non-public tool
- **WHEN** execute is called with no bearer token for a tool not in the `public` group
- **THEN** execute returns `"Unauthorized"`

#### Scenario: Authenticated user blocked from tool outside their access
- **WHEN** execute is called by a user whose groups and explicit tools do not include the requested tool
- **THEN** execute returns `"Unauthorized"`
