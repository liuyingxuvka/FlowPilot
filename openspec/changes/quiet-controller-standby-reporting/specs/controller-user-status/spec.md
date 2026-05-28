## ADDED Requirements

### Requirement: Controller user reports follow a speak/silence budget
The Controller SHALL remain silent for quiet internal progress and SHALL only send user-visible status when the user needs to know or act.

#### Scenario: Quiet patrol does not produce user chatter
- **WHEN** Controller runs quiet standby patrol and receives `continue_patrol`
- **THEN** Controller keeps the foreground duty active without sending a user-visible progress message
- **AND** the result remains Controller-operational metadata only.

#### Scenario: Internal housekeeping stays silent
- **WHEN** Controller completes receipts, ledger row cleanup, relay bookkeeping, patrol restart, or other internal housekeeping without a user-facing state change
- **THEN** Controller MUST NOT send a user-visible status message solely for that housekeeping.

#### Scenario: Meaningful changes are reported concisely
- **WHEN** FlowPilot needs user input, reaches a blocker or recovery path, changes the user-relevant waiting target, displays required route text, stops, or completes
- **THEN** Controller may send a concise plain-language message describing what changed and whether the user needs to act.

#### Scenario: Explicit status request is answered
- **WHEN** the user explicitly asks for current FlowPilot status
- **THEN** Controller may provide a concise plain-language status summary while preserving sealed-body and authority boundaries.
