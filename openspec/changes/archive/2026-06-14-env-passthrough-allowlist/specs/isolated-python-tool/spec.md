## ADDED Requirements

### Requirement: fn introspection and execution honor env_passthrough consistently
The load-time introspection subprocess for an fn tool SHALL use the same `env_passthrough` setting as the call-time execution subprocess. The introspection subprocess SHALL NOT inherit the full parent environment when `env_passthrough` is `false` or a list. The pyrunner environment builder SHALL NOT fall back to the full parent environment; it SHALL build from the env floor, the `env_passthrough` mode, and declared `env`/`env_file`, then apply its required additions (`PYTHONPATH` prepended with the tool cwd, `MCC_SKIP_AUTOLOAD`).

#### Scenario: Introspection does not leak parent secrets
- **WHEN** an fn tool is loaded with `env_passthrough: false` and the parent environment contains `MCC_SECRET=value`
- **THEN** the introspection subprocess environment does not contain `MCC_SECRET`

#### Scenario: Introspect env matches call env
- **WHEN** an fn tool sets `env_passthrough: ["FOO_*"]`
- **THEN** both the introspection subprocess and the call-time subprocess receive the same `FOO_*` variables from the parent (plus floor, `PYTHONPATH`, and `MCC_SKIP_AUTOLOAD`)

#### Scenario: Floor and PYTHONPATH keep imports working under default-deny
- **WHEN** an fn tool with `env_passthrough: false` and no env configuration runs
- **THEN** the subprocess environment contains the env floor, `MCC_SKIP_AUTOLOAD`, and `PYTHONPATH` with the tool cwd prepended
- **AND** the subprocess environment does not contain non-floor parent variables such as `MCC_SECRET`

#### Scenario: Allowlisted variable available at import time
- **WHEN** an fn tool sets `env_passthrough: ["VIRTUAL_ENV"]` and the parent has `VIRTUAL_ENV` set
- **THEN** the introspection subprocess receives `VIRTUAL_ENV`
