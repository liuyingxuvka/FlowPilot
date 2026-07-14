# executable-repair-transactions Specification

## Purpose
TBD - created by archiving change make-repair-transactions-executable. Update Purpose after archive.
## Requirements
### Requirement: PM repair transactions are executable
FlowPilot SHALL require each PM control-blocker repair decision to provide a
`repair_transaction.plan_kind` that Router can validate as executable before
committing the repair transaction, and FlowPilot SHALL keep multi-round fake AI
rehearsal evidence for repair decisions that would otherwise create a
no-producer follow-up wait.

#### Scenario: Router commits only executable repair decisions
- **WHEN** PM submits a control-blocker repair decision for the active blocker
- **THEN** Router validates the selected `repair_transaction.plan_kind` and commits the transaction only when the plan has a concrete queued action, an existing event producer, a named Router handler, or a terminal stop.

#### Scenario: Router rejects empty waits
- **WHEN** PM submits a repair transaction that asks Router to wait for an event with no current producer or queued action
- **THEN** Router rejects the PM decision and leaves the original control blocker active for a corrected PM decision.

#### Scenario: Multi-round rehearsal covers no-producer repair waits
- **WHEN** prepared fake AI work packages exercise a bad package followed by a no-producer PM repair decision
- **THEN** the multi-round rehearsal evidence MUST show that the bad repair cannot advance the route
- **AND** the corrected repair MUST demonstrate current producer evidence before the route continues.

### Requirement: Executable plan kinds have plan-specific fields
FlowPilot SHALL support explicit current repair transaction plan kinds for
operation_replay, controller_repair_work_packet, role_reissue,
router_internal_reconcile, await_existing_event, route_mutation, and
terminal_stop. packet_reissue and replacement-packet fields are retired and
MUST be rejected rather than translated into a current plan kind.

#### Scenario: Operation replay names a replayable operation
- **WHEN** PM selects operation_replay
- **THEN** the repair transaction names the recorded operation to replay and Router queues that operation only if it is replayable in the current blocker context.

#### Scenario: Controller repair work packet is bounded
- **WHEN** PM selects controller_repair_work_packet
- **THEN** the repair transaction includes allowed reads, allowed writes, forbidden actions, expected success evidence, and blocker output rules before Router creates the Controller work packet.
- **AND** the repair packet guidance requires fixing and rechecking only defects inside those bounded reads, writes, forbidden actions, and success evidence.

#### Scenario: Await existing event names a producer
- **WHEN** PM selects await_existing_event
- **THEN** Router verifies that a current pending action, role packet, or Router wait target can produce the awaited success event before committing the repair transaction.

#### Scenario: Role reissue and route mutation name current PM producers
- **WHEN** PM selects role_reissue or route_mutation and the transaction will wait for a follow-up event
- **THEN** Router verifies that the current PM-owned output or accepted route mutation creates a concrete producer for that event.

#### Scenario: Terminal stop is explicit
- **WHEN** PM selects terminal_stop
- **THEN** Router records the terminal stop reason and does not wait for a follow-up repair event.

#### Scenario: Retired replacement-packet repair is rejected
- **WHEN** PM submits packet_reissue, replacement_packets, or a replacement-packet spec path or hash
- **THEN** Router rejects the decision before transaction commit
- **AND** Router leaves the current blocker active for a corrected current-contract decision.

### Requirement: Unsupported event replay cannot create dead waits
FlowPilot SHALL reject unsupported `event_replay` repair transactions instead of
treating them as aliases for current repair transactions.

#### Scenario: Unsupported replay with producer is rejected
- **WHEN** PM submits unsupported `event_replay` and the awaited event already has a current producer
- **THEN** Router rejects the repair decision before writing a committed repair transaction
- **AND** Router SHALL NOT normalize the transaction to an existing-event wait.

#### Scenario: Unsupported replay without producer is rejected
- **WHEN** PM submits unsupported `event_replay` without an existing producer for the awaited event
- **THEN** Router rejects the repair decision before writing a committed repair transaction.

### Requirement: Role reissue waits require concrete producers
FlowPilot SHALL NOT commit a role_reissue repair transaction that waits for a role-produced event unless the transaction proves that a concrete current PM producer exists for that awaited event. Worker, Reviewer, FlowGuard Operator, research, and ordinary evidence rework SHALL use the existing current-node, research-package, or PM role-work packet/result/review path rather than a replacement-packet repair branch.

#### Scenario: Role reissue without producer is rejected
- **WHEN** PM submits a control-blocker repair decision with repair_transaction.plan_kind=role_reissue
- **AND** the selected rerun_target is a role-produced event
- **AND** the repair transaction does not bind a current PM producer for that event
- **THEN** Router MUST reject the repair decision before writing a committed repair transaction
- **AND** Router MUST leave the original control blocker active for a corrected PM decision.

#### Scenario: Ordinary role rework uses the existing package path
- **WHEN** Worker, Reviewer, FlowGuard Operator, research, or evidence work must be performed again
- **THEN** PM MUST create or activate that work through the existing current-node, research-package, or PM role-work path
- **AND** Router MUST NOT synthesize a replacement-packet repair transaction or expose a wait before the current producer exists.

### Requirement: PM repair commit exposes only post-decision executable waits
FlowPilot SHALL commit PM control-blocker repair decisions so the PM decision flag, repair transaction, current outcome table, active blocker allowed events, indexes, and daemon-visible run state describe the same post-decision state.

#### Scenario: PM repair decision enables a current follow-up wait
- **WHEN** PM submits a valid current repair decision whose executable plan has a current producer, queued action, Router handler, or terminal stop
- **THEN** Router MUST persist the PM decision flag and transaction before exposing any allowed follow-up event or daemon-computed next action.

#### Scenario: Half-committed repair state is detected
- **WHEN** active blocker records contain allowed events whose required flags or executable producer evidence are absent from current daemon-visible run state
- **THEN** Router MUST treat the projection as invalid and repair or block it without claiming the wait is executable.

### Requirement: Operation replay synthesizes fresh Controller work
FlowPilot SHALL use operation_replay only to synthesize a fresh Controller action from replay intent, the recorded safe operation, and current run state.

#### Scenario: Replayed operation has fresh identity
- **WHEN** Router queues an operation_replay action from a recorded Controller action
- **THEN** the new Controller action MUST have its own action id and scheduler idempotency key
- **AND** the old action id may appear only as audit metadata such as replay_of_controller_action_id.

#### Scenario: Replayed operation uses current packet and route identity
- **WHEN** a replayed operation touches current-node, research, or PM role-work packet/result relay state
- **THEN** Router MUST derive allowed reads, allowed writes, packet ids, lease identity, batch identity where applicable, and route generation from current run state
- **AND** Router MUST reject the replay if it cannot prove that those identities are current.

