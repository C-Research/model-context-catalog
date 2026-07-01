## ADDED Requirements

### Requirement: Session store
The system SHALL maintain a per-session, per-user context dictionary backed by a
FastMCP `session_state_store`. The store SHALL be Elasticsearch, configured via
`FastMCP(session_state_store=...)` using an `ElasticsearchStore` that reuses the
existing MCC Elasticsearch client wiring (`ELASTICSEARCH_URL`).

The store's index prefix SHALL be `"mcc-ctx"` so the session-state index
(`mcc-ctx-fastmcp_state`) is isolated from the indices MCC uses for users, tools, and
keys, and SHALL NOT clobber them.

The effective storage key SHALL be scoped by both session and user: the context blob
is stored under the state key `{username}:context`, which FastMCP further prefixes with
the session id, yielding `{session_id}:{username}:context`.

#### Scenario: Store backed by Elasticsearch
- **WHEN** the server starts
- **THEN** the FastMCP app is constructed with an Elasticsearch-backed session state store
- **AND** the store reuses the same Elasticsearch connection settings as the users/tools indices

#### Scenario: Session index does not collide with MCC indices
- **WHEN** the session store is created with prefix `mcc-ctx`
- **THEN** it writes only to an index derived from that prefix (e.g. `mcc-ctx-fastmcp_state`)
- **AND** the `mcc-users`, `mcc-tools`, and `mcc-keys` indices are untouched

#### Scenario: Two sessions of the same user are isolated
- **WHEN** user `alice` sets a context var in session A
- **THEN** a `get_session` for that var in session B (also `alice`) returns `null`

#### Scenario: Two users never share a bucket
- **WHEN** session ids collide but the authenticated usernames differ
- **THEN** neither user can read the other's context vars

### Requirement: Anonymous scoping
Anonymous (unauthenticated) callers SHALL be supported. When no user is authenticated,
the username component of the scope key SHALL be `anonymous`, and isolation SHALL rely
on the session id.

#### Scenario: Anonymous caller stores and reads a var
- **WHEN** an anonymous caller in session X calls `set_session("note", "hi")` then `get_session("note")`
- **THEN** it returns `"hi"`

#### Scenario: Two anonymous sessions are isolated
- **WHEN** anonymous session X sets `note` and anonymous session Y reads `note`
- **THEN** session Y receives `null`

### Requirement: Reserved identity keys
The context dictionary SHALL always carry the reserved keys `user`, `email`, `groups`,
and `tools`, populated from the authenticated user. `set_session` SHALL refuse to write
any reserved key.

#### Scenario: Identity present in context
- **WHEN** authenticated user `alice` (groups `[admin]`) assembles her context
- **THEN** the dict contains `user="alice"` and `groups=["admin"]`

#### Scenario: set() rejects a reserved key
- **WHEN** a caller invokes `set_session("user", "admin")`
- **THEN** the call is rejected and the stored identity is unchanged

### Requirement: set_session tool
The system SHALL expose an MCP tool `set_session(name, value)` that writes one entry
into the caller's context dictionary. `name` SHALL match `^[a-z_][a-z0-9_]*$`. `value`
MAY be any JSON-serializable type and SHALL be stored with its type preserved.

#### Scenario: Set a scalar
- **WHEN** `set_session("budget", 1000)` is called
- **THEN** the context dict has `budget=1000` (stored as an integer)

#### Scenario: Set a complex value
- **WHEN** `set_session("filters", {"q": "x"})` is called
- **THEN** the context dict has `filters={"q": "x"}` (stored as an object)

#### Scenario: Invalid name rejected
- **WHEN** `set_session("My Key", 1)` is called (contains space / uppercase)
- **THEN** the call is rejected without writing

### Requirement: get_session tool
The system SHALL expose an MCP tool `get_session(name)` that returns one entry from
the caller's context dictionary, JSON-encoded so the value's type is unambiguous in
the textual result. When the name is not set it SHALL return the JSON literal `null`.

#### Scenario: Get an existing var
- **WHEN** `budget=1000` is set and `get_session("budget")` is called
- **THEN** it returns the JSON string `1000` (decoding to the integer `1000`)

#### Scenario: Get a missing var
- **WHEN** `get_session("nope")` is called and `nope` was never set
- **THEN** it returns the JSON literal `null`

#### Scenario: Get a reserved identity key
- **WHEN** authenticated user `alice` calls `get_session("user")`
- **THEN** it returns the JSON string `"alice"`

### Requirement: fn tools receive context as a JSON blob
For `fn:` (Python) tools, the full context dictionary SHALL be passed to the subprocess
as a single environment variable `MCC_CTX` containing the JSON-encoded dict. exec tools
SHALL NOT receive `MCC_CTX`.

#### Scenario: MCC_CTX present for fn tools
- **WHEN** an `fn:` tool runs for authenticated user `alice`
- **THEN** the subprocess environment contains `MCC_CTX` whose JSON decodes to a dict including `user="alice"`

#### Scenario: MCC_CTX absent for exec tools
- **WHEN** an `exec:` tool runs
- **THEN** the subprocess environment does NOT contain a `MCC_CTX` variable

### Requirement: context kwarg injection for fn tools
`pyrunner` SHALL parse `MCC_CTX` and, when the resolved callable declares a parameter
named `context`, SHALL pass the parsed dict as that keyword argument. When the callable
does not declare `context`, no injection occurs.

The injected `context` parameter SHALL be shadowed: it MUST be excluded from the tool's
visible signature so it never appears in the LLM-facing schema and is never elicited.

#### Scenario: Callable with context param receives the dict
- **WHEN** a callable `def f(x: int, context: dict)` is invoked as a tool
- **THEN** `context` is populated from `MCC_CTX` and is not part of the tool's advertised params

#### Scenario: Callable without context param is unaffected
- **WHEN** a callable `def g(x: int)` is invoked as a tool
- **THEN** no `context` argument is passed and the call succeeds

#### Scenario: context param hidden from signature
- **WHEN** a tool whose callable declares `context` is described via search/whoami
- **THEN** `context` does not appear among its visible parameters

### Requirement: exec tools receive context expanded into env vars
For `exec:` (shell) tools, each entry of the context dictionary SHALL be expanded into
its own environment variable named `MCC_CTX_<NAME>`, where `<NAME>` is the uppercased
entry name. Scalar values (str/int/float/bool) SHALL be written as their raw string
form; complex values (dict/list) SHALL be JSON-encoded into the string.

#### Scenario: Identity expanded for exec tools
- **WHEN** an `exec:` tool runs for `alice` in groups `[admin, osint]`
- **THEN** the environment contains `MCC_CTX_USER=alice` and `MCC_CTX_GROUPS` listing her groups

#### Scenario: Scalar var expanded raw
- **WHEN** `budget=1000` is in context and an `exec:` tool runs
- **THEN** the environment contains `MCC_CTX_BUDGET=1000`

#### Scenario: Complex var expanded as JSON
- **WHEN** `filters={"q": "x"}` is in context and an `exec:` tool runs
- **THEN** the environment contains `MCC_CTX_FILTERS` set to the JSON string `{"q": "x"}`

### Requirement: Identity cannot be spoofed via tool env
Injected context (both `MCC_CTX` and the `MCC_CTX_<NAME>` expansion) SHALL be merged
last when building the subprocess environment, so a tool definition's own `env:` cannot
override the caller's identity entries.

#### Scenario: Tool env cannot override identity
- **WHEN** a tool declares `env: { MCC_CTX_USER: attacker }` and `alice` calls it
- **THEN** the subprocess sees `MCC_CTX_USER=alice`

### Requirement: Removal of legacy identity env vars
The system SHALL remove the previous standalone identity-propagation path that injected
only the discrete identity vars (`MCC_CTX_USER`, `MCC_CTX_EMAIL`, `MCC_CTX_GROUPS`,
`MCC_CTX_TOOLS`). Those names SHALL now be produced solely as expanded entries of the
unified context dictionary for exec tools.

#### Scenario: Identity flows through the unified dict
- **WHEN** identity is propagated to a tool
- **THEN** it originates from the context dictionary (blob for fn, expansion for exec), not from a separate identity-only code path

### Requirement: Authoritative identity remains request-scoped
The system SHALL continue to resolve authoritative caller identity from the
request-scoped `current_user_var` (set by `AuthMiddleware` from the validated auth
token), NOT from the stored context blob. On every request the reserved identity keys
SHALL be re-derived from `current_user_var` and merged over the stored variables so
that identity always wins over any stored value. The stored blob SHALL be treated as a
read snapshot for tools and SHALL NOT be authoritative for identity or RBAC.

#### Scenario: RBAC reads the request identity, not the blob
- **WHEN** a tool's access is evaluated for the caller
- **THEN** `tool.allows(user)` uses the `UserModel` from `current_user_var`, not values from the stored context

#### Scenario: Stored identity cannot override the request identity
- **WHEN** a stored context blob contains `user="admin"` but the request resolves to `alice`
- **THEN** the assembled context and all propagation report `user="alice"`

### Requirement: fn-tool context write-back
After an `fn` tool executes, the system SHALL propagate the tool's (possibly
mutated) `context` dict back into the caller's session state as a **full replace**
of the caller's non-identity vars. This SHALL NOT require any change to the tool's
signature: the tool continues to receive and mutate the injected `context` kwarg.

The write-back SHALL be carried on the pyrunner→server stdout channel as a
2-element envelope `[result, context]`. Element 0 (the tool result) SHALL be
returned to the LLM exactly as before. Element 1 SHALL be the context dict to
write back, or `null` when the tool declared no `context` parameter.

`null` in the context slot SHALL mean "do not modify session state". An empty
object `{}` SHALL mean "replace with no non-identity vars" (i.e. clear them).

Only in-place mutation of the injected dict SHALL propagate; rebinding the local
name inside the tool SHALL NOT be observed.

#### Scenario: Tool writes a new var read by a later tool
- **WHEN** an fn tool with a `context` param sets `context["cursor"] = 6` and returns
- **THEN** the value written to session state includes `cursor = 6`
- **AND** a subsequent tool execution in the same session receives `cursor = 6` in its injected context

#### Scenario: Tool result returned unchanged
- **WHEN** an fn tool returns a result and mutates its context
- **THEN** the LLM receives the original result, not the `[result, context]` envelope

#### Scenario: No context param does not touch state
- **WHEN** an fn tool that declares no `context` param executes
- **THEN** stdout carries `[result, null]`
- **AND** the caller's stored session vars are unchanged

#### Scenario: Empty context clears non-identity vars
- **WHEN** a tool receives context with stored vars and returns it as `{}` (all non-identity keys deleted)
- **THEN** the caller's non-identity session vars are cleared
- **AND** the reserved identity keys remain present on the next read

#### Scenario: Result that is itself a list is not confused with the envelope
- **WHEN** an fn tool returns a list value
- **THEN** the server unwraps the outer 2-element envelope first and returns the list as the result

### Requirement: Write-back enforces reserved identity keys
The context write-back SHALL NOT allow a tool to set, alter, or delete the reserved
identity keys (`user`, `email`, `groups`, `tools`). Before writing, the system SHALL
strip all reserved keys from the returned dict and re-derive them from the
authenticated user (identity wins). Reserved keys present in the returned dict SHALL
be stripped silently (not rejected), because they are injected into every context a
tool receives.

#### Scenario: Tool cannot spoof identity via write-back
- **WHEN** an fn tool sets `context["user"] = "admin"` and returns
- **THEN** the stored identity re-derives `user` from the authenticated caller
- **AND** the stored `user` is NOT `"admin"`

#### Scenario: Tool cannot delete identity via write-back
- **WHEN** an fn tool deletes `context["groups"]` and returns
- **THEN** the next context read still contains `groups` derived from the authenticated user

### Requirement: Write-back rejects invalid keys
The system SHALL reject the entire context write-back, and log it, when the returned
context contains a non-reserved key that does not match the slug pattern
`^[a-z_][a-z0-9_]*$`. A rejected write-back SHALL NOT fail the tool call: the tool's
result SHALL still be returned to the LLM, and the stored session vars SHALL be left
unchanged.

#### Scenario: Invalid key rejects the whole write-back
- **WHEN** an fn tool sets `context["bad key"] = 1` (space is not a valid slug) and returns a result
- **THEN** the write-back is rejected and logged
- **AND** none of that tool's context changes are persisted
- **AND** the tool's result is still returned to the LLM

### Requirement: exec tools are read-only
`exec` (shell) tools SHALL NOT participate in context write-back. Their context
propagation SHALL remain one-way (`MCC_CTX_<NAME>` env vars in), consistent with the
fact that a subprocess cannot mutate its parent's environment.

#### Scenario: Shell tool cannot write session state
- **WHEN** an exec tool runs and modifies its `MCC_CTX_<NAME>` env vars
- **THEN** the caller's stored session vars are unchanged
