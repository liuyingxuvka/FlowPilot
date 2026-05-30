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
- **AND** the repair packet guidance requires fixing and rechecking only defects inside those bounded reads, writes, forbidden actions, and success evidence.

#### Scenario: Await existing event names a producer
- **WHEN** PM selects `await_existing_event`
- **THEN** Router verifies that a current pending action, role packet, or Router wait target can produce the awaited success event before committing the repair transaction.

#### Scenario: Terminal stop is explicit
- **WHEN** PM selects `terminal_stop`
- **THEN** Router records the terminal stop reason and does not wait for a follow-up repair event.

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
FlowPilot SHALL NOT commit a `role_reissue` repair transaction that waits for a role-produced event unless the transaction can prove that a concrete producer exists or will be created for that awaited event.

#### Scenario: Role reissue without producer is rejected
- **WHEN** PM submits a control-blocker repair decision with `repair_transaction.plan_kind=role_reissue`
- **AND** the selected `rerun_target` is a role-produced event
- **AND** the repair transaction does not create replacement packets, replay a current operation, reference an existing producer, or provide a bounded work packet that can emit the event
- **THEN** Router MUST reject the repair decision before writing a committed repair transaction
- **AND** Router MUST leave the original control blocker active for a corrected PM decision.

#### Scenario: Material self-check rework uses packet reissue or replay
- **WHEN** worker material-scan results are returned but their result envelopes show failed contract self-checks
- **AND** PM selects same-gate repair so workers must produce corrected `worker_scan_results_returned` evidence
- **THEN** Router MUST require a concrete `packet_reissue`, a current-generation `operation_replay`, a bounded `controller_repair_work_packet`, or an explicit blocker/terminal outcome
- **AND** Router MUST NOT expose a bare wait for `worker_scan_results_returned`.

#### Scenario: Valid packet reissue remains executable
- **WHEN** PM submits a material-scan `packet_reissue` repair transaction with replacement packet specs
- **THEN** Router MUST commit the new packet generation and expose the material packet relay path before waiting for worker results.

### Requirement: PM repair commit exposes only post-decision executable waits
FlowPilot SHALL commit PM control-blocker repair decisions so active blocker
allowed events, repair transaction records, indexes, and daemon-visible
run-state flags describe the same post-decision state.

#### Scenario: PM repair decision enables material recheck events
- **WHEN** PM submits a valid `packet_reissue` repair decision that records
  material recheck events requiring `pm_control_blocker_repair_decision_recorded`
- **THEN** Router MUST persist the PM decision flag before those events are
  exposed as active blocker waits or daemon-computed next actions.

#### Scenario: Half-committed repair state is detected
- **WHEN** active blocker records contain allowed events whose required flags
  are not satisfied in the current daemon-visible run state
- **THEN** Router MUST treat the projection as invalid and repair or block it
  without claiming the wait is executable.

### Requirement: Packet reissue continues material repair work
FlowPilot SHALL continue material repair work after a valid `packet_reissue`
instead of projecting a stale pre-decision wait for PM repair.

#### Scenario: Packet reissue registers fresh producer
- **WHEN** PM commits a valid `packet_reissue` repair transaction with a fresh
  material repair generation
- **THEN** Router MUST expose a next action that either relays or waits on the
  fresh producer evidence for that generation, not an unresolved PM decision.

#### Scenario: Packet reissue producer is missing
- **WHEN** a committed `packet_reissue` lacks the packet, batch, generation, or
  producer evidence required to continue
- **THEN** Router MUST keep or create a control blocker that names the missing
  producer evidence instead of advertising a non-executable wait.

### Requirement: Material packet reissue commits one current generation
FlowPilot SHALL commit material-scan `packet_reissue` repair transactions through the existing repair transaction path as one current material generation across material index, active packet batch, packet ledger projection, and repair transaction metadata.

#### Scenario: Packet reissue supersedes old generation
- **WHEN** PM commits a `packet_reissue` repair transaction for material scan dispatch
- **THEN** Router MUST write a current `packet_generation_id` on the material index and every new material packet record
- **AND** Router MUST supersede prior material-scan packet records so they cannot satisfy current material-scan waits
- **AND** Router MUST update the active material-scan packet batch to reference only current-generation packet ids

#### Scenario: Recheck success belongs to current generation
- **WHEN** Router finalizes a successful material-scan repair recheck
- **THEN** the repair transaction outcome MUST reference the current `packet_generation_id`
- **AND** Router MUST NOT complete the repair transaction from an event or artifact that references a superseded material generation

### Requirement: Operation replay synthesizes fresh Controller work
FlowPilot SHALL use `operation_replay` only to synthesize a fresh Controller action from replay intent and current run state.

#### Scenario: Replayed operation has fresh identity
- **WHEN** Router queues an `operation_replay` action from a recorded Controller action
- **THEN** the new Controller action MUST have its own action id and scheduler idempotency key
- **AND** the old action id may appear only as audit metadata such as `replay_of_controller_action_id`

#### Scenario: Material operation replay uses current generation
- **WHEN** the replayed operation touches material-scan packet or result relay state
- **THEN** Router MUST derive allowed reads, allowed writes, packet ids, and batch identity from the current material generation
- **AND** Router MUST reject the replay if it cannot prove the operation targets the current generation.
