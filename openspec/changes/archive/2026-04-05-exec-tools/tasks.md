## 1. ToolModel Changes

- [x] 1.1 Add `exec: str | None = None`, `stdin: bool = False`, `timeout: int | None = None`, `limits: dict | None = None` fields to ToolModel
- [x] 1.2 Add model validator enforcing exactly one of `fn` or `exec` is set
- [x] 1.3 Make `fn` optional (`str | None = None`)
- [x] 1.4 Update `introspect()` to skip callable-based inference when `exec` is set; default name to command basename
- [x] 1.5 Update `callable` cached property to generate async subprocess closure for exec tools
- [x] 1.6 Update `signature` property to handle exec tools (no return type annotation available)

## 2. Subprocess Closure

- [x] 2.1 Implement interpolation mode: `cmd = self.exec.format(**params)`, run via `asyncio.create_subprocess_shell`, return `(returncode, stdout, stderr)`
- [x] 2.2 Implement stdin mode: pipe `json.dumps(params)` to stdin, return `(returncode, stdout, stderr)`
- [x] 2.3 Implement timeout: wrap `proc.communicate()` in `asyncio.wait_for`, kill and return `(-1, "", "timeout after {n}s")` on expiry
- [x] 2.4 Implement resource limits: build `preexec_fn` from `limits` dict using `resource` module (`RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_FSIZE`, `RLIMIT_NOFILE`), pass as kwarg to `create_subprocess_shell`; skip silently on non-unix

## 3. Tests

- [x] 3.1 Create test fixture YAML files for exec tools (interpolation mode, stdin mode, timeout)
- [x] 3.2 Test exec tool loads and registers correctly
- [x] 3.3 Test fn+exec raises ValueError, neither fn nor exec raises ValueError
- [x] 3.4 Test interpolation mode executes command with params formatted in
- [x] 3.5 Test stdin mode sends JSON on stdin
- [x] 3.6 Test successful command returns `(0, stdout, stderr)`
- [x] 3.7 Test failed command returns `(nonzero, stdout, stderr)` without raising
- [x] 3.8 Test timeout kills process and returns `(-1, "", "timeout after {n}s")`
- [x] 3.9 Test name defaults to command basename when not specified
- [x] 3.10 Test resource limits are applied via `preexec_fn` (unix only)
- [x] 3.11 Test limits silently ignored on non-unix (or when not set)

## 4. Documentation

- [x] 4.1 Add exec tool YAML format examples to README
- [x] 4.2 Document security warning about shell injection with interpolation mode
