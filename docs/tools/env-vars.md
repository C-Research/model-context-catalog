# Environment Variables

MCC supports environment variable substitution in YAML tool files. Any value in the YAML can reference an environment variable using `$VAR_NAME` or `${VAR_NAME}` syntax.

## Usage

```yaml
groups: [internal]
tools:
  - fn: mypackage.api:call
    description: Calls the internal API
    params:
      - name: api_key
        type: str
        override: $INTERNAL_API_KEY

      - name: base_url
        type: str
        override: ${API_BASE_URL}
```

At load time, MCC substitutes the values from the environment:

```bash
export INTERNAL_API_KEY=secret123
export API_BASE_URL=https://api.internal.example.com
```

## Behavior when a variable is unset

If a referenced variable is not set in the environment, MCC leaves the literal string as-is (e.g. `$INTERNAL_API_KEY`). No error is raised.

!!! tip "Always hidden"
    Use overrides for injecting env vars into tool calls. This keeps secrets out of YAML and out of the LLM's view.

