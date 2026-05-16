# persistent-router-daemon Specification

## Purpose
TBD - created by archiving change daemonize-flowpilot-router. Update Purpose after archive.
## Requirements
### Requirement: Per-run Router daemon
FlowPilot SHALL provide a per-run Router daemon mode that continuously drives
Router reconciliation for one active run without requiring Controller to invoke
`next` or `run-until-wait` after every role ACK, report, or result.

#### Scenario: Daemon starts for an active run
- **WHEN** a formal FlowPilot run enters daemon mode
- **THEN** exactly one Router daemon is associated with that run root and writes daemon status under `.flowpilot/runs/<run-id>/runtime/`

#### Scenario: Daemon uses current run state
- **WHEN** the Router daemon starts or restarts
- **THEN** it MUST load the current run pointer, router state, execution frontier, packet ledger, return ledger, continuation binding, and crew ledger before computing or consuming any next action

### Requirement: Fixed one-second daemon tick
The Router daemon SHALL run a fixed one-second tick while the run lifecycle is
active.

#### Scenario: Active wait tick
- **WHEN** the run is active and Router is waiting for mailbox evidence or Controller receipts
- **THEN** the daemon MUST check the relevant files once per second without dynamic backoff

#### Scenario: Terminal tick stops
- **WHEN** the run lifecycle becomes terminal
- **THEN** the daemon MUST stop active ticking after writing the terminal daemon status and required Controller terminal actions

### Requirement: Router owns ordinary waiting
The Router daemon SHALL own ordinary waits for card ACKs, bundle ACKs, packet
ACKs, role reports, result envelopes, and Controller receipts.

#### Scenario: Card bundle ACK arrives
- **WHEN** Router is waiting for a system-card bundle ACK and the expected ACK file appears
- **THEN** the daemon MUST validate and consume the ACK, update return state idempotently, and compute the next Router action without waiting for Controller to call Router manually

#### Scenario: Role report arrives
- **WHEN** Router is waiting for a role report and a report envelope appears in the expected mailbox path
- **THEN** the daemon MUST validate run id, role, event authority, body path/hash references, and expected route/frontier context before advancing

#### Scenario: Expected evidence is absent
- **WHEN** Router is waiting for expected mailbox evidence and the evidence is absent
- **THEN** the daemon MUST keep the wait state active, update daemon status, and check again on the next one-second tick

### Requirement: Router daemon is idempotent
The Router daemon SHALL treat repeated ticks, duplicate file observations, and
unchanged mailbox files as idempotent.

#### Scenario: Duplicate ACK observation
- **WHEN** the daemon sees the same already-consumed ACK on multiple ticks
- **THEN** it MUST NOT append duplicate return events, reissue duplicate Controller actions, or advance the route twice

#### Scenario: Replayed daemon after crash
- **WHEN** the daemon restarts after a crash during or after mailbox consumption
- **THEN** it MUST use persisted ledgers and action ids to avoid duplicate side effects

### Requirement: Router daemon does not execute host actions
The Router daemon SHALL NOT perform Controller-only host actions such as sending
messages to role agents, displaying user-dialog text, creating automations,
spawning roles, or closing roles.

#### Scenario: Next action requires Controller
- **WHEN** the next Router action requires a host tool, user-dialog display, role relay, role spawn, automation update, or Controller receipt
- **THEN** the daemon MUST write a Controller action ledger entry instead of marking the action complete

#### Scenario: Internal safe action
- **WHEN** the next Router action is already classified as safe internal Router work
- **THEN** the daemon MAY apply that internal action and continue ticking without Controller execution

### Requirement: Run-scoped Router lock
The Router daemon SHALL use a run-scoped lock to prevent two Router daemons from
writing the same run state.

#### Scenario: Duplicate daemon start
- **WHEN** a second Router daemon starts for a run with a live non-stale daemon lock
- **THEN** the second daemon MUST refuse to become the writer and report the existing daemon status

#### Scenario: Delayed daemon heartbeat requires liveness check
- **WHEN** foreground monitoring observes a daemon heartbeat older than five seconds
- **THEN** FlowPilot MUST report `heartbeat_status=check_liveness` rather than replacing the lock from heartbeat age alone

#### Scenario: Stale daemon lock after liveness check
- **WHEN** Controller liveness checking confirms that the current-run daemon process is not alive and the daemon lock is stale according to the configured stale-lock threshold
- **THEN** recovery MAY replace the stale lock and restart Router from persisted run state

#### Scenario: Active daemon appears during recovery
- **WHEN** Controller attempts recovery after `check_liveness` and discovers a live current-run daemon lock
- **THEN** FlowPilot MUST attach to the existing daemon and MUST NOT start a second writer
