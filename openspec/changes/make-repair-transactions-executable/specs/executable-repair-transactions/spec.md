## ADDED Requirements

### Requirement: PM repair transactions are executable
FlowPilot SHALL require each PM control-blocker repair decision to provide a
`repair_transaction.plan_kind` that Router can validate as executable before
committing the repair transaction.

#### Scenario: Router commits only executable repair decisions
- **WHEN** PM submits a control-blocker repair decision for the active blocker
- **THEN** Router validates the selected `repair_transaction.plan_kind` and commits the transaction only when the plan has a concrete queued action, an existing event producer, a named Router handler, or a terminal stop.

#### Scenario: Router rejects empty waits
- **WHEN** PM submits a repair transaction that asks Router to wait for an event with no current producer or queued action
- **THEN** Router rejects the PM decision and leaves the original control blocker active for a corrected PM decision.

### Requirement: Executable plan kinds have plan-specific fields
FlowPilot SHALL support explicit repair transaction plan kinds for
`operation_replay`, `controller_repair_work_packet`, `packet_reissue`,
`role_reissue`, `router_internal_reconcile`, `await_existing_event`,
`route_mutation`, and `terminal_stop`.

#### Scenario: Operation replay names a replayable operation
- **WHEN** PM selects `operation_replay`
- **THEN** the repair transaction names the recorded operation to replay and Router queues that operation only if it is replayable in the current blocker context.

#### Scenario: Controller repair work packet is bounded
- **WHEN** PM selects `controller_repair_work_packet`
- **THEN** the repair transaction includes allowed reads, allowed writes, forbidden actions, expected success evidence, and blocker output rules before Router creates the Controller work packet.

#### Scenario: Await existing event names a producer
- **WHEN** PM selects `await_existing_event`
- **THEN** Router verifies that a current pending action, role packet, or Router wait target can produce the awaited success event before committing the repair transaction.

#### Scenario: Terminal stop is explicit
- **WHEN** PM selects `terminal_stop`
- **THEN** Router records the terminal stop reason and does not wait for a follow-up repair event.

### Requirement: Legacy event replay cannot create dead waits
FlowPilot SHALL treat legacy `event_replay` repair transactions as a
deprecated compatibility alias for `await_existing_event` only when an existing
producer is present.

#### Scenario: Legacy replay with producer is accepted as compatibility
- **WHEN** PM submits legacy `event_replay` and the awaited event already has a current producer
- **THEN** Router normalizes the transaction to an existing-event wait or records compatibility metadata without creating a new replay mechanism.

#### Scenario: Legacy replay without producer is rejected
- **WHEN** PM submits legacy `event_replay` without an existing producer for the awaited event
- **THEN** Router rejects the repair decision before writing a committed repair transaction.
