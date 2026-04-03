## ADDED Requirements

### Requirement: CLI entry point via `mcc` command
The system SHALL expose a Click CLI group named `cli` in `mcc/cli.py`, registered as the `mcc` console script in `pyproject.toml`. All user and permission management SHALL be performed through this CLI.

#### Scenario: mcc is available as a command
- **WHEN** the package is installed
- **THEN** `mcc --help` lists available commands

### Requirement: add-user command
`mcc add-user <username>` SHALL create a new user in the store, generate a bearer token, print the token to stdout exactly once, and print a warning that the token will not be shown again. The `--admin` flag SHALL set `is_admin=True`.

#### Scenario: add-user creates user and prints token
- **WHEN** `mcc add-user alice` is run
- **THEN** a user named `alice` is created with `is_admin=False` and the plain token is printed to stdout

#### Scenario: add-user --admin creates admin user
- **WHEN** `mcc add-user alice --admin` is run
- **THEN** `alice` is created with `is_admin=True`

#### Scenario: add-user with duplicate username exits with error
- **WHEN** `mcc add-user alice` is run and `alice` already exists
- **THEN** the command exits with a non-zero status and prints an error message

#### Scenario: Token is shown once with save warning
- **WHEN** a user is successfully created
- **THEN** stdout contains the token and a message indicating it will not be shown again

### Requirement: remove-user command
`mcc remove-user <username>` SHALL delete the user from the store.

#### Scenario: remove-user deletes existing user
- **WHEN** `mcc remove-user alice` is run and alice exists
- **THEN** the user is removed from the store

#### Scenario: remove-user on unknown user exits with error
- **WHEN** `mcc remove-user alice` is run and alice does not exist
- **THEN** the command exits with a non-zero status and prints an error message

### Requirement: grant command
`mcc grant <username> [--group <group>] [--tool <tool>]` SHALL add the specified group(s) and/or tool(s) to the user. At least one of `--group` or `--tool` is required. Both may be specified in one invocation.

#### Scenario: grant --group adds group to user
- **WHEN** `mcc grant alice --group ops` is run
- **THEN** `"ops"` is in alice's groups

#### Scenario: grant --tool adds tool to user
- **WHEN** `mcc grant alice --tool special_tool` is run
- **THEN** `"special_tool"` is in alice's explicit tools

#### Scenario: grant with both --group and --tool applies both
- **WHEN** `mcc grant alice --group ops --tool special_tool` is run
- **THEN** both `"ops"` is in alice's groups and `"special_tool"` is in alice's tools

#### Scenario: grant with neither --group nor --tool exits with error
- **WHEN** `mcc grant alice` is run with no options
- **THEN** the command exits with a non-zero status and prints a usage error

#### Scenario: grant on unknown user exits with error
- **WHEN** `mcc grant nonexistent --group ops` is run
- **THEN** the command exits with a non-zero status and prints an error message

### Requirement: revoke command
`mcc revoke <username> [--group <group>] [--tool <tool>]` SHALL remove the specified group(s) and/or tool(s) from the user. At least one of `--group` or `--tool` is required.

#### Scenario: revoke --group removes group from user
- **WHEN** `mcc revoke alice --group ops` is run and alice is in ops
- **THEN** `"ops"` is no longer in alice's groups

#### Scenario: revoke --tool removes tool from user
- **WHEN** `mcc revoke alice --tool special_tool` is run
- **THEN** `"special_tool"` is no longer in alice's explicit tools

#### Scenario: revoke group user is not a member of exits with error
- **WHEN** `mcc revoke alice --group finance` and alice is not in finance
- **THEN** the command exits with a non-zero status and prints an error message
