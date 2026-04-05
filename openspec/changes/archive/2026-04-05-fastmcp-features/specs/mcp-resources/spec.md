## ADDED Requirements

### Requirement: Tool catalog resource
The server SHALL expose a `catalog://tools` MCP resource that returns the signatures of all tools the current user can access.

#### Scenario: Authenticated user reads catalog
- **WHEN** an authenticated user with group "admin" reads `catalog://tools`
- **THEN** the resource returns markdown signatures of all tools accessible to that user

#### Scenario: Anonymous user reads catalog
- **WHEN** an unauthenticated user reads `catalog://tools`
- **THEN** the resource returns only tools in the "public" group

### Requirement: Single tool resource template
The server SHALL expose a `catalog://tools/{key}` MCP resource template that returns the signature of a single tool by its key.

#### Scenario: Accessible tool
- **WHEN** a user reads `catalog://tools/public.list_tools`
- **THEN** the resource returns that tool's full signature markdown

#### Scenario: Inaccessible tool
- **WHEN** a user without the required group reads `catalog://tools/admin.shell`
- **THEN** the resource returns a "not found" message

#### Scenario: Unknown tool key
- **WHEN** a user reads `catalog://tools/nonexistent`
- **THEN** the resource returns a "not found" message

### Requirement: User identity resource
The server SHALL expose a `user://me` MCP resource that returns the current user's identity, groups, and tool grants.

#### Scenario: Authenticated user
- **WHEN** an authenticated user reads `user://me`
- **THEN** the resource returns username, email, groups, and granted tools

#### Scenario: Anonymous user
- **WHEN** an unauthenticated user reads `user://me`
- **THEN** the resource returns an anonymous identity with no groups or grants
