# daemon-projection-reconciliation Specification

## Purpose
TBD - created by archiving change harden-daemon-projection-reconciliation. Update Purpose after archive.
## Requirements
### Requirement: Daemon reconciles Controller-boundary projections before work selection
The Router daemon SHALL reconcile valid Controller-boundary durable evidence
into Router flags before returning an existing pending action or computing a
new Controller action.

#### Scenario: Boundary artifact and ledgers are complete but flags are stale
- **WHEN** a valid Controller-boundary artifact exists, the Controller action
  receipt is done, and the Router scheduler row is reconciled, but Router flags
  still say the Controller role is not confirmed
- **THEN** Router MUST sync the boundary flags and MUST NOT reissue
  `confirm_controller_core_boundary`

#### Scenario: Boundary action and scheduler disagree
- **WHEN** the Controller-boundary action and Router scheduler row disagree
  about reconciliation state
- **THEN** Router MUST surface the projection mismatch to FlowGuard/live
  projection checks instead of treating the boundary as complete

### Requirement: Boundary projection sync is idempotent without pending action
The Router daemon SHALL be able to rebuild Controller-boundary Router flags from
durable evidence even when `pending_action` is empty.

#### Scenario: Completed boundary action is no longer pending
- **WHEN** `pending_action` is empty and durable Controller-boundary evidence is
  valid and reconciled
- **THEN** Router MUST sync the canonical flags/events and continue from the
  next real work item

### Requirement: Daemon sleeps only when no immediate queue work remains
The Router daemon SHALL skip the one-second sleep after a tick only when the
queue stopped because it reached the per-tick action budget.

#### Scenario: Queue reaches per-tick budget
- **WHEN** a daemon tick stops with `queue_stop_reason=max_actions_per_tick`
- **THEN** the daemon MUST immediately begin the next tick unless `max_ticks` or
  terminal status stops it

#### Scenario: Queue reaches a real wait
- **WHEN** a daemon tick stops with `queue_stop_reason=barrier`,
  `queue_stop_reason=no_action`, or `queue_stop_reason=pending_action_changed`
- **THEN** the daemon MUST keep the normal sleep/wait behavior

### Requirement: Focused FlowGuard model guards projection and fast-loop hazards
The focused daemon reconciliation FlowGuard checks SHALL include known-bad
hazards for stale boundary flags, reissued boundary actions, action exposure
without pending action, sleeping after internal queue budget exhaustion, and
fast-looping after a real barrier.

#### Scenario: Known-bad hazards are represented
- **WHEN** the focused FlowGuard runner evaluates its hazard catalog
- **THEN** each known-bad projection or fast-loop hazard MUST be detected by an
  invariant before production code changes are trusted

### Requirement: Terminal projections share one terminal fact
FlowPilot SHALL refresh current-run status, run index, router state, daemon
status, and daemon lock projection from the same terminal lifecycle fact after a
run stop.

#### Scenario: Stop projection is refreshed
- **WHEN** user stop or cancel is recorded for a run
- **THEN** `.flowpilot/current.json`, `.flowpilot/index.json`, the run router
  state, the daemon status, and the daemon lock projection MUST agree that the
  run is terminal or stopped
- **AND** visible next-step text MUST NOT describe creating unsupported
  continuation automation, starting roles, startup intake, or route work as the
  active next task.

#### Scenario: Historical ledger rows remain
- **WHEN** historical Controller ledger rows or retry rows remain after terminal
  projection refresh
- **THEN** they MAY remain as history
- **AND** they MUST be marked cancelled, superseded, terminal-only, or otherwise
  not active for nonterminal execution.

### Requirement: Daemon reconciles direct role-output events before work selection
The Router daemon SHALL fold every authorized direct role-output event from durable role-output storage into canonical Router events, flags, and registered side-effect projections before returning an existing pending action or computing new work.

#### Scenario: Material review event exists only in role output ledger
- **WHEN** a valid `material_sufficiency_report` direct role output declares `reviewer_reports_material_insufficient`, the matching Controller action row is done, and the matching Router scheduler row is reconciled, but Router state lacks the material review event and flag
- **THEN** Router MUST record the canonical event, sync `material_review` and `material_review_insufficient`, expose the PM repair or research branch, and MUST NOT continue projecting the old Reviewer wait

#### Scenario: Generic direct role event is replayed
- **WHEN** a valid direct role-output event was already folded into Router state and the same durable role-output evidence is seen again
- **THEN** Router MUST treat the replay as idempotent and MUST NOT record a duplicate event or duplicate side effect

#### Scenario: Invalid or unauthorized direct role event exists
- **WHEN** a role-output ledger entry is missing runtime validation, declares an event that is not expected for the active wait, or violates the role-output contract
- **THEN** Router MUST NOT fold it into canonical Router events and MUST surface a control-plane blocker or conservative waiting state

### Requirement: Daemon clears stale waits after internal evidence appears
The Router daemon SHALL reconcile stale Controller wait/projection rows when
authoritative Router-owned internal postcondition evidence exists.

#### Scenario: Old wait remains after capability sync evidence
- **WHEN** `capabilities/capability_sync.json` exists and validates
- **AND** `capability_evidence_synced` is recorded or can be reclaimed from the
  artifact
- **AND** an open or blocked Controller wait/reminder still names
  `capability_evidence_synced`
- **THEN** Router MUST mark that projection resolved from Router-owned evidence
- **AND** Router MUST NOT keep reporting that the Controller or reviewer is the
  missing actor for the already-satisfied postcondition
