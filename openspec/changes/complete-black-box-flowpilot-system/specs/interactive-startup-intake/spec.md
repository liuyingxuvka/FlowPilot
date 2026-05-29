## ADDED Requirements

### Requirement: Startup Intake Feeds Current Run Ledger

Interactive startup intake SHALL create sealed current-run evidence that can be
materialized into the complete black-box ledger without exposing the user work
request as public chat or status text.

#### Scenario: Startup intake submits work request

- **WHEN** the startup panel records the work request and options
- **THEN** the runtime MUST write a sealed intake body with public envelope,
  path, hash, answer enums, and run id
- **AND** the router MUST consume that record through the current-run ledger.

### Requirement: Startup UI Is Not Completion Evidence

Interactive startup intake SHALL NOT be treated as route execution or
completion evidence.

#### Scenario: Startup panel closes successfully

- **WHEN** the startup panel returns a valid intake record
- **THEN** the runtime MUST proceed to contract/route startup gates and MUST NOT
  mark project work complete from the intake record alone.
