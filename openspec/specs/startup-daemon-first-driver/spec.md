# startup-daemon-first-driver Specification

## Purpose
TBD - created by archiving change startup-daemon-first-driver. Update Purpose after archive.
## Requirements
### Requirement: Startup Daemon Becomes Driver Before External Startup Work

Formal FlowPilot startup SHALL create only the minimal run shell, current
pointer, and run index before starting or attaching the run-scoped Router
daemon. The daemon SHALL become the startup driver before startup intake UI,
role startup, heartbeat binding, or Controller core load.

#### Scenario: New formal startup starts daemon first

- **WHEN** a new formal startup begins
- **THEN** Router loads, creates the run shell, writes the current pointer,
  updates the run index, and starts or attaches the Router daemon
- **AND** startup intake UI, role startup, heartbeat binding, and Controller
  core load do not happen before daemon readiness is proven.

#### Scenario: Daemon cannot become the startup driver

- **WHEN** the daemon cannot prove live lock, status, and ledger state
- **THEN** startup blocks or fails with explicit repair evidence
- **AND** startup does not continue by directly scheduling external startup
  work from the foreground Router path.

### Requirement: Startup Uses The Same Two-Table Protocol

Daemon-scheduled startup work SHALL be represented in the same Controller
action ledger and Router scheduler ledger used after Controller core loads.

#### Scenario: Daemon schedules a startup row

- **WHEN** the daemon schedules startup intake UI, role startup, heartbeat
  binding, or Controller core handoff
- **THEN** Router writes a Controller action row for Controller/work execution
- **AND** Router writes a Router scheduler row for ordering, scope,
  idempotency, dependencies, and barrier classification
- **AND** Controller may check off the row without owning Router dependency
  metadata.

#### Scenario: Foreground next is called during daemon-owned startup

- **WHEN** the Router daemon controls startup and a foreground `next` request
  happens before Controller core
- **THEN** the foreground path returns an already daemon-scheduled pending row
  or waits briefly for the daemon to schedule one
- **AND** it SHALL NOT compute a fresh external startup row outside the daemon.

#### Scenario: Daemon consumes a startup Controller receipt

- **WHEN** Controller checks off a daemon-scheduled startup row with a `done` receipt
- **THEN** Router MUST sync the matching startup authority flag, Router scheduler row, Controller action row, and bootstrap `pending_action`
- **AND** Router MUST schedule the next startup row unless a real startup barrier has been reached
- **AND** Router MUST NOT reissue the same startup Controller action after the receipt is consumed.

### Requirement: Startup Gate Waits For Current-Scope Reconciliation

Before startup reviewer fact or real-time review begins, Router SHALL clear
startup-scope Controller rows, ACKs, receipts, and required postconditions for
the startup scope.

#### Scenario: Startup review is requested with pending startup rows

- **WHEN** startup review would begin while startup-scope rows, ACKs, receipts,
  or required postconditions remain pending
- **THEN** Router schedules or keeps a current-scope reconciliation wait
- **AND** reviewer review does not start until the startup scope is clean.
