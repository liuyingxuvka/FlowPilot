# startup-settlement-ownership Specification

## Purpose
TBD - created by archiving change unify-startup-settlement-ownership. Update Purpose after archive.
## Requirements
### Requirement: Foreground startup waits for active runtime writers
FlowPilot SHALL treat fresh runtime JSON write locks encountered by foreground
startup/status reads as settlement-in-progress evidence and retry after the
writer settles.

#### Scenario: foreground start sees fresh runtime writer
- **WHEN** a foreground startup command needs runtime JSON while a fresh
  runtime write lock is present
- **THEN** FlowPilot waits for the active writer to settle and retries the
  read
- **AND** FlowPilot MUST NOT return a fatal startup error solely because the
  fresh lock existed.

#### Scenario: stale runtime writer remains a failure
- **WHEN** a foreground startup command needs runtime JSON while the matching
  runtime write lock is stale
- **THEN** FlowPilot uses the existing stale-write failure path rather than
  waiting indefinitely.

### Requirement: Startup receipt application has a single final owner
FlowPilot SHALL reconcile startup daemon bootloader Controller receipts through
the existing startup receipt application path before marking startup action
rows or scheduler rows as Router-reconciled. Startup intake answers and their
deterministic seed side effects SHALL have one authoritative owner and SHALL be
safe to replay after daemon/controller reconciliation.

#### Scenario: daemon bootloader postcondition writes a done receipt
- **WHEN** a startup daemon bootloader action writes or observes a done
  Controller receipt
- **THEN** FlowPilot applies the startup postcondition through the existing
  startup receipt effect handler
- **AND** the resulting action-row and scheduler-row reconciliation source
  MUST be the startup Controller receipt owner, not a direct daemon
  postcondition owner.

#### Scenario: startup receipt replay is idempotent
- **WHEN** a startup daemon bootloader receipt has already been reconciled
- **THEN** a later daemon tick or foreground retry treats the receipt as
  already settled
- **AND** FlowPilot MUST NOT create a PM/control blocker from the replay.

#### Scenario: native startup intake receipt folds UI result
- **WHEN** the startup daemon schedules `open_startup_intake_ui`
- **AND** the Controller writes a done receipt containing the native startup
  intake `result_path`
- **THEN** FlowPilot applies the same startup intake validation and bootstrap
  seeding used by the direct bootloader apply path
- **AND** the action row, scheduler row, bootstrap pending action, and
  run-state startup flags reconcile under the startup Controller receipt owner.

#### Scenario: daemon apply receipt preserves intake side effects
- **WHEN** the startup daemon observes an `open_startup_intake_ui` receipt
  written by the bootloader apply path
- **AND** the startup intake result has already recorded answers and completed
  deterministic seed evidence
- **THEN** FlowPilot syncs the startup answer and seed-owned flags before
  choosing later startup work
- **AND** FlowPilot MUST NOT reissue a separate answer-recording row for the same
  completed intake.

#### Scenario: retired answer-recording receipt replay is safe
- **WHEN** a retired answer-recording receipt is replayed after the same
  startup answers are already durable for the run
- **THEN** FlowPilot preserves the native startup answer owner and treats the
  retired receipt as non-current replay evidence
- **AND** FlowPilot MUST NOT create a PM/control blocker from the replay.

#### Scenario: unsupported startup receipt still blocks
- **WHEN** the existing startup receipt effect handler cannot prove the
  startup postcondition from the receipt and run state
- **THEN** FlowPilot keeps the existing unsupported-receipt or blocker path
  instead of marking the row reconciled through a fallback owner.

### Requirement: Live projection accepts post-release startup packet states
FlowPilot's focused startup-settlement projection SHALL treat a Router-released
`user_intake` packet as released after the PM opens the packet body or after a
terminal lifecycle records that the previously released packet was stopped by
the user.

#### Scenario: released startup packet is opened by PM
- **WHEN** the packet ledger records Router startup release of `user_intake`
  to the project manager
- **AND** the packet status later becomes `packet-body-opened-by-recipient`
- **THEN** the live projection MUST treat startup `user_intake` as released
  rather than reporting an unreleased-packet finding.

#### Scenario: terminal lifecycle preserves prior release evidence
- **WHEN** the packet ledger records Router startup release of `user_intake`
  before a user stop or terminal lifecycle status
- **THEN** the live projection MUST preserve that release evidence
- **AND** it MUST NOT require the top-level active packet status to remain at
  the earlier `envelope-relayed` state.
