## MODIFIED Requirements

### Requirement: Interpolation mode (default)
When `stdin` is false (the default), the system SHALL render the `exec` field as a Jinja2 template with all validated parameters available as template variables. Parameter quoting is the template author's responsibility via the `| quote` filter. The system SHALL NOT apply any automatic quoting.

#### Scenario: Params rendered into command via Jinja
- **WHEN** exec is `"grep -rn {{ pattern | quote }} {{ path | quote }}"` and params are `pattern=TODO, path=src/`
- **THEN** the executed command is `grep -rn TODO src/`

#### Scenario: Missing required param fails before execution
- **WHEN** exec is `"echo {{ msg | quote }}"` but param `msg` is not provided and is required
- **THEN** validation fails before the command is executed
