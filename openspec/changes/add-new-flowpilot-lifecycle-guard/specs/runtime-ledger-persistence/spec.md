## ADDED Requirements

### Requirement: Current-run ledger persists lifecycle guard authority
The new FlowPilot current-run ledger SHALL persist lifecycle guard snapshots,
patrol decisions, resume evidence, repeated-action history, and terminal stop
authority as machine-readable current-run state.

#### Scenario: Guard snapshot is written after state-changing command
- **WHEN** startup, status, patrol, resume, packet assignment, ACK, result
  submission, or closure changes the legal next action
- **THEN** the current-run ledger MUST contain the latest lifecycle guard
  snapshot
- **AND** the run projection MUST write a guard artifact under the current run
  without exposing sealed bodies.

#### Scenario: Terminal stop authority is current-run state
- **WHEN** the final closure decision is complete
- **THEN** the ledger MUST record terminal stop authority through the lifecycle
  guard
- **AND** old route state, chat memory, or prior-run artifacts MUST NOT be used
  as the stop authority.

#### Scenario: Repeated action history survives reload
- **WHEN** the same current run is loaded after a manual resume or later
  process invocation
- **THEN** repeated-action history and the latest guard snapshot MUST be read
  from the current-run ledger
- **AND** the guard MUST be able to classify a repeated unchanged action as
  control-plane stuck.
