## MODIFIED Requirements

### Requirement: add-user command
`mcc add-user --username <github_handle> [--email <email>]` SHALL create a new user in the store. No token is generated or printed. The command SHALL confirm success by printing the username of the created user.

#### Scenario: add-user creates user by username
- **WHEN** `mcc add-user --username alice` is run
- **THEN** a user with `username="alice"` is created and a confirmation message is printed

#### Scenario: add-user with email stores email
- **WHEN** `mcc add-user --username alice --email alice@example.com` is run
- **THEN** a user with `username="alice"` and `email="alice@example.com"` is created

#### Scenario: add-user with duplicate username exits with error
- **WHEN** `mcc add-user --username alice` is run and that username already exists
- **THEN** the command exits with a non-zero status and prints an error message

#### Scenario: No token is printed
- **WHEN** a user is successfully created
- **THEN** stdout does NOT contain any token string

### Requirement: remove-user command
`mcc remove-user <username>` SHALL delete the user identified by username from the store.

#### Scenario: remove-user deletes existing user by username
- **WHEN** `mcc remove-user alice` is run and that user exists
- **THEN** the user is removed from the store

#### Scenario: remove-user on unknown username exits with error
- **WHEN** `mcc remove-user alice` is run and that username does not exist
- **THEN** the command exits with a non-zero status and prints an error message

### Requirement: list-users command
`mcc list-users` SHALL print each user's username (and email if present) along with their groups and tools.

#### Scenario: list-users shows username
- **WHEN** `mcc list-users` is run
- **THEN** each line shows the user's username

#### Scenario: list-users shows email when present
- **WHEN** `mcc list-users` is run and a user has an email
- **THEN** that user's line includes their email

### Requirement: grant command
`mcc grant <username> [--group <group>] [--tool <tool>]` SHALL add the specified group(s) and/or tool(s) to the user identified by username.

#### Scenario: grant --group adds group to user by username
- **WHEN** `mcc grant alice --group ops` is run
- **THEN** `"ops"` is in alice's groups

#### Scenario: grant --tool adds tool to user by username
- **WHEN** `mcc grant alice --tool special_tool` is run
- **THEN** `"special_tool"` is in alice's explicit tools

#### Scenario: grant with neither --group nor --tool exits with error
- **WHEN** `mcc grant alice` is run with no options
- **THEN** the command exits with a non-zero status and prints a usage error

### Requirement: revoke command
`mcc revoke <username> [--group <group>] [--tool <tool>]` SHALL remove the specified group(s) and/or tool(s) from the user identified by username.

#### Scenario: revoke --group removes group from user by username
- **WHEN** `mcc revoke alice --group ops` is run and alice is in ops
- **THEN** `"ops"` is no longer in alice's groups

#### Scenario: revoke group user is not a member of exits with error
- **WHEN** `mcc revoke alice --group finance` and alice is not in finance
- **THEN** the command exits with a non-zero status and prints an error message
