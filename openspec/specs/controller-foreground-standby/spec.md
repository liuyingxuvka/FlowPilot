# controller-foreground-standby Specification

## Purpose
TBD - created by archiving change keep-controller-foreground-waiting. Update Purpose after archive.
## Requirements
### Requirement: Foreground Controller SHALL wait while Router daemon owns progress
Foreground Controller SHALL enter standby instead of ending the user-visible
turn when the Router daemon is live and the current run is waiting for role
output, a future daemon-issued Controller action, or a Router-authored
wait-target reminder/liveness cycle.

#### Scenario: Live daemon waits for reviewer output
- **WHEN** Router daemon status reports a live lock and `current_wait.target_role`
  is `human_like_reviewer`
- **THEN** foreground Controller standby remains active and reports a nonterminal `waiting_for_role` wait reason

#### Scenario: No manual Router metronome during standby
- **WHEN** foreground Controller is in standby
- **THEN** it MUST NOT call `next` or `run-until-wait` as the normal progress mechanism

#### Scenario: Wait target drives reminder and liveness checks
- **WHEN** foreground Controller is in standby and `current_wait` says a
  reminder or liveness check is due
- **THEN** Controller follows the Router-authored wait target metadata without
  reading sealed bodies or deciding route progress

### Requirement: Standby exits on real Controller work or unsafe daemon state
Foreground Controller standby SHALL exit only when a daemon-issued Controller
action is ready, the run is terminal, user input is required, the daemon
lock/status is missing or stale, a wait-target blocker must be recorded, or an
explicit bounded wait expires.

#### Scenario: Controller action wakes standby
- **WHEN** the Controller action ledger contains a pending or in-progress action
- **THEN** standby returns `controller_action_ready` with the pending action ids and ledger path

#### Scenario: Stale daemon exits standby for repair
- **WHEN** the Router daemon lock is missing or stale
- **THEN** standby returns `daemon_stale_or_missing` and does not claim the route is still safely waiting

#### Scenario: Bounded wait expires while daemon is still healthy
- **WHEN** the explicit standby wait limit expires while the daemon is still live
  and no Controller action, wait-target reminder, or wait-target blocker is due
- **THEN** standby returns `timeout_still_waiting` with current wait metadata so Controller can continue standby without driving Router progress

#### Scenario: Wait target blocker exits standby
- **WHEN** an ACK timeout, lost role, unresponsive role, cancelled role, unknown
  role, or Controller-local action failure is detected from controller-visible
  metadata
- **THEN** standby returns a blocker-needed outcome for the existing Router and
  PM recovery flow

### Requirement: Standby observes only controller-visible metadata
Foreground Controller standby SHALL read only controller-visible daemon status,
lock, action-ledger metadata, wait-target metadata, reminder records, liveness
probe receipts, and blocker envelopes, and SHALL NOT read sealed packet,
result, report, or decision bodies.

#### Scenario: Metadata-only standby result
- **WHEN** standby returns because the daemon is waiting for a role
- **THEN** the returned payload includes paths, status, wait labels, action ids,
  reminder due status, and liveness probe evidence only, not sealed body content

### Requirement: Nonterminal return permission is not Controller stop permission

Foreground Controller standby SHALL distinguish user/status return permission
from Controller stop permission. A nonterminal standby result MAY allow a
status update or required user/liveness/wait-target handling, but it MUST NOT
authorize final Controller exit unless `controller_stop_allowed=true`.

#### Scenario: User input required while daemon run is nonterminal

- **WHEN** standby returns `foreground_required_mode=return_for_user_input` for
  a nonterminal run
- **THEN** the payload reports `user_status_update_allowed=true`,
  `controller_stop_allowed=false`, and `nonterminal_controller_must_stay_attached=true`
- **AND** the payload states that a user/status return does not complete the
  Controller role.

#### Scenario: Waiting standby remains patrol duty

- **WHEN** the Router daemon is live and `continuous_controller_standby` is
  waiting or in progress
- **THEN** standby reports `controller_patrol_required=true` and
  `foreground_exit_allowed=false`
- **AND** Controller must continue patrol or process a Router-exposed duty
  rather than final-answer.

#### Scenario: Stale projection conflicts with ledger

- **WHEN** status or display projection names a completed action while the
  Controller action ledger still contains nonterminal standby duty
- **THEN** Controller standby treats the projection as display-only and keeps
  the ledger/terminal gate as the stop authority.

### Requirement: Final Controller stop requires terminal preflight

Foreground Controller standby SHALL expose a final-answer preflight contract
that requires terminal status, `controller_stop_allowed=true`, no pending
ordinary Controller work, and no in-progress `continuous_controller_standby`.

#### Scenario: Nonterminal standby cannot pass final preflight

- **WHEN** the run is nonterminal and the standby row remains waiting or
  in-progress
- **THEN** final-answer preflight fails even if a user/status return is allowed.

#### Scenario: Terminal run passes final preflight

- **WHEN** the monitored run is terminal, `controller_stop_allowed=true`, and no
  nonterminal Controller ledger row remains active
- **THEN** final-answer preflight allows the foreground Controller to end after
  required terminal cleanup.

### Requirement: Foreground standby pruning preserves state-specific duties

Foreground Controller standby SHALL keep separate Controller-visible duties for
pending Controller work, wait-target check, wait-target blocker, wait-target
reissue, user input, daemon liveness check, terminal stop, and live daemon
watching even when internal branch logic is simplified.

#### Scenario: Wait-target states stay distinct

- **WHEN** standby detects reminder/liveness due, blocker required, or reissue
  required from controller-visible wait metadata
- **THEN** it returns the matching state-specific `foreground_required_mode`
  instead of collapsing all wait-target outcomes into one generic duty.

#### Scenario: Live daemon watching still blocks exit

- **WHEN** standby detects a live daemon with no ready Controller action and no
  wait-target duty
- **THEN** it reports a watch mode, keeps Controller attached, and does not
  authorize final foreground exit.
