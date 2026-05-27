## ADDED Requirements

### Requirement: Current status summary is display-only projection

The current status summary SHALL declare itself as a display-only projection
and SHALL name the Controller action ledger plus Router daemon status as the
authoritative control sources for Controller progress and stop decisions.

#### Scenario: Status summary names projection authority

- **WHEN** Router writes `current_status_summary.json`
- **THEN** the summary includes projection metadata stating that it is not a
  Controller stop authority
- **AND** the summary names the Controller action ledger and Router daemon
  status as authoritative control sources.

#### Scenario: Status update permission is separate from stop permission

- **WHEN** the summary reports that a user/status update may be returned during
  a nonterminal run
- **THEN** it also reports `controller_stop_allowed=false` and
  `nonterminal_controller_must_stay_attached=true`.

### Requirement: Next step projection carries source and freshness

The current status summary SHALL attach source and freshness metadata to its
`next_step` projection so Controller can distinguish executable ledger work
from display-only or stale information.

#### Scenario: Pending action is current

- **WHEN** `next_step` is derived from the current pending Controller action
- **THEN** the summary includes a `source_action_id`, `source_status`, and
  `fresh_for_controller_decision=true`.

#### Scenario: No pending action or completed action projection

- **WHEN** there is no pending executable Controller action or the projected
  action is already done/reconciled
- **THEN** the summary marks `next_step.fresh_for_controller_decision=false`
  and `next_step.display_only=true`.

#### Scenario: Stale next step cannot authorize stop

- **WHEN** `next_step.fresh_for_controller_decision=false`
- **THEN** Controller MUST NOT use `next_step` as evidence that final Controller
  exit is allowed.
