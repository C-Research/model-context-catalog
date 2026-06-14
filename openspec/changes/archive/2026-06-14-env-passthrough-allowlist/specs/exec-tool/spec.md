## ADDED Requirements

### Requirement: env_passthrough accepts a bool or an allowlist
A tool's `env_passthrough` field SHALL accept either a boolean or a list of strings. When it is a list, each entry SHALL be treated as an `fnmatchcase` (case-sensitive) glob pattern matched against the names of the parent process environment variables; matching variables SHALL be included in the subprocess base environment. `false` SHALL include no parent variables beyond the env floor. `true` SHALL include the entire parent environment.

#### Scenario: List allowlist includes only matching parent variables
- **WHEN** a tool sets `env_passthrough: ["AWS_*", "HOME"]` and the parent environment contains `AWS_REGION`, `AWS_SECRET_ACCESS_KEY`, `HOME`, and `GITHUB_TOKEN`
- **THEN** the subprocess environment contains `AWS_REGION`, `AWS_SECRET_ACCESS_KEY`, and `HOME`
- **AND** the subprocess environment does not contain `GITHUB_TOKEN`

#### Scenario: Glob matching is case-sensitive
- **WHEN** a tool sets `env_passthrough: ["PATH"]` and the parent environment contains `PATH` but not `path`
- **THEN** the subprocess environment contains `PATH`
- **AND** a pattern `["path"]` would not match `PATH`

#### Scenario: Empty list behaves like false
- **WHEN** a tool sets `env_passthrough: []`
- **THEN** the subprocess environment contains only the env floor plus any explicitly declared `env`/`env_file` values

#### Scenario: true passes the full parent environment
- **WHEN** a tool sets `env_passthrough: true`
- **THEN** the subprocess environment contains every variable from the parent environment

### Requirement: Configurable env floor always applies
The system SHALL maintain a configurable env floor (`env_floor` in settings) — a list of variable names that are always merged into every subprocess base environment regardless of `env_passthrough`, including when `env_passthrough` is `false`. A floor variable SHALL be included only if it is present in the parent environment. The default floor SHALL be `PATH, HOME, USER, LOGNAME, TMPDIR, LANG, LC_ALL, TZ, TERM, SHELL`.

#### Scenario: Floor present under default-deny
- **WHEN** a tool sets `env_passthrough: false` and the parent environment contains `PATH` and `HOME`
- **THEN** the subprocess environment contains `PATH` and `HOME`

#### Scenario: Floor variable absent from parent is skipped
- **WHEN** a floor lists `TZ` but the parent environment has no `TZ`
- **THEN** the subprocess environment does not define `TZ` (it is not set to an empty value)

#### Scenario: Floor is configurable
- **WHEN** `env_floor` is overridden in settings to `["PATH"]`
- **THEN** a tool with `env_passthrough: false` receives only `PATH` from the parent (plus declared `env`/`env_file`)

#### Scenario: Allowlist and overlays layer on top of the floor
- **WHEN** a tool sets `env_passthrough: ["AWS_*"]`, `env: {EXTRA: "1"}`, and the floor includes `PATH`
- **THEN** the subprocess environment contains `PATH`, the matching `AWS_*` variables, and `EXTRA=1`

### Requirement: Bare exec does not inherit the full parent environment
An exec tool with no `env`, no `env_file`, and `env_passthrough: false` SHALL receive a concrete environment consisting of only the env floor — it SHALL NOT inherit the full parent environment via OS default. The environment builder SHALL always produce a concrete environment dictionary rather than a null value that would cause OS-default inheritance.

#### Scenario: Bare exec sees the floor, not parent secrets
- **WHEN** an exec tool has no env configuration, `env_passthrough: false`, and the parent environment contains `MCC_SECRET=value`
- **THEN** the subprocess environment does not contain `MCC_SECRET`
- **AND** the subprocess environment contains the floor variables present in the parent (e.g. `PATH`)
