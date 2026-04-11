## Requirements

### Requirement: Optional transform field
A tool entry MAY specify a `transform` field. The value SHALL be either a shell command string or a list of shell command strings. When a list is provided, entries SHALL be joined with ` | ` to form a single pipeline. The field is optional; omitting it leaves tool output unchanged.

#### Scenario: No transform field
- **WHEN** a tool entry has no `transform` field
- **THEN** the tool output is returned as-is with no postprocessing

#### Scenario: Transform as string
- **WHEN** a tool entry has `transform: "jq -r '.items[]'"`
- **THEN** the tool loads successfully and the single command is used as the pipeline

#### Scenario: Transform as list
- **WHEN** a tool entry has `transform: ["jq -r '.items[]'", "head -c 4000"]`
- **THEN** the tool loads successfully and the pipeline is `jq -r '.items[]' | head -c 4000`

### Requirement: Jinja templating in transform
The `transform` value SHALL be Jinja-templated at call time using the same kwargs available to the main exec command. Template rendering SHALL occur before the transform command is executed.

#### Scenario: Transform uses tool kwargs
- **WHEN** a tool has `transform: "jq -r '.{{ field }}'` and is called with `field=name`
- **THEN** the executed transform command is `jq -r '.name'`

#### Scenario: Transform with no template variables
- **WHEN** a tool has `transform: "head -c 8000"` and is called with any kwargs
- **THEN** the transform command is `head -c 8000` regardless of kwargs

### Requirement: Exec tool transform appended to pipeline
For `exec` and `curl` tools, the rendered transform SHALL be appended to the rendered exec command as a shell pipeline in the same subprocess. The original command SHALL be wrapped in parentheses before appending.

#### Scenario: Curl tool with transform
- **WHEN** a curl tool has `transform: "pup 'article p text{}'"` and is executed
- **THEN** the subprocess runs `(curl -sL -o - '{{ url }}') | pup 'article p text{}'`

#### Scenario: Exec tool with multi-step transform
- **WHEN** an exec tool has `transform: ["jq '.hits'", "head -c 2000"]` and is executed
- **THEN** the subprocess runs `(<exec_cmd>) | jq '.hits' | head -c 2000`

### Requirement: Fn tool transform runs as separate subprocess
For `fn` tools, after the pyrunner subprocess completes successfully, the transform SHALL be executed as a new shell subprocess with the fn's JSON output piped as stdin.

#### Scenario: Fn tool output piped through transform
- **WHEN** an fn tool returns `{"items": ["a", "b"]}` and has `transform: "jq -r '.items[]'"`
- **THEN** the string `{"items": ["a", "b"]}` is piped as stdin to `jq -r '.items[]'`
- **AND** the transform stdout is returned as the tool result

### Requirement: Transform skipped on tool failure
If the original tool call fails (non-zero exit code), the transform SHALL NOT be applied. The error result SHALL be returned unchanged.

#### Scenario: Exec tool fails
- **WHEN** an exec tool exits with a non-zero code and has a `transform` defined
- **THEN** the transform is not executed
- **AND** the `(code, stdout, stderr)` tuple is returned as-is

#### Scenario: Fn tool fails
- **WHEN** a pyrunner subprocess exits with a non-zero code and the tool has a `transform`
- **THEN** the transform is not executed
- **AND** the error result is returned as-is

### Requirement: Transform inherits tool timeout
The transform subprocess SHALL share the tool's configured `timeout`. The timeout applies to the overall execution budget; no separate per-step timeout is tracked.

#### Scenario: Transform respects tool timeout
- **WHEN** a tool has `timeout: 10` and the transform subprocess runs
- **THEN** the transform is subject to the same 10-second timeout as the rest of execution

### Requirement: Transform has no env inheritance
The transform subprocess SHALL NOT inherit the tool's `env` or `env_file` values. The transform runs with the default process environment.

#### Scenario: Tool with env does not pass env to transform
- **WHEN** a tool has `env: {API_KEY: secret}` and a `transform`
- **THEN** the transform subprocess does not have `API_KEY` in its environment
