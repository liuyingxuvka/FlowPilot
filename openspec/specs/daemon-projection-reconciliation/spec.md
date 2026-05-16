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
