# router-external-wait-reconciliation Specification

## Purpose
TBD - created by archiving change router-reconciles-external-wait-events. Update Purpose after archive.
## Requirements
### Requirement: Router closes waits satisfied by recorded external events
Router SHALL close every open `await_role_decision` Controller action row whose `allowed_external_events` contains a recorded external event.

#### Scenario: Newly recorded event satisfies a wait row
- **WHEN** Router records an external event that appears in an open wait row's `allowed_external_events`
- **THEN** Router marks that wait row satisfied from the external event and rebuilds the Controller action ledger

#### Scenario: Already-recorded event repairs stale wait row
- **WHEN** Router receives an idempotent replay of an already-recorded event and a matching wait row is still open
- **THEN** Router closes the matching wait row without recording a duplicate event

#### Scenario: Output-bearing work clears only from output event
- **WHEN** a Controller wait row represents an output-bearing work package for PM, reviewer, officer, or worker
- **AND** the matching output event in `allowed_external_events` is recorded
- **THEN** Router closes the wait row and rebuilds the Controller action ledger
- **AND** ACK evidence alone is not sufficient for this closure.

### Requirement: Router advances only after closing satisfied waits
Router SHALL close satisfied external-event wait rows before exposing a next wait row or next Controller action derived from that event.

#### Scenario: PM repair decision opens a follow-up wait
- **WHEN** Router records `pm_records_control_blocker_repair_decision` and the repair decision requires a follow-up event
- **THEN** the old PM-decision wait is no longer open before Router exposes the follow-up wait

### Requirement: Controller does not own external-event wait progression
Controller SHALL NOT be responsible for deciding that an external-event wait is satisfied.

#### Scenario: Wait closed from Router evidence
- **WHEN** a role or PM event satisfies a wait row
- **THEN** the row records Router-owned reconciliation evidence rather than requiring a Controller receipt

### Requirement: Repair follow-up waits carry producer evidence
Router SHALL expose a post-repair `await_role_decision` row only when the awaited external event has validated producer evidence.

#### Scenario: Follow-up wait records producer evidence
- **WHEN** Router commits a repair transaction that legitimately waits for a follow-up external event
- **THEN** the exposed wait row MUST include the allowed external events and the producer evidence source, such as a current ordinary work packet/result identity, queued Controller action, existing event producer, or bounded repair work packet.

#### Scenario: Empty follow-up wait becomes PM correction
- **WHEN** a committed repair transaction would otherwise expose a follow-up wait with no producer evidence
- **THEN** Router MUST refuse to expose that wait
- **AND** Router MUST require PM to submit a corrected executable repair decision or a supported blocker/terminal outcome.

#### Scenario: Producer evidence is current-packet scoped
- **WHEN** the awaited event is an ordinary research or PM role-work result after repair
- **THEN** Router MUST bind producer evidence to the current run, packet, lease, and required result contract
- **AND** Router MUST NOT accept superseded results, stale global flags, or a retired material generation as producer evidence.

### Requirement: Wait replay distinguishes idempotent package replay from package conflict
Router external-event wait reconciliation SHALL close waits for idempotent PM package-result replays only when the replay matches the already-recorded semantic package identity and conflict evidence.

#### Scenario: Matching replay closes stale wait
- **WHEN** a PM package-result disposition has already been recorded
- **AND** the same package disposition is replayed while a matching wait row remains open
- **THEN** the Router closes the wait row from already-recorded evidence
- **AND** it does not write duplicate package side effects

#### Scenario: Conflicting replay does not close stale wait as success
- **WHEN** a PM package-result disposition has already been recorded
- **AND** a different PM body is submitted for the same semantic package identity while a matching wait row remains open
- **THEN** the Router rejects the conflict instead of closing the wait as a successful replay
- **AND** the run remains blocked until an authorized repair or reissue path handles the conflict

### Requirement: External wait reconciliation enforces role-output contract mode
FlowPilot SHALL reconcile external waits against the expected role-output contract mode before accepting a Router event as satisfying the wait.

#### Scenario: Wait expects role-output runtime envelope
- **WHEN** the active wait expects a registry-backed role-output runtime envelope
- **THEN** Router MUST require a valid runtime envelope and receipt for the expected output contract
- **AND** Router MUST reject or quarantine a plain manual event envelope for the same event

#### Scenario: Wait closes only after transaction completion
- **WHEN** a PM package disposition event is accepted by Router
- **THEN** the external wait MUST remain open until the registered control transaction reaches a complete or quarantined outcome

### Requirement: Resolved external-event waits invalidate matching pending action
Router SHALL invalidate a `pending_action` projection when its referenced Controller action row or Router scheduler row is durably resolved.

#### Scenario: Controller and scheduler rows are resolved
- **WHEN** `router_state.pending_action` references an `await_role_decision` action whose Controller action row is `done` or whose Router scheduler row is `reconciled`
- **THEN** Router MUST clear or ignore that pending action before daemon status, current-work selection, reminder creation, or next-action computation

#### Scenario: Resolved wait has no Router event yet
- **WHEN** a wait row is resolved but Router state does not yet contain the event or flag that explains the resolution
- **THEN** Router MUST run durable event reconciliation before selecting new work and MUST NOT use the stale pending action as the current owner

#### Scenario: Reconciled wait would trigger reminder
- **WHEN** a wait row has already been reconciled from an external event
- **THEN** Router MUST NOT create a role reminder for that wait, even if `pending_action.last_wait_reminder_at` is absent or stale

### Requirement: External wait grouping excludes Router-owned postconditions
FlowPilot SHALL NOT include Router-owned internal postconditions in passive
external-event wait groups.

#### Scenario: Internal postcondition remains unsynced
- **WHEN** an expected event is marked as a Router-owned internal
  postcondition
- **AND** its prerequisite flag is satisfied
- **AND** the event flag is still false
- **THEN** Router MUST route the event through internal postcondition
  reconciliation
- **AND** Router MUST NOT create a Controller `await_role_decision` row for
  that event

### Requirement: Manual event replay does not change ownership
FlowPilot SHALL keep any idempotent manual external-event recording path for a
Router-owned internal postcondition separate from ownership classification, so
that repeated manual replay SHALL NOT make the postcondition a role-owned wait.

#### Scenario: Manual capability sync event is replayed
- **WHEN** `capability_evidence_synced` is manually recorded after its source
  artifacts are valid
- **THEN** Router MAY reuse the same capability sync writer
- **AND** repeated recording MUST remain idempotent
- **AND** the event MUST remain excluded from future passive role waits

