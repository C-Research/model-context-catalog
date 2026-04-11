## 1. Core Implementation

- [x] 1.1 In `load_file()`, add a first-pass `yaml.safe_load()` to extract top-level `env_file` and `env` fields from the raw YAML before `EnvYAML` is called
- [x] 1.2 Resolve `env_file` path relative to the YAML file's directory; raise `FileNotFoundError` if the file does not exist
- [x] 1.3 Build the env overlay dict: `{**dotenv_values(env_file), **env_block}` (env block wins on conflicts)
- [x] 1.4 Temporarily inject overlay into `os.environ` (keys not already set) before calling `EnvYAML`; clean up in finally block

## 2. Tests

- [x] 2.1 Test: file-level `env_file` expands `${VAR}` in a `curl:` template
- [x] 2.2 Test: file-level `env_file` expands `${VAR}` in a param `override:` field
- [x] 2.3 Test: file-level `env` block expands `${VAR}`, overrides `env_file` on conflict
- [x] 2.4 Test: missing `env_file` path raises `FileNotFoundError` at load time
- [x] 2.5 Test: per-tool `env_file`/`env` still passed through to `ToolModel` unchanged
- [x] 2.6 Test: YAML file with no top-level `env_file`/`env` loads without change (regression)

## 3. Integration

- [x] 3.1 Update `osint/search.yaml`: move `env_file: osint.env` from per-tool to top-level; remove per-tool `env_file` from `serpapi_search`
- [x] 3.2 Verify server starts and `${SERPAPI_KEY}` resolves correctly with the updated YAML
