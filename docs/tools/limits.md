# Resource Limits

Resource limits cap how much CPU, memory, and other OS resources a tool's subprocess can consume. They are applied via [`setrlimit`](https://man7.org/linux/man-pages/man2/setrlimit.2.html) in the child process before the tool runs.

!!! note "Unix only"
    Resource limits use POSIX `setrlimit` and are only enforced on Linux and macOS. The `limits:` field is silently ignored on Windows.

## Configuration

```yaml
tools:
  - name: sandbox
    exec: python {{ script | quote }}
    limits:
      mem_mb: 256
      cpu_sec: 10
      fsize_mb: 50
      nofile: 64
    params:
      - name: script
        type: str
        required: true
```

All fields are optional — set only the ones you need. Limits apply to both `exec:` and `fn:` tools.

## Limit types

### `mem_mb` — virtual memory (`RLIMIT_AS`)

Caps the total virtual address space the process can map, in megabytes.

When exceeded the OS delivers `SIGKILL` to the process. The tool returns:

```python
(-9, "", "resource limit hit: killed (SIGKILL) [limits: {'mem_mb': 256}]")
```

**What it covers:** heap allocations, memory-mapped files, stack, and shared libraries — any address space reservation counts against this limit.

**What it doesn't cover:** it measures virtual memory, not resident (physical) memory. A process that maps 1 GB but only touches 100 MB of pages will still hit a 256 MB `mem_mb` limit because the address space reservation itself exceeds it.

**Typical values:** 256–2048 MB depending on the workload. Set conservatively for untrusted user scripts; more generously for known data-processing jobs.

```yaml
limits:
  mem_mb: 512    # 512 MB virtual address space
```

---

### `cpu_sec` — CPU time (`RLIMIT_CPU`)

Caps the total CPU time the process may consume, in seconds. This measures actual processor time used — not wall-clock time.

When the soft limit is reached the OS sends `SIGXCPU`; if execution continues to the hard limit it sends `SIGKILL`. MCC sets both soft and hard to the same value, so the process is killed immediately when the limit is hit. The tool returns:

```python
(-24, "", "resource limit hit: cpu time exceeded (SIGXCPU) [limits: {'cpu_sec': 10}]")
```

**CPU time vs. wall time:** a process that sleeps for 60 seconds uses almost no CPU time and will not hit a 10-second `cpu_sec` limit. A process that runs a tight compute loop for 10 seconds will. Use `timeout:` to enforce wall-clock deadlines; use `cpu_sec` to cap compute cost.

**Typical values:** 5–60 seconds for interactive tools; higher for batch jobs. Combine with `timeout:` if you want to cap both:

```yaml
limits:
  cpu_sec: 30     # can't burn more than 30 CPU seconds
timeout: 60       # must finish within 60 wall-clock seconds
```

---

### `fsize_mb` — file write size (`RLIMIT_FSIZE`)

Caps the maximum size of any single file the process may write, in megabytes.

When a write would exceed this limit, the OS sends `SIGXFSZ` and the write fails with `EFBIG`. The tool returns:

```python
(-25, "", "resource limit hit: file size exceeded (SIGXFSZ) [limits: {'fsize_mb': 50}]")
```

**What it covers:** any file created or extended by the subprocess — output files, logs, temp files, pipes backed by files.

**What it doesn't cover:** it is per-file, not total disk usage. A process could write 100 files each just under the limit.

**Typical values:** 10–500 MB. Useful for preventing runaway log writes or oversized output files from user scripts.

```yaml
limits:
  fsize_mb: 100   # no single file may grow beyond 100 MB
```

---

### `nofile` — open file descriptors (`RLIMIT_NOFILE`)

Caps the number of file descriptors the process may have open simultaneously.

When the limit is reached, any attempt to open a new file or socket returns `EMFILE` ("too many open files"). The process is not killed — it continues running but can't open more resources.

**What it covers:** regular files, sockets, pipes, device files — anything represented as a file descriptor.

**What it doesn't cover:** already-open descriptors inherited from the parent process (stdin/stdout/stderr and any others) count against the limit. MCC's subprocess starts with at least 3 (stdin, stdout, stderr).

**Typical values:** 64–256 for tightly sandboxed scripts. The system default is typically 1024. Set lower to prevent a script from opening large numbers of network connections or files.

```yaml
limits:
  nofile: 64      # at most 64 open file descriptors
```

---

## Combining limits

All four limits can be set together. Each is enforced independently:

```yaml
tools:
  - name: user_script
    exec: python {{ script | quote }}
    timeout: 30           # wall-clock: killed after 30 seconds regardless
    limits:
      mem_mb: 256         # can't allocate more than 256 MB of address space
      cpu_sec: 20         # can't burn more than 20 CPU seconds
      fsize_mb: 10        # can't write files larger than 10 MB
      nofile: 32          # can't open more than 32 file descriptors
    params:
      - name: script
        type: str
        required: true
```

## On limit violations

When a signal-based limit (`mem_mb`, `cpu_sec`, `fsize_mb`) is exceeded, the process is killed and the tool returns a tuple:

```python
(returncode: int, stdout: str, stderr: str)
```

The `returncode` is the negative signal number (`-9` for SIGKILL, `-24` for SIGXCPU, `-25` for SIGXFSZ). The `stderr` string describes which limit was hit:

```python
(-9,  "", "resource limit hit: killed (SIGKILL) [limits: {'mem_mb': 256}]")
(-24, "", "resource limit hit: cpu time exceeded (SIGXCPU) [limits: {'cpu_sec': 10}]")
(-25, "", "resource limit hit: file size exceeded (SIGXFSZ) [limits: {'fsize_mb': 50}]")
```

`nofile` violations do not kill the process — the subprocess receives an `EMFILE` error on `open()` and decides how to handle it.
