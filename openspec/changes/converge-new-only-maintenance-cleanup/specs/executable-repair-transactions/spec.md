## ADDED Requirements

### Requirement: Retired Event Replay Is Rejected
FlowPilot SHALL reject retired `event_replay` repair transactions instead of
normalizing them into current executable repair transactions.

#### Scenario: Retired replay is submitted
- **WHEN** PM submits a repair transaction whose `plan_kind` is `event_replay`
- **THEN** Router rejects the repair transaction as unsupported
- **AND** Router SHALL NOT treat it as an alias for `await_existing_event`.
