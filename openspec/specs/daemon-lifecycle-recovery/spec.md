# daemon-lifecycle-recovery Specification

## Purpose
TBD - created by archiving change daemonize-flowpilot-router. Update Purpose after archive.
## Requirements
### Requirement: Heartbeat supervises daemon lifecycle
FlowPilot heartbeat/manual resume SHALL supervise Router daemon, Controller
executor, and role cohort liveness instead of acting as the normal way to
advance route work.

#### Scenario: Router daemon is alive
- **WHEN** heartbeat/manual resume wakes and finds a live Router daemon for the current run
- **THEN** it MUST NOT start a second Router daemon and MUST reattach Controller to the current Controller action ledger

#### Scenario: Router daemon is dead or stale
- **WHEN** heartbeat/manual resume wakes and finds no live Router daemon or a stale daemon lock
- **THEN** it MUST restart Router daemon from persisted current-run state before asking Controller or roles to continue work

### Requirement: Controller executor recovery
Heartbeat/manual resume SHALL verify that a Controller executor is attached to
the current run's Controller action ledger.

#### Scenario: Controller executor is attached
- **WHEN** heartbeat/manual resume confirms Controller is attached to the active run ledger
- **THEN** it MUST let Controller continue clearing Router-authored actions and MUST NOT manually apply route progress from chat history

#### Scenario: Controller executor is missing
- **WHEN** heartbeat/manual resume cannot verify a live Controller executor attachment
- **THEN** it MUST restore Controller context from current-run state and the Controller action ledger before any route, packet, card, or role work continues

### Requirement: Role cohort recovery remains current-run scoped
Heartbeat/manual resume SHALL restore or replace the six FlowPilot background
roles only from current-run role memory and current-run crew records.

#### Scenario: Role is live
- **WHEN** a role slot is live, current-run scoped, and addressable
- **THEN** recovery MUST preserve that role slot rather than replacing it

#### Scenario: Role is missing or stale
- **WHEN** a role slot is missing, cancelled, stale, unknown, or not addressable
- **THEN** recovery MUST spawn or rehydrate a replacement role from current-run memory before work that depends on that role continues

### Requirement: Terminal cleanup stops daemon mode
Terminal lifecycle events SHALL stop Router daemon mode, Controller ledger
execution, heartbeat continuation, and role activity for the run.

#### Scenario: User requests run stop
- **WHEN** Router records `user_requests_run_stop`
- **THEN** Router MUST write terminal lifecycle state, cancel or supersede pending nonterminal Controller actions, request terminal Controller cleanup actions, stop daemon active ticking, and prevent further route work

#### Scenario: Terminal summary written
- **WHEN** Controller completes the Router-authored terminal summary action
- **THEN** the run MUST remain terminal and heartbeat/manual resume MUST NOT restart Router daemon or rehydrate roles unless the user explicitly starts a new formal FlowPilot run

### Requirement: Recovery never trusts chat history as route state
Heartbeat/manual resume SHALL recover only from current-run persisted state,
daemon status, action ledgers, mailbox evidence, crew memory, and Router
records.

#### Scenario: Chat says work is alive
- **WHEN** chat history or ordinary role chat implies that work is alive but current-run daemon or ledger state cannot prove it
- **THEN** recovery MUST treat the claim as diagnostic only and follow Router daemon and ledger recovery

#### Scenario: Persisted state proves pending work
- **WHEN** current-run persisted state shows pending Controller actions, mailbox waits, packet leases, role reports, or result envelopes
- **THEN** recovery MUST restore Router daemon and Controller ledger execution from those persisted records
