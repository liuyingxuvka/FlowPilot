# startup-answer-reconciliation Specification

## Purpose
TBD - created by archiving change fix-startup-answer-reconciliation. Update Purpose after archive.
## Requirements
### Requirement: Startup answers have one authoritative owner
FlowPilot SHALL treat the confirmed interactive startup intake result as the
authoritative startup answer owner for a run. Router reconciliation MUST NOT
create a separate required Controller-owned `record_startup_answers` step after
the intake result has already recorded startup answers and completed the
deterministic startup seed.

#### Scenario: intake result records answers once
- **WHEN** `open_startup_intake_ui` completes with a valid interactive native
  intake result
- **THEN** Router records startup answers and deterministic seed evidence under
  the startup intake owner
- **AND** the next startup action MUST NOT be `record_startup_answers` solely
  because the daemon receipt used a bootloader apply source.

#### Scenario: completed seed prevents deterministic setup rows
- **WHEN** durable deterministic startup seed evidence is complete for the
  current run
- **THEN** Router MUST project seed-owned flags before choosing the next startup
  action
- **AND** Router MUST NOT schedule seed-owned setup rows as ordinary Controller
  work.

### Requirement: Startup answer replay is idempotent
FlowPilot SHALL treat `record_startup_answers` as idempotent when the run
already has validated durable startup answers that satisfy the same
postcondition. Replayed receipts MUST reconcile the row instead of creating a
PM/control blocker.

#### Scenario: repeated answer receipt matches durable answers
- **WHEN** a `record_startup_answers` Controller receipt contains startup
  answers matching the run's durable startup answers
- **THEN** Router marks the startup answer postcondition reconciled
- **AND** Router MUST NOT create a PM/control blocker from that replay.

#### Scenario: repeated answer receipt differs from durable answers
- **WHEN** a `record_startup_answers` Controller receipt contains startup
  answers that conflict with the run's durable startup answers
- **THEN** Router MUST keep the row unreconciled or blocked through the existing
  unsupported/missing-postcondition path
- **AND** Router MUST NOT silently overwrite the durable answers.

### Requirement: Startup receipt contract matches executable reconciliation
FlowPilot SHALL expose a Controller completion contract for startup bootloader
rows that matches the executable Router reconciliation path. A row shown as
receipt-completable MUST have a receipt effect that can prove or reject its
postcondition.

#### Scenario: receipt-completable answer row has an effect
- **WHEN** Router exposes `record_startup_answers` as a Controller
  receipt-completable row
- **THEN** the startup receipt effect handler can validate the receipt payload
  and either reconcile the postcondition or return a precise unsupported reason.

#### Scenario: router-apply-only row is not mislabeled
- **WHEN** a startup row can only be completed through Router bootloader apply
- **THEN** Controller-facing metadata MUST NOT describe it as ordinary
  receipt-only work.
