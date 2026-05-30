# startup-answer-reconciliation Specification

## Purpose
TBD - created by archiving change fix-startup-answer-reconciliation. Update Purpose after archive.
## Requirements
### Requirement: Startup answers have one authoritative owner
FlowPilot SHALL treat the confirmed interactive startup intake result as the
authoritative startup answer owner for a run. Router reconciliation MUST NOT
create a separate required Controller-owned answer-recording step after
the intake result has already recorded startup answers and completed the
deterministic startup seed.

#### Scenario: intake result records answers once
- **WHEN** `open_startup_intake_ui` completes with a valid interactive native
  intake result
- **THEN** Router records startup answers and deterministic seed evidence under
  the startup intake owner
- **AND** the next startup action MUST NOT be a separate answer-recording row solely
  because the daemon receipt used a bootloader apply source.

#### Scenario: completed seed prevents deterministic setup rows
- **WHEN** durable deterministic startup seed evidence is complete for the
  current run
- **THEN** Router MUST project seed-owned flags before choosing the next startup
  action
- **AND** Router MUST NOT schedule seed-owned setup rows as ordinary Controller
  work.

### Requirement: Unsupported startup answer receipts are not current work
FlowPilot SHALL keep durable native startup intake answers as the current
answer owner and SHALL NOT treat unsupported answer-recording receipts as current
Controller work. Replayed unsupported receipts MUST NOT overwrite durable answers.

#### Scenario: unsupported answer receipt matches durable answers
- **WHEN** a unsupported answer-recording Controller receipt contains startup
  answers matching the run's durable startup answers
- **THEN** Router keeps the durable startup answer owner unchanged
- **AND** Router MUST NOT create a PM/control blocker from that replay.

#### Scenario: unsupported answer receipt differs from durable answers
- **WHEN** a unsupported answer-recording Controller receipt contains startup
  answers that conflict with the run's durable startup answers
- **THEN** Router MUST reject or quarantine the unsupported receipt through the existing
  unsupported/missing-postcondition path
- **AND** Router MUST NOT silently overwrite the durable answers.

### Requirement: Startup receipt contract matches executable reconciliation
FlowPilot SHALL expose a Controller completion contract for startup bootloader
rows that matches the executable Router reconciliation path. A row shown as
receipt-completable MUST have a receipt effect that can prove or reject its
postcondition.

#### Scenario: answer work is seed-owned
- **WHEN** Router needs to prove startup answers for the current run
- **THEN** the startup receipt effect handler uses native intake and deterministic
  seed evidence
- **AND** it returns a precise unsupported reason for unsupported answer-recording rows.

#### Scenario: router-apply-only row is not mislabeled
- **WHEN** a startup row can only be completed through Router bootloader apply
- **THEN** Controller-facing metadata MUST NOT describe it as ordinary
  receipt-only work.
