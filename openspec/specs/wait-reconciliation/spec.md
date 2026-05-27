# wait-reconciliation Specification

## Purpose
TBD - created by archiving change optimize-flowpilot-wait-reconciliation. Update Purpose after archive.
## Requirements
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

### Requirement: Wait Reconciliation Uses Source Closure Classification
FlowPilot wait reconciliation SHALL settle passive waits, ACK waits, role-output
waits, and scheduler waits from the closure classification of their source
obligation.

#### Scenario: Passive wait settles after source obligation closes
- **WHEN** a passive wait points at an obligation that the closure kernel now
  classifies as `closed_success` or `closed_terminal`
- **THEN** Router settles or supersedes the wait instead of reissuing it

#### Scenario: Source obligation still open keeps wait active
- **WHEN** a wait points at an obligation that the closure kernel classifies as
  `open`, `repair_required`, `invalid_or_incomplete`, or
  `unknown_needs_recheck`
- **THEN** Router keeps the wait visible or routes a repair action according to
  the existing wait contract
