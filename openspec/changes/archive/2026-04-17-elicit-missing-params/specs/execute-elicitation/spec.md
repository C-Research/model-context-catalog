## ADDED Requirements

### Requirement: Elicit missing primitive parameters before execution
When `execute()` is called with missing required parameters that are primitive types (`str`, `int`, `float`, `bool`), the handler SHALL use `ctx.elicit()` to request them from the client before proceeding with tool execution. The elicitation schema SHALL include only the missing required primitive params with their descriptions.

#### Scenario: All missing params elicited and accepted
- **WHEN** a user calls execute with missing required primitive params and the client accepts the elicitation
- **THEN** the provided values are merged with any existing params and the tool is executed

#### Scenario: Elicitation declined
- **WHEN** a user calls execute with missing required params and the client declines the elicitation
- **THEN** the handler returns "Execution cancelled: required parameters not provided"

#### Scenario: Elicitation cancelled
- **WHEN** a user calls execute with missing required params and the client cancels the elicitation
- **THEN** the handler returns "Execution cancelled: required parameters not provided"

#### Scenario: Client does not support elicitation
- **WHEN** a user calls execute with missing required params and the client raises an exception during elicitation
- **THEN** the handler falls through to the existing tool.call() path and returns a validation error

#### Scenario: Missing params include non-primitive types
- **WHEN** a user calls execute with missing required params that include list or dict types
- **THEN** only the missing primitive params are included in the elicitation schema; non-primitive missing params are not elicited and cause a validation error after execution is attempted

#### Scenario: No primitive params missing
- **WHEN** all required primitive params are already provided
- **THEN** elicitation is skipped and the tool is called directly
