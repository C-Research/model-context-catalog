## ADDED Requirements

### Requirement: Jinja2 template rendering for exec commands
The `exec` field in tool YAML SHALL be rendered as a Jinja2 template at call time. The template receives all validated parameter values as variables. The Jinja environment SHALL use `StrictUndefined` so that referencing an unknown variable raises an error immediately.

#### Scenario: Template renders with provided params
- **WHEN** exec is `"echo {{ message | quote }}"` and `message` is `hello world`
- **THEN** the executed command is `echo 'hello world'`

#### Scenario: Unknown variable raises error
- **WHEN** exec is `"echo {{ typo }}"` and no param named `typo` exists
- **THEN** an `UndefinedError` is raised before the subprocess is executed

### Requirement: quote filter for scalar values
The Jinja environment SHALL provide a `quote` filter that applies `shlex.quote(str(value))` to a scalar value, producing a safely shell-quoted string.

#### Scenario: String with spaces is quoted
- **WHEN** `{{ value | quote }}` is rendered with `value` = `hello world`
- **THEN** the output is `'hello world'`

#### Scenario: String with shell metacharacters is quoted
- **WHEN** `{{ value | quote }}` is rendered with `value` = `foo; rm -rf /`
- **THEN** the output is `'foo; rm -rf /'`

#### Scenario: Simple alphanumeric value is quoted
- **WHEN** `{{ value | quote }}` is rendered with `value` = `foo`
- **THEN** the output is `foo` (shlex.quote passthrough for safe strings)

### Requirement: quote filter for list values
When the `quote` filter is applied to a list, it SHALL `shlex.quote` each element and join with a single space, producing a string suitable for direct shell interpolation.

#### Scenario: List of paths is quoted and joined
- **WHEN** `{{ files | quote }}` is rendered with `files` = `["a.txt", "b c.txt"]`
- **THEN** the output is `a.txt 'b c.txt'`

#### Scenario: Empty list produces empty string
- **WHEN** `{{ files | quote }}` is rendered with `files` = `[]`
- **THEN** the output is an empty string

### Requirement: Conditional template blocks
The Jinja template SHALL support `{% if %}` / `{% else %}` / `{% endif %}` blocks, allowing optional command arguments based on param values.

#### Scenario: Conditional flag included when true
- **WHEN** exec is `"grep {% if recursive %}-r {% endif %}{{ pattern | quote }}"` and `recursive` is `true`
- **THEN** the executed command includes `-r`

#### Scenario: Conditional flag omitted when false
- **WHEN** exec is `"grep {% if recursive %}-r {% endif %}{{ pattern | quote }}"` and `recursive` is `false`
- **THEN** the executed command does not include `-r`

### Requirement: EnvYAML and Jinja coexistence
EnvYAML `${VAR}` substitution SHALL occur at YAML load time, before any Jinja rendering. Jinja rendering SHALL occur at call time. The two mechanisms SHALL not interfere with each other.

#### Scenario: Env var resolved before Jinja renders
- **WHEN** exec is `"cat {{ file | quote }} >> ${LOG_DIR}/out.txt"` and `LOG_DIR=/var/log`
- **THEN** at load time the string becomes `"cat {{ file | quote }} >> /var/log/out.txt"` and at call time Jinja renders the `{{ file | quote }}` portion
