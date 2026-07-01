## ADDED Requirements

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
