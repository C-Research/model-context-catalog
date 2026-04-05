## Context

The tool catalog currently only supports Python callables via `fn:` in YAML. The `ToolModel.callable` property resolves Python import paths, and `introspect()` infers name/description/params from the callable's signature and docstring. To support external commands, we need a second execution path that runs subprocesses instead of calling Python functions.

The existing `contrib/subprocess.py:bash()` already implements the async subprocess pattern returning `(returncode, stdout, stderr)`. The exec tool feature generalizes this into the tool model itself.

## Goals / Non-Goals

**Goals:**
- Allow tool definitions to specify an external command via `exec:` field
- Support two parameter-passing modes: command string interpolation (default) and JSON-on-stdin
- Optional timeout enforcement via `asyncio.wait_for`
- Consistent return signature `(returncode, stdout, stderr)` for all exec tools
- No changes to existing `fn:` tool behavior

**Non-Goals:**
- Full sandboxing or containerization
- Shell injection prevention — documented risk, accepted for now
- Streaming stdout/stderr — full capture only

## Decisions

### 1. `exec` as a new field alongside `fn`, not a replacement

ToolModel gets `exec: str | None = None` and `fn: str | None = None`. A model validator enforces exactly one is set. This keeps the existing `fn` path completely untouched.

**Alternative**: Overloading `fn` with a prefix like `fn: exec:node tool.js`. Rejected — muddies the field semantics and complicates parsing.

### 2. `callable` generates a closure for exec tools

Rather than branching in `call()`, the `callable` cached property returns a generated async function for exec tools. This means `call()` works identically for both tool types — it just sees an async callable.

The generated closure captures `self.exec`, `self.stdin`, and `self.timeout` and uses `asyncio.create_subprocess_shell`.

### 3. `stdin: bool = False` — interpolation is the default

Most exec tools will wrap existing CLI commands where interpolation (`exec: "grep -rn {pattern} {path}"`) is the natural fit. Stdin mode (`stdin: true`) is opt-in for polyglot JSON protocol tools.

**Alternative**: Default to `stdin: true` for safety (no injection risk). Rejected — interpolation is the common case and more ergonomic.

### 4. `introspect()` skips callable-based inference for exec tools

Exec tools have no Python callable to inspect. The validator skips name/description/params inference when `exec` is set. Name defaults to the command basename. Params must be declared in YAML.

### 5. Timeout returns a tuple, does not raise

On timeout, the process is killed and the tool returns `(-1, "", "timeout after {n}s")` instead of raising `TimeoutError`. This keeps the return type consistent.

### 6. Resource limits via `preexec_fn` passthrough

Exec tools may declare a `limits` dict with `mem_mb`, `cpu_sec`, `fsize_mb`, and `nofile` keys. These are enforced using Python's `resource` module in a `preexec_fn` passed as a kwarg to `asyncio.create_subprocess_shell`. The kwarg passes through asyncio's subprocess layer down to `subprocess.Popen` on CPython/Unix.

```yaml
limits:
  mem_mb: 256
  cpu_sec: 30
  fsize_mb: 50
  nofile: 128
```

Maps to:
- `mem_mb` → `resource.RLIMIT_AS`
- `cpu_sec` → `resource.RLIMIT_CPU`
- `fsize_mb` → `resource.RLIMIT_FSIZE`
- `nofile` → `resource.RLIMIT_NOFILE`

Unix only. On non-unix platforms, limits are silently ignored. When a process exceeds a limit, the OS kills it — the tool returns a nonzero exit code like any other failure.

**Alternative**: Use `asyncio.timeout()` or external wrappers like `ulimit` in the command string. Rejected — `preexec_fn` is cleaner, applies before the process starts, and doesn't require modifying the command.

## Risks / Trade-offs

- **Shell injection** → Accepted risk. Documented in tool YAML and README. Exec tools with user-controlled params should not be exposed to untrusted callers.
- **Timeout kills process tree** → `proc.kill()` only kills the direct child. If the command spawns subprocesses, they may orphan. Mitigation: use process groups in a future iteration.
- **No param introspection** → Exec tools with missing param definitions will fail at call time, not load time. Mitigation: validate that interpolation placeholders match declared params during `introspect()`.
- **`preexec_fn` passthrough** → Relies on CPython implementation detail (asyncio forwarding kwargs to `Popen`). Works reliably in practice but isn't part of the asyncio API contract. Unix only.
