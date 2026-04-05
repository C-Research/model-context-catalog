## ADDED Requirements

### Requirement: Find and run prompt
The server SHALL expose a `find_and_run` MCP prompt that takes a `task` parameter and returns a message template guiding the LLM to search for and execute an appropriate tool.

#### Scenario: Prompt with task
- **WHEN** a client requests the `find_and_run` prompt with task="deploy the app"
- **THEN** the server returns a user message instructing the LLM to search for a matching tool and execute it

### Requirement: Explain tool prompt
The server SHALL expose an `explain_tool` MCP prompt that takes a `key` parameter and returns a message template asking the LLM to explain what the tool does.

#### Scenario: Prompt with tool key
- **WHEN** a client requests the `explain_tool` prompt with key="admin.shell"
- **THEN** the server returns a user message instructing the LLM to describe the tool's purpose, parameters, and usage

### Requirement: Debug error prompt
The server SHALL expose a `debug_error` MCP prompt that takes `key` and `error` parameters and returns a message template asking the LLM to diagnose a tool execution failure.

#### Scenario: Prompt with error context
- **WHEN** a client requests the `debug_error` prompt with key="admin.shell" and error="permission denied"
- **THEN** the server returns a user message instructing the LLM to diagnose the error and suggest fixes
