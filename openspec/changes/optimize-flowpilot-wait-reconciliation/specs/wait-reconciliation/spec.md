## ADDED Requirements

### Requirement: Router reconciles durable wait evidence before waiting
The Router SHALL refresh active packet, ACK, result, and controller-status evidence before emitting any wait action for a role or packet batch.

#### Scenario: Existing result satisfies pending wait
- **WHEN** a result envelope already exists for a packet whose wait is still pending
- **THEN** the Router records the packet as returned before selecting the next action

#### Scenario: Stale wait is not reissued
- **WHEN** the previously expected role has already returned valid durable evidence
- **THEN** the next Router action does not ask the Controller to keep waiting for that same completed role

### Requirement: Reconciliation is idempotent
The Router SHALL key reconciliation updates by run id, batch id, packet id, request id, role, and result target so repeated Router ticks do not duplicate counts or side effects.

#### Scenario: Repeated reconciliation tick
- **WHEN** the same valid result envelope is observed on two consecutive Router ticks
- **THEN** the returned count remains one for that packet and no duplicate PM relay or gate advancement is recorded

### Requirement: Reconciliation preserves sealed-packet boundaries
The Router SHALL reconcile only metadata, hashes, envelope paths, status packets, and result references; it MUST NOT read sealed packet or sealed result bodies during wait reconciliation.

#### Scenario: Status refresh with sealed result present
- **WHEN** a sealed result body exists beside a result envelope
- **THEN** the Router updates metadata status without reading or summarizing the sealed result body
