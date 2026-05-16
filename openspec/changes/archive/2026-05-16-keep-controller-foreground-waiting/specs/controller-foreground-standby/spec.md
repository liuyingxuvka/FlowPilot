## ADDED Requirements

### Requirement: Foreground Controller waits while Router daemon owns progress
When the Router daemon is live and the current run is waiting for role output or a future daemon-issued Controller action, the foreground Controller SHALL enter standby instead of ending the user-visible turn.

#### Scenario: Live daemon waits for reviewer output
- **WHEN** Router daemon status reports a live lock and `current_wait.waiting_for_role` is `human_like_reviewer`
- **THEN** foreground Controller standby remains active and reports a nonterminal `waiting_for_role` wait reason

#### Scenario: No manual Router metronome during standby
- **WHEN** foreground Controller is in standby
- **THEN** it MUST NOT call `next` or `run-until-wait` as the normal progress mechanism

### Requirement: Standby exits on real Controller work or unsafe daemon state
Foreground Controller standby SHALL exit only when a daemon-issued Controller action is ready, the run is terminal, user input is required, the daemon lock/status is missing or stale, or an explicit bounded wait expires.

#### Scenario: Controller action wakes standby
- **WHEN** the Controller action ledger contains a pending or in-progress action
- **THEN** standby returns `controller_action_ready` with the pending action ids and ledger path

#### Scenario: Stale daemon exits standby for repair
- **WHEN** the Router daemon lock is missing or stale
- **THEN** standby returns `daemon_stale_or_missing` and does not claim the route is still safely waiting

#### Scenario: Bounded wait expires while daemon is still healthy
- **WHEN** the explicit standby wait limit expires while the daemon is still live and no Controller action is ready
- **THEN** standby returns `timeout_still_waiting` with current wait metadata so Controller can continue standby without driving Router progress

### Requirement: Standby observes only controller-visible metadata
Foreground Controller standby SHALL read only controller-visible daemon status, lock, and action-ledger metadata and SHALL NOT read sealed packet, result, report, or decision bodies.

#### Scenario: Metadata-only standby result
- **WHEN** standby returns because the daemon is waiting for a role
- **THEN** the returned payload includes paths, status, wait labels, and action ids only, not sealed body content
