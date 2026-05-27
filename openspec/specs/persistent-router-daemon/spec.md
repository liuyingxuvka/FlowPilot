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
- **WHEN** foreground monitoring observes a daemon heartbeat older than thirty seconds
- **THEN** FlowPilot MUST report `heartbeat_status=check_liveness` rather than replacing the lock from heartbeat age alone

#### Scenario: Stale daemon lock after liveness check
- **WHEN** Controller liveness checking confirms that the current-run daemon process is not alive and the daemon lock is stale according to the configured stale-lock threshold
- **THEN** recovery MAY replace the stale lock and restart Router from persisted run state

#### Scenario: Active daemon appears during recovery
- **WHEN** Controller attempts recovery after `check_liveness` and discovers a live current-run daemon lock
- **THEN** FlowPilot MUST attach to the existing daemon and MUST NOT start a second writer

### Requirement: Shadow crash tests cover daemon and launcher recovery
The system SHALL test daemon shutdown, stale owner locks, interrupted launcher
startup, and resume rehydration through deterministic shadow packages.

#### Scenario: Daemon crash returns to resumable state
- **WHEN** a shadow run simulates daemon death or stale lock during fake AI
  package processing
- **THEN** the Router reports a resumable or blocked standard state and does
  not silently advance work from stale liveness evidence

### Requirement: Daemon defers transient scheduler ledger contention
The Router daemon SHALL treat transient scheduler-ledger access contention as a
retryable tick condition rather than a daemon-fatal error.

#### Scenario: Scheduler ledger read-back is temporarily denied
- **WHEN** the daemon or Router-owned fold verifies or reads
  `router_scheduler_ledger.json`
- **AND** the operating system reports a transient access-denied condition while
  the runtime ledger has fresh write activity
- **THEN** the daemon records a deferred tick
- **AND** it keeps the daemon lock active
- **AND** it retries on the next tick instead of releasing the lock with status
  `error`.

### Requirement: JSON write contention is daemon-deferrable
The Router daemon SHALL keep running when a runtime JSON write is blocked by a
live or uncertain active writer.

#### Scenario: Live writer blocks daemon JSON write
- **WHEN** a Router daemon tick cannot acquire a runtime JSON write lock because
  another writer is live or owner liveness is uncertain
- **THEN** the daemon MUST record the write as deferred for a later tick
- **AND** the daemon MUST NOT exit fatally solely because of that lock wait.

#### Scenario: Dead writer lock is recovered
- **WHEN** a Router daemon tick encounters a fresh runtime JSON write lock whose
  owner process is confirmed dead
- **THEN** the daemon MUST recover the lock, record takeover evidence, and
  continue through the normal persisted-state replay path.

### Requirement: Terminal daemon ticks do not schedule active work
The Router daemon SHALL treat terminal lifecycle state as a hard fence for
nonterminal startup, heartbeat, role, and route actions.

#### Scenario: Daemon tick sees terminal lifecycle
- **WHEN** a Router daemon tick loads a run whose lifecycle status is terminal
- **THEN** the daemon MUST write terminal daemon status and return terminal
  without scheduling startup rows, heartbeat automations, role starts, or route
  work.

#### Scenario: Terminal lifecycle appears during a tick
- **WHEN** terminal lifecycle is written while a daemon tick is processing
- **THEN** any nested startup or heartbeat scheduler reached by that tick MUST
  re-check the terminal fence before creating nonterminal side effects.

### Requirement: Daemon replay covers repair finalization interleavings
The Router daemon SHALL be covered by regression evidence for PM repair
decision finalization interleavings that can expose half-committed
control-blocker state.

#### Scenario: Daemon observes PM repair transaction immediately after commit
- **WHEN** PM submits a valid repair decision and the daemon computes the next
  action in the same live run before any manual clean reload
- **THEN** the daemon MUST observe a coherent post-decision state and MUST NOT
  fail because a repair event requires an unsatisfied PM decision flag.

#### Scenario: Daemon status reports scoped repair blocker
- **WHEN** repair finalization cannot produce an executable next action
- **THEN** daemon status MUST report a concrete repair blocker with current
  required facts rather than a generic non-executable event error.

### Requirement: Daemon evidence cannot be model-only for live misses
FlowPilot SHALL require runtime daemon evidence for known live daemon misses.

#### Scenario: Persistent daemon check skips conformance replay
- **WHEN** a persistent daemon result skips conformance replay or runs in
  abstract model-only mode
- **THEN** that result MUST NOT be counted as full evidence for a historical
  daemon miss replay.

### Requirement: Daemon Write-Lock Wait Path Does Not Self-Terminate

The Router daemon SHALL treat recoverable runtime ledger write locks as deferred
progress, including write locks encountered while recording wait status.

#### Scenario: Scheduler ledger write is temporarily blocked

- **WHEN** a daemon tick attempts to update `router_scheduler_ledger.json`
- **AND** the runtime JSON writer reports a write-in-progress condition for that
  ledger
- **THEN** the daemon records or returns a deferred tick for runtime ledger
  settlement
- **AND** it SHALL NOT release the daemon lock with `daemon_error`.

#### Scenario: Run state is locked while recording write-lock wait status

- **WHEN** daemon tick work raises `RouterLedgerWriteInProgress`
- **AND** the daemon's recovery/status path also hits
  `RouterLedgerWriteInProgress` for `router_state.json`
- **THEN** the daemon keeps the run in a deferred runtime write-lock wait
- **AND** it SHALL NOT convert the nested wait into a fatal daemon error.

#### Scenario: Dead-owner lock takeover rejoins daemon flow

- **WHEN** a runtime JSON write lock is owned by a dead process
- **THEN** takeover evidence is recorded
- **AND** the daemon resumes normal replay or terminal reconciliation from
  persisted state after the lock is cleared.

### Requirement: Self-Owned Stale Write-Lock Recovery Rejoins Daemon Flow

The Router daemon SHALL treat its own stale runtime JSON write-lock sentinel as
a recoverable mechanical persistence condition only after safe artifact checks.

#### Scenario: Daemon encounters its own stale lock

- **WHEN** the daemon needs to write a runtime JSON ledger
- **AND** the existing `.write.lock` names the same daemon process
- **AND** the lock is stale, target JSON is parseable, and no temp write
  artifact remains
- **THEN** the daemon records self-owned stale-lock recovery evidence
- **AND** clears the stale sentinel
- **AND** retries the write or replay step without creating a second daemon.

#### Scenario: Daemon encounters another live process lock

- **WHEN** the daemon needs to write a runtime JSON ledger
- **AND** the existing `.write.lock` names a different live process
- **THEN** the daemon defers progress as runtime write settlement
- **AND** it SHALL NOT clear the other process's lock.

#### Scenario: Self-owned recovery is unsafe

- **WHEN** the daemon sees its own stale lock
- **AND** target JSON is not parseable or temp write artifacts remain
- **THEN** the daemon does not clear the lock automatically
- **AND** the condition remains a mechanical runtime settlement blocker until
  repair evidence exists.
