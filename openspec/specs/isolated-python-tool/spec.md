## ADDED Requirements

### Requirement: python field on fn tools
A fn-based tool entry MAY specify `python: <interpreter>` where the value is either a full path or a name resolvable via `shutil.which`. The `python` field SHALL only be valid on tools that also specify `fn`; it MUST NOT be used with `exec`.

#### Scenario: python field with full path
- **WHEN** a tool entry specifies `fn: mymodule.fn` and `python: /opt/venv/bin/python3`
- **THEN** the tool loads successfully and uses that interpreter for introspection and execution

#### Scenario: python field with name on PATH
- **WHEN** a tool entry specifies `python: python3.10` and `python3.10` is resolvable via shutil.which
- **THEN** the tool loads successfully

#### Scenario: python field with unknown interpreter
- **WHEN** a tool entry specifies `python: /nonexistent/python`
- **THEN** loader raises a `ValueError` at load time with a message indicating the interpreter was not found

#### Scenario: python field with exec tool
- **WHEN** a tool entry specifies both `exec` and `python`
- **THEN** loader raises a `ValueError` at load time

### Requirement: Load-time introspection via subprocess
When `python` is set and `params` are not explicitly declared in YAML, the system SHALL introspect the function signature by spawning `python pyrunner.py introspect <fn_path>` synchronously at load time. The stdout SHALL be a JSON array of parameter descriptors used to populate `ToolModel.params`.

#### Scenario: Params auto-populated from target interpreter
- **WHEN** a fn tool specifies `python:` and no explicit `params:` in YAML
- **THEN** params are populated by running pyrunner introspect in the target interpreter

#### Scenario: Explicit params skip introspection
- **WHEN** a fn tool specifies `python:` and also declares `params:` in YAML
- **THEN** params are used as declared without spawning a subprocess

#### Scenario: Module not importable in target env
- **WHEN** pyrunner introspect fails because the module is not installed in the target env
- **THEN** loader raises an error at load time with the subprocess stderr included

### Requirement: Call-time execution via subprocess
When `python` is set, the system SHALL execute the tool by spawning `python pyrunner.py exec <fn_path>` asynchronously. Validated kwargs SHALL be sent as a JSON object on stdin. The return value SHALL be the subprocess stdout as a string on success.

#### Scenario: Tool executes in target interpreter
- **WHEN** a fn tool with `python:` is called with valid kwargs
- **THEN** the function runs in the specified interpreter and stdout is returned as a string

#### Scenario: Kwargs passed as JSON on stdin
- **WHEN** a fn tool with `python:` is called with kwargs `{x: 1, y: "hello"}`
- **THEN** the subprocess receives `{"x": 1, "y": "hello"}` on stdin

#### Scenario: Async fn handled transparently
- **WHEN** the target function is an async def
- **THEN** pyrunner wraps it in asyncio.run() and returns the result normally

### Requirement: Error envelope matches exec tools
fn tools with `python:` SHALL use the same return envelope as exec tools: return the stdout string on success (exit code 0), and return `(code: int, stdout: str, stderr: str)` on failure (nonzero exit code). The shared communicate-and-result logic SHALL be extracted into a common private helper in `mcc/exec.py` used by both `make_exec_callable` and `make_py_callable`.

#### Scenario: Successful call returns stdout string
- **WHEN** the subprocess exits with code 0
- **THEN** the tool returns the stdout string directly

#### Scenario: Failed call returns tuple
- **WHEN** the subprocess exits with nonzero code (e.g. unhandled exception in the fn)
- **THEN** the tool returns `(code, stdout, stderr)` without raising


### Requirement: Resource limits
fn tools with `python:` MAY specify a `limits` dict with the same keys as exec tools (`mem_mb`, `cpu_sec`, `fsize_mb`, `nofile`). When set on a unix platform, limits SHALL be enforced via `preexec_fn` using `_build_preexec_fn` from `mcc/exec.py`, passed to `asyncio.create_subprocess_exec`. On non-unix platforms, limits SHALL be silently ignored. When the subprocess is killed by a resource limit signal, the error message SHALL include `resource limit hit:` and the signal reason.

#### Scenario: Memory limit enforced on isolated python tool
- **WHEN** a python tool specifies `limits: {mem_mb: 256}` on a unix platform
- **THEN** the subprocess is started with `RLIMIT_AS` set to 256 MB

#### Scenario: Process exceeds limit
- **WHEN** a subprocess exceeds a resource limit
- **THEN** the tool returns `(code, stdout, stderr)` where stderr contains `resource limit hit:`

#### Scenario: Limits on non-unix platform
- **WHEN** limits are specified but the platform is not unix
- **THEN** limits are silently ignored and the subprocess runs without resource constraints

### Requirement: stdlib-only pyrunner
`mcc/pyrunner.py` SHALL import only Python standard library modules. It SHALL be locatable at runtime as `Path(__file__).with_name("pyrunner.py")` relative to `mcc/models.py`. `mcc` modules MAY import from `pyrunner.py`; `pyrunner.py` MUST NOT import from any `mcc` module.

#### Scenario: pyrunner runs on target interpreter without mcc installed
- **WHEN** pyrunner.py is executed by a Python interpreter that does not have mcc installed
- **THEN** it runs successfully without ImportError

### Requirement: dotpath resolution refactored into pyrunner
The fn path resolution logic (parsing `module:attr` and `module.attr` formats, importing the module, and traversing attributes) SHALL live in `pyrunner.py` as the canonical implementation. `mcc/models.py` SHALL import and reuse this function from `pyrunner.py` for its existing in-process resolution, rather than duplicating the logic.

#### Scenario: mcc reuses pyrunner resolve for in-process fn tools
- **WHEN** an fn tool without `python:` is loaded
- **THEN** `ToolModel.callable` resolves the fn path by calling the `resolve` function imported from `pyrunner.py`

#### Scenario: pyrunner resolve handles colon-separated path
- **WHEN** fn_path is `mypackage.mymodule:MyClass.method`
- **THEN** resolve imports `mypackage.mymodule` and traverses `MyClass` then `method`

#### Scenario: pyrunner resolve handles dot-separated path
- **WHEN** fn_path is `mypackage.mymodule.my_function`
- **THEN** resolve imports `mypackage.mymodule` and retrieves `my_function`
