## ADDED Requirements

### Requirement: Runtime Ledger Authority

The clean runtime SHALL treat the project black-box ledger as the single source
of truth for route state, lease state, packet state, review state, FlowGuard
state, console status, and final closure.

#### Scenario: Chat memory claims completion

- **GIVEN** chat memory or an agent message claims a task is complete
- **AND** the ledger lacks a current accepted result, independent review, and
  required FlowGuard evidence for the packet
- **WHEN** the router selects the next action
- **THEN** the router MUST keep the packet incomplete.

### Requirement: Dynamic Agent Lease Runtime

The runtime SHALL lease agents on demand by responsibility and SHALL allow
leases to be closed, expired, replaced, or superseded without requiring a fixed
number of permanent roles.

#### Scenario: Closed lease returns output

- **GIVEN** a lease is closed, expired, or superseded
- **WHEN** that lease submits output
- **THEN** the output MUST be recorded as non-authoritative
- **AND** the router MUST require a current lease/result before acceptance.

### Requirement: ACK And Progress Are Liveness Only

The runtime SHALL treat ACK and progress as liveness evidence only.

#### Scenario: ACK-only worker

- **GIVEN** a worker ACKs a packet
- **AND** no valid result packet is submitted before timeout
- **WHEN** the router evaluates the packet
- **THEN** the packet MUST remain incomplete
- **AND** the lease MUST be retryable, expired, or replaced.

### Requirement: Sealed Packet Envelope And Body

The runtime SHALL store task and result packets as envelope/body pairs and
SHALL hash bodies so public routing can inspect envelopes without reading
sealed contents.

#### Scenario: Console renders packet status

- **GIVEN** a packet has a private body
- **WHEN** the public console renders status
- **THEN** it MAY show envelope metadata and state
- **AND** it MUST NOT show sealed task or result body text.

### Requirement: FlowGuard Work-Order Scheduler

The runtime SHALL create FlowGuard work orders with an explicit modeled target
and SHALL select the FlowGuard skill from that target.

#### Scenario: Wrong modeled target is green

- **GIVEN** the needed risk is `development_process`
- **AND** a FlowGuard report models `target_product_behavior`
- **WHEN** final closure is attempted
- **THEN** the report MUST NOT satisfy the development-process gate.

### Requirement: Independent Review Gate

The runtime SHALL require independent review before accepting a packet result.

#### Scenario: Worker self-reviews

- **GIVEN** a result was produced by lease A
- **WHEN** a review for that result is also produced by lease A or the same
  agent identity
- **THEN** the review MUST be rejected
- **AND** the result MUST remain unaccepted.

### Requirement: Route Mutation Quarantine

The runtime SHALL prevent old route outputs from silently satisfying the active
route after a route mutation.

#### Scenario: Old route packet returns late

- **GIVEN** route version 1 issued a packet
- **AND** route version 2 becomes active
- **WHEN** the old packet result returns without explicit rebinding
- **THEN** the result MUST be recorded as stale or quarantined
- **AND** it MUST NOT close route version 2.

### Requirement: Evidence Freshness Gate

The runtime SHALL compare result evidence generation with the latest source and
route generation before acceptance.

#### Scenario: Evidence predates source change

- **GIVEN** a result cites evidence from generation 1
- **AND** the source generation is now 2
- **WHEN** review or closure evaluates the result
- **THEN** the evidence MUST be stale
- **AND** the result MUST remain blocked or explicitly scoped.

### Requirement: Final Backward Closure

The runtime SHALL close only by walking backward from the user goal through the
active route, accepted packets, independent reviews, matching FlowGuard
reports, fresh validation evidence, and explicit gaps.

#### Scenario: Missing backward chain

- **GIVEN** a project has a result
- **AND** no current backward closure chain links it to the user goal and
  validation evidence
- **WHEN** completion is attempted
- **THEN** the runtime MUST refuse final completion.

### Requirement: Release Evidence Gate

The runtime SHALL distinguish routine model/test evidence from release
confidence evidence.

#### Scenario: Background or install evidence is not run

- **GIVEN** routine runtime checks pass
- **AND** background Meta/Capability regressions or install parity checks are
  missing, stale, skipped, failed, or progress-only
- **WHEN** release confidence is claimed
- **THEN** the release gate MUST remain blocked.
