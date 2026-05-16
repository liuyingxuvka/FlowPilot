# deterministic-startup-bootstrap Specification

## Purpose
TBD - created by archiving change deterministic-startup-bootstrap. Update Purpose after archive.
## Requirements
### Requirement: Deterministic bootstrap seed owns file foundation
FlowPilot SHALL create deterministic startup foundation files through code
before the unified Router scheduler starts. The seed MUST be limited to local
file and ledger initialization that requires no AI judgment, host automation,
role spawning, heartbeat creation, Controller core loading, or PM repair
decision.

#### Scenario: Seed creates the foundation before scheduling
- **WHEN** a new FlowPilot run starts
- **THEN** the run shell, current pointer, run index, runtime directories,
  empty ledgers, startup answer records, user request reference, and user
  intake scaffold exist before the first Router scheduler row is active

#### Scenario: Seed failure stops startup before PM repair
- **WHEN** deterministic foundation creation fails
- **THEN** FlowPilot records a startup failure before route activation and
  MUST NOT create a PM repair control blocker

### Requirement: Deterministic setup is not Controller work
FlowPilot SHALL NOT schedule deterministic setup actions as Controller action
ledger rows after the seed has completed. This includes placeholder filling,
mailbox initialization, raw user-request recording, and user-intake scaffold
creation.

#### Scenario: Scheduler excludes deterministic setup rows
- **WHEN** the bootstrap seed has completed successfully
- **THEN** the Router scheduler and Controller action ledgers do not contain
  rows for deterministic file setup actions

### Requirement: Startup obligations use the unified scheduler
FlowPilot SHALL schedule startup work that requires waiting, host automation,
role state, or explicit postcondition reconciliation through the unified
Router scheduler.

#### Scenario: Non-deterministic startup work remains scheduled
- **WHEN** startup foundation is ready
- **THEN** role-slot startup, heartbeat binding when requested, and Controller
  core loading are represented as scheduler rows with postcondition contracts

### Requirement: Scheduled row reconciliation is idempotent
FlowPilot SHALL reconcile scheduled rows through one generic
receipt/postcondition path. A row already marked reconciled MUST be skipped on
later receipt scans and MUST NOT produce a PM repair blocker.

#### Scenario: Replayed receipt after reconciliation is harmless
- **WHEN** a receipt is scanned again for a row already marked reconciled
- **THEN** Router leaves the row reconciled and does not create a control
  blocker

#### Scenario: Real unsatisfied postcondition can block
- **WHEN** a scheduled row has a done receipt but its postcondition remains
  unsatisfied
- **THEN** Router may create the appropriate blocker only for that real
  unsatisfied postcondition

### Requirement: Bootstrap evidence remains auditable
FlowPilot SHALL write machine-readable bootstrap evidence that lists the
deterministic foundation artifacts and proof status. Startup review and runtime
tests MUST be able to distinguish seed-owned foundation work from scheduled
Controller work.

#### Scenario: Startup review can inspect seed proof
- **WHEN** startup review checks the run foundation
- **THEN** it can read bootstrap evidence showing which deterministic artifacts
  were created and verified
