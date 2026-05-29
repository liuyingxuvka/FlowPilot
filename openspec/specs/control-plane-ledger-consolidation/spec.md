# control-plane-ledger-consolidation Specification

## Purpose
TBD - created by archiving change consolidate-flowpilot-control-plane-ledgers. Update Purpose after archive.
## Requirements
### Requirement: Daemon-owned scheduler folding
FlowPilot SHALL treat the Router daemon as the single owner of scheduler ledger
state transitions while a run is in daemon mode.

#### Scenario: Foreground receipt arrives during daemon mode
- **WHEN** Controller writes a valid receipt for a Controller action while a live
  Router daemon owns the run
- **THEN** the receipt is persisted as append-only completion evidence
- **AND** scheduler row status is folded by Router-owned reconciliation rather
  than by an independent foreground scheduler write.

#### Scenario: Daemon folds receipt into scheduler state
- **WHEN** the Router daemon observes a valid unreconciled Controller receipt
- **THEN** it updates the matching Controller action record, scheduler row, and
  display projection from one fold operation
- **AND** the fold is idempotent across repeated daemon ticks.

### Requirement: Pending action is a non-authoritative projection
FlowPilot SHALL NOT let `pending_action` override Controller action ledger
authority for action execution, receipt requirements, or router-controlled wait
classification.

#### Scenario: Pending action conflicts with Controller action
- **WHEN** `pending_action` says `apply_required=true` but the matching
  Controller action ledger row says the action is receipt-only or
  router-controlled wait
- **THEN** Controller and daemon decisions follow the Controller action ledger
  row
- **AND** status output labels the pending action as a non-authoritative
  projection.

### Requirement: Stale passive waits are superseded
FlowPilot SHALL close or supersede passive/current-scope wait rows whose blocker
or prerequisite has already been resolved by later authoritative state.

#### Scenario: Startup reconciliation blocker is already resolved
- **WHEN** a startup current-scope reconciliation wait points at a Controller row
  that is already reconciled or superseded
- **THEN** Router-owned reconciliation marks the wait row superseded or
  reconciled
- **AND** it is removed from open scheduler rows and passive wait summaries.

### Requirement: Signed artifacts stay immutable
FlowPilot SHALL keep signed packet/result artifacts immutable during control
plane consolidation.

#### Scenario: Missing projection field on signed envelope
- **WHEN** a migration or reconciliation needs additional metadata for an
  already signed packet envelope
- **THEN** it writes a sidecar migration/projection record or a new versioned
  artifact
- **AND** it MUST NOT mutate the signed original envelope body.
