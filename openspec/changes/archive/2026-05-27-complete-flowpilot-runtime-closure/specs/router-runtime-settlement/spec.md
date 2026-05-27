## ADDED Requirements

### Requirement: Reconciled Controller actions backfill Router scheduler rows

FlowPilot SHALL keep the existing Router-owned reconciliation path as the
single owner for Controller action and Router scheduler settlement.

#### Scenario: Controller action is already reconciled
- **WHEN** a Controller action is `done` and `router_reconciliation_status` is
  `reconciled`
- **AND** the matching Router scheduler row is still `receipt_done`
- **THEN** Router backfills the scheduler row to `reconciled` from the durable
  Controller action reconciliation evidence
- **AND** it does not start a second ordinary pusher or daemon to settle the
  row.

#### Scenario: Startup role-slot receipt was already applied
- **WHEN** startup role slots have been applied and their Controller action is
  already reconciled
- **THEN** the startup bootloader reconciliation path remains idempotent and
  still leaves the matching Router scheduler row reconciled.

### Requirement: Active runtime writers wait instead of becoming blockers

FlowPilot SHALL treat fresh or visibly progressing runtime JSON writers as a
wait/retry state in the existing foreground and daemon settlement path.

#### Scenario: Runtime writer is active
- **WHEN** a foreground command or daemon tick observes a fresh runtime JSON
  write lock
- **THEN** it waits for the writer to settle and retries the existing operation
  instead of recording a PM/control blocker or launching a second writer.

#### Scenario: Runtime writer keeps making progress
- **WHEN** a runtime JSON write lock is older than the normal fresh threshold
  but the target file or lock evidence continues changing
- **THEN** FlowPilot continues waiting through the existing settlement helper
  until the writer settles or becomes stale without progress.
