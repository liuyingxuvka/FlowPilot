## MODIFIED Requirements

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
