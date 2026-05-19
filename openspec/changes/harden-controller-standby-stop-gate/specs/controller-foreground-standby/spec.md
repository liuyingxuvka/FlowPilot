## ADDED Requirements

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
