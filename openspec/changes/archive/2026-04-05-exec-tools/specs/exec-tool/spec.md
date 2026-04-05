## ADDED Requirements

### Requirement: Exec tool definition
A tool entry MAY specify `exec: <command>` instead of `fn:`. The `exec` field SHALL be a shell command string. Exactly one of `fn` or `exec` MUST be present on each tool entry.

#### Scenario: Valid exec tool loads
- **WHEN** a tool entry has `exec: "node tool.js"` and no `fn` field
- **THEN** the tool loads successfully and is registered in the catalog

#### Scenario: Both fn and exec raises error
- **WHEN** a tool entry specifies both `fn` and `exec`
- **THEN** loader raises a `ValueError` at load time

#### Scenario: Neither fn nor exec raises error
- **WHEN** a tool entry specifies neither `fn` nor `exec`
- **THEN** loader raises a `ValueError` at load time

### Requirement: Exec tool params from YAML
Exec tools SHALL require params to be declared in YAML. There is no callable to introspect, so params MUST be explicitly defined.

#### Scenario: Exec tool with declared params
- **WHEN** an exec tool declares params in YAML
- **THEN** the params are used for validation at call time

#### Scenario: Exec tool with no params
- **WHEN** an exec tool declares no params
- **THEN** the tool accepts no parameters and the command runs as-is

### Requirement: Interpolation mode (default)
When `stdin` is false (the default), the system SHALL interpolate validated parameters into the `exec` command string using Python `str.format(**params)` before executing.

#### Scenario: Params interpolated into command
- **WHEN** exec is `"grep -rn {pattern} {path}"` and params are `pattern=TODO, path=src/`
- **THEN** the executed command is `grep -rn TODO src/`

#### Scenario: Missing interpolation placeholder raises error
- **WHEN** exec is `"echo {msg}"` but param `msg` is not provided and is required
- **THEN** validation fails before the command is executed

### Requirement: Stdin mode
When `stdin` is true, the system SHALL send all validated parameters as a JSON object on stdin. The command string SHALL NOT be interpolated.

#### Scenario: Params sent as JSON on stdin
- **WHEN** exec is `"node tool.js"`, stdin is true, and params are `file=app.py`
- **THEN** the process receives `{"file": "app.py"}` on stdin

### Requirement: Return signature
All exec tools SHALL return a tuple of `(returncode: int, stdout: str, stderr: str)`.

#### Scenario: Successful command
- **WHEN** an exec tool command exits with code 0
- **THEN** the tool returns `(0, <stdout>, <stderr>)`

#### Scenario: Failed command
- **WHEN** an exec tool command exits with code 1
- **THEN** the tool returns `(1, <stdout>, <stderr>)` without raising an exception

### Requirement: Timeout
Exec tools MAY specify a `timeout: int` in seconds. When set, the system SHALL enforce the timeout via `asyncio.wait_for`. On timeout, the process SHALL be killed.

#### Scenario: Command completes within timeout
- **WHEN** timeout is 5 and the command completes in 1 second
- **THEN** the tool returns the normal `(returncode, stdout, stderr)` tuple

#### Scenario: Command exceeds timeout
- **WHEN** timeout is 1 and the command takes 10 seconds
- **THEN** the process is killed and the tool returns `(-1, "", "timeout after 1s")`

#### Scenario: No timeout set
- **WHEN** timeout is not specified
- **THEN** the command runs with no time limit

### Requirement: Resource limits
Exec tools MAY specify a `limits` dict with optional keys `mem_mb` (int), `cpu_sec` (int), `fsize_mb` (int), and `nofile` (int). When set on a unix platform, the system SHALL enforce these limits via `preexec_fn` using the `resource` module, passed as a kwarg to `asyncio.create_subprocess_shell`. On non-unix platforms, limits SHALL be silently ignored.

#### Scenario: Memory limit enforced
- **WHEN** an exec tool specifies `limits: {mem_mb: 256}` on a unix platform
- **THEN** the subprocess is started with `RLIMIT_AS` set to 256 MB

#### Scenario: CPU time limit enforced
- **WHEN** an exec tool specifies `limits: {cpu_sec: 10}` on a unix platform
- **THEN** the subprocess is started with `RLIMIT_CPU` set to 10 seconds

#### Scenario: File size limit enforced
- **WHEN** an exec tool specifies `limits: {fsize_mb: 50}` on a unix platform
- **THEN** the subprocess is started with `RLIMIT_FSIZE` set to 50 MB

#### Scenario: Open file descriptor limit enforced
- **WHEN** an exec tool specifies `limits: {nofile: 128}` on a unix platform
- **THEN** the subprocess is started with `RLIMIT_NOFILE` set to 128

#### Scenario: Process exceeds limit
- **WHEN** a subprocess exceeds a resource limit
- **THEN** the OS kills the process and the tool returns a nonzero exit code

#### Scenario: Limits on non-unix platform
- **WHEN** limits are specified but the platform is not unix
- **THEN** limits are silently ignored and the command runs without resource constraints

#### Scenario: No limits specified
- **WHEN** no limits dict is present
- **THEN** the command runs without resource constraints

### Requirement: Exec tool name inference
When `name` is not specified for an exec tool, the system SHALL default to the basename of the command (first token of the `exec` string).

#### Scenario: Name inferred from command
- **WHEN** exec is `"node tools/lint.js"` and no name is specified
- **THEN** the tool name defaults to `node`

#### Scenario: Explicit name overrides
- **WHEN** exec is `"node tools/lint.js"` and name is `lint`
- **THEN** the tool name is `lint`
