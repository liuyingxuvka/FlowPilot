# startup-scheduler-barrier-classification Specification

## Purpose
TBD - created by archiving change classify-startup-scheduler-barriers. Update Purpose after archive.
## Requirements
### Requirement: Router classifies scheduling progress by dependency semantics

FlowPilot SHALL decide whether queue filling can continue from an action's
scheduling semantics, not only from broad action mechanics such as payload,
display confirmation, host spawn, or host automation requirements.

#### Scenario: Broad mechanics do not automatically stop independent startup queueing

- **WHEN** Router enqueues a startup action that requires payload, host spawn,
  host automation, or display confirmation
- **AND** that action is classified as a parallel obligation or local
  dependency
- **THEN** Router MAY continue queueing unrelated startup work
- **AND** Router MUST keep the action's evidence obligation unresolved until
  the required proof is recorded.

#### Scenario: True barriers still stop queueing

- **WHEN** Router reaches user input, terminal work, a control blocker,
  resume/rehydration, a non-startup ACK/result wait, or current-scope
  reconciliation
- **THEN** Router MUST stop queueing unrelated work
- **AND** the stopped reason MUST remain visible as the current wait or barrier.

### Requirement: Startup parallel obligations join before Reviewer startup review

FlowPilot SHALL allow startup banner, heartbeat binding, and startup
display/status obligations to run in parallel with unrelated startup work, but
SHALL reconcile them before Reviewer live startup fact review.

#### Scenario: Parallel startup obligation remains open while unrelated work is queued

- **WHEN** a startup banner, heartbeat binding, or startup display/status row
  is already scheduled but not yet reconciled
- **AND** Router can enqueue an unrelated startup action
- **THEN** Router MAY enqueue the unrelated action
- **AND** it MUST NOT mark the open obligation complete without its required
  Router-visible proof.

#### Scenario: Reviewer review waits for parallel obligations

- **WHEN** any startup parallel obligation remains unresolved
- **AND** Router would otherwise deliver `reviewer.startup_fact_check` or
  accept `reviewer_reports_startup_facts`
- **THEN** Router MUST return startup current-scope reconciliation instead
- **AND** startup facts MUST remain unreported.

### Requirement: Startup role-slot spawn is a local dependency

FlowPilot SHALL treat startup role-slot spawn as a local dependency rather than
as a global queue barrier.

#### Scenario: Role spawn does not block unrelated startup work

- **WHEN** startup role-slot spawn is scheduled but not reconciled
- **AND** the next startup work does not require role ids, role liveness, role
  memory injection, or role card delivery
- **THEN** Router MAY enqueue that unrelated work.

#### Scenario: Role-dependent work waits for role slots

- **WHEN** startup role-slot spawn is not reconciled
- **AND** Router would otherwise deliver role-dependent cards, role memory, role
  freshness review, or role-addressed startup work
- **THEN** Router MUST wait on the role-slot dependency instead of delivering
  that role-dependent work.

### Requirement: Startup receipts update bootstrap and scheduler state atomically

FlowPilot SHALL consume done startup Controller receipts by synchronizing all
Router-owned startup state before scheduling the next row.

#### Scenario: Done startup receipt advances all authoritative state

- **WHEN** Router consumes a done startup Controller receipt
- **THEN** Router updates the matching startup flag
- **AND** clears matching bootstrap `pending_action`
- **AND** marks the matching Router scheduler row reconciled
- **AND** does not reissue the same action idempotency key
- **AND** computes the next startup row unless a true barrier has been reached.

#### Scenario: Reconciled scheduler row is monotonic

- **WHEN** a Router scheduler row is already reconciled
- **AND** a later receipt synchronization sees the same Controller receipt
- **THEN** Router MUST NOT downgrade the scheduler row to `receipt_done` or
  another less-complete status.

### Requirement: Focused validation records heavy-check skips explicitly

FlowPilot SHALL not report heavyweight meta or capability regressions as passed
when they were intentionally skipped.

#### Scenario: User requests focused checks only

- **WHEN** the user asks to skip `run_meta_checks.py` and
  `run_capability_checks.py`
- **THEN** final validation evidence MUST list them as skipped by explicit user
  request
- **AND** focused FlowGuard and runtime tests for the touched behavior MUST
  still run before implementation is considered complete.
