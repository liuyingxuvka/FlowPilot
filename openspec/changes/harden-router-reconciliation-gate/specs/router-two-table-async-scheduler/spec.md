## MODIFIED Requirements

### Requirement: Router daemon queues independent work until a barrier
The Router daemon SHALL reconcile visible tables once per tick and enqueue additional independent Controller rows while no barrier is active.

#### Scenario: Equivalent Controller work in flight
- **WHEN** Router is considering a Controller action whose action type, scope, and registered postcondition match an existing pending, running, waiting, done, or reconciled row
- **THEN** Router MUST classify that existing row before enqueueing
- **AND** Router MUST NOT enqueue another ordinary row for the same work unless the existing row is explicitly terminal-failed and eligible for bounded retry

#### Scenario: Reconciled stateful row with drift blocks duplicate enqueue
- **WHEN** the existing equivalent row is done/reconciled but its Router-owned stateful postcondition flag is false
- **THEN** Router MUST enter reconciliation/repair for that row
- **AND** Router MUST NOT enqueue a fresh ordinary row for the same action in the same scope

#### Scenario: Independent startup work still queues
- **WHEN** a different startup Controller row is pending but the next startup action has a different action type or postcondition and no dependency on the pending row
- **THEN** Router MAY enqueue the independent row according to the existing nonblocking startup rules
