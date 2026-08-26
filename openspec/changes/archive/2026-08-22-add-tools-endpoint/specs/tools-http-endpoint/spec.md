## ADDED Requirements

### Requirement: Tools listing endpoint
The server SHALL expose a `GET /tools` HTTP route that lists the tools the caller can access. It SHALL NOT require authentication to respond — a request with no valid API key SHALL still succeed, scoped to public tools only.

#### Scenario: Anonymous request returns only public tools
- **WHEN** a `GET /tools` request arrives with no `X-API-Key` header, no `Authorization` header, or an invalid/expired key
- **THEN** the server responds `200` with only the tools that have no `groups` or `"public"` in `groups` (i.e. `tool.allows(None)` is `True`)

#### Scenario: Authenticated request returns the caller's full accessible set
- **WHEN** a `GET /tools` request arrives with a valid API key (via `X-API-Key` or `Authorization: Bearer`) resolving to a user
- **THEN** the server responds `200` with every tool for which `tool.allows(user)` is `True` — the user's public tools plus any granted via group membership or explicit tool grant

### Requirement: JSON response format (default)
`GET /tools` SHALL default to a JSON response (no `format` query parameter, or `?format=json`) — a JSON array with one object per accessible tool. Each object SHALL contain `key`, `groups`, `params` (each with `name`, `type`, `required`, `default`, `description`, `example`), `return_type`, `description`, and `example`. It SHALL NOT contain any of the tool's internal execution fields (`fn`, `exec`, `curl`, `python`, `cwd`, `env`, `env_file`, `env_passthrough`, `limits`, `transform`).

#### Scenario: Default format is JSON
- **WHEN** a `GET /tools` request arrives with no `format` query parameter
- **THEN** the response is a JSON array of accessible-tool objects with the fields listed above

#### Scenario: Explicit json format
- **WHEN** a `GET /tools?format=json` request arrives
- **THEN** the response is identical in shape to the no-parameter default

#### Scenario: Internal execution fields never appear
- **WHEN** any `GET /tools` JSON response is inspected, for a tool defined with `fn`, `exec`, `curl`, `env`, or any other internal execution field
- **THEN** none of those field names or their values appear anywhere in the response body

#### Scenario: exec tool return type
- **WHEN** an accessible tool is an `exec`-type tool (defined with `exec`, not `fn`)
- **THEN** its JSON object's `return_type` is the literal string `"str | (int, str, str)"`, regardless of any `return_type` declared in its YAML definition

### Requirement: Markdown response format
`GET /tools?format=md` SHALL respond with `Content-Type: text/plain` containing the same per-tool markdown signature blocks used by the `search()` and `describe_tools()` MCP tools (via `ToolModel.signature`), joined for the accessible tool set.

#### Scenario: Markdown format requested
- **WHEN** a `GET /tools?format=md` request arrives
- **THEN** the response `Content-Type` is `text/plain` and the body is the accessible tools' markdown signature blocks joined together

### Requirement: HTML response format
`GET /tools?format=html` SHALL respond with `Content-Type: text/html` containing the markdown response (per the Markdown response format requirement) rendered to HTML.

#### Scenario: HTML format requested
- **WHEN** a `GET /tools?format=html` request arrives
- **THEN** the response `Content-Type` is `text/html` and the body is the markdown tool listing rendered as HTML

### Requirement: Unknown format falls back to JSON
An unrecognized `format` query parameter value SHALL NOT produce an error response. The server SHALL fall back to the default JSON format.

#### Scenario: Unrecognized format value
- **WHEN** a `GET /tools?format=xml` (or any value other than `json`, `md`, `html`) request arrives
- **THEN** the server responds `200` with the same JSON body it would return for `?format=json`
