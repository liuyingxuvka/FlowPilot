## MODIFIED Requirements

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
- **AND** FlowPilot MUST NOT reissue `record_startup_answers` for the same
  completed intake.

#### Scenario: answer-recording receipt replay is safe
- **WHEN** a `record_startup_answers` receipt is replayed after the same
  startup answers are already durable for the run
- **THEN** FlowPilot treats the row as reconciled under the startup Controller
  receipt owner
- **AND** FlowPilot MUST NOT create a PM/control blocker from the replay.

#### Scenario: unsupported startup receipt still blocks
- **WHEN** the existing startup receipt effect handler cannot prove the
  startup postcondition from the receipt and run state
- **THEN** FlowPilot keeps the existing unsupported-receipt or blocker path
  instead of marking the row reconciled through a fallback owner.
