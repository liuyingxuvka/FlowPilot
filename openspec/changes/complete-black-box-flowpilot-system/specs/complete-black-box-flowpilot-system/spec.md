## ADDED Requirements

### Requirement: Current-Run Ledger Authority

The complete FlowPilot system SHALL treat the current run ledger as the single
source of authority for startup, routes, packets, leases, FlowGuard orders,
reviews, validation evidence, Cockpit projection, lifecycle state, and final
closure.

#### Scenario: Chat or old state claims completion

- **WHEN** chat memory, old `.flowpilot` state, an old agent id, or a stale
  artifact claims that work is complete
- **THEN** the complete runtime MUST keep the work incomplete unless the current
  run ledger contains current accepted results, independent review, matching
  FlowGuard evidence, fresh validation, and final backward closure.

#### Scenario: Continuing prior work

- **WHEN** a new FlowPilot invocation continues prior work
- **THEN** the runtime MUST create a new current run and import prior outputs as
  read-only evidence rather than resuming prior control state as authority.

### Requirement: Dynamic Responsibility Leases

The complete FlowPilot system SHALL lease responsibilities on demand instead of
requiring a fixed permanent role topology as runtime authority.

#### Scenario: Lease expires before result

- **WHEN** a worker, reviewer, PM, or FlowGuard operator lease expires before a
  valid result is committed
- **THEN** the router MUST mark the lease inactive and require replacement,
  repair, or an explicit blocked state before the dependent gate can continue.

#### Scenario: Closed lease submits late output

- **WHEN** a closed, expired, superseded, or wrong-scope lease submits output
- **THEN** the runtime MUST record the output as non-authoritative and MUST NOT
  let it satisfy the current route.

### Requirement: Deterministic Router State Machine

The complete FlowPilot router SHALL choose typed next actions only from the
current ledger state and SHALL NOT perform project work, approve gates, or read
sealed packet/result bodies.

#### Scenario: Packet is waiting on ACK

- **WHEN** the active packet has an assigned live lease but lacks an ACK
- **THEN** the router MUST return a wait-for-ACK action or a timeout action,
  not an acceptance action.

#### Scenario: Packet has ACK but no result

- **WHEN** the active packet has only ACK or progress records
- **THEN** the router MUST keep the packet incomplete and wait, repair, expire,
  or replace the lease.

### Requirement: Sealed Packet And Result Runtime

The complete FlowPilot system SHALL store packet and result bodies separately
from public envelopes and SHALL protect body integrity with hashes.

#### Scenario: Cockpit renders packet list

- **WHEN** Cockpit or chat route status renders active packet information
- **THEN** it MAY show envelope metadata, status, owner responsibility, route
  version, blockers, and hashes
- **AND** it MUST NOT show sealed task or result body text.

#### Scenario: Body hash mismatch

- **WHEN** a result or review references a packet body hash that does not match
  the current body file
- **THEN** the runtime MUST block acceptance and require repair or reissue.

### Requirement: FlowGuard Work-Order Scheduling

The complete FlowPilot system SHALL create explicit FlowGuard work orders with
a modeled target before selecting a FlowGuard skill or accepting a FlowGuard
report.

#### Scenario: Wrong target report

- **WHEN** a gate requires `development_process` evidence
- **AND** a report modeled `target_product_behavior`
- **THEN** the runtime MUST reject the report for that gate even if the report
  says it passed.

#### Scenario: Missing modeled target

- **WHEN** a PM, Controller, or agent asks for FlowGuard work without a modeled
  target
- **THEN** the router MUST block the work order until the target and selected
  route are recorded.

### Requirement: Independent Review And Repair

The complete FlowPilot system SHALL require independent review before accepting
packet results, route mutations, major UI evidence, FlowGuard reports used for
completion, and final closure.

#### Scenario: Self-review attempt

- **WHEN** the same lease or same agent identity produces a result and review
- **THEN** the review MUST be rejected and the result MUST remain unaccepted.

#### Scenario: Reviewer finds route-invalidating issue

- **WHEN** independent review finds that the current route cannot satisfy the
  frozen contract
- **THEN** the PM/router flow MUST mutate, split, repair, or block the route
  and mark affected previous evidence stale.

### Requirement: Cockpit Operation Surface

The complete FlowPilot system SHALL provide a usable startup/status operation
surface that renders current state and submits only typed user events.

#### Scenario: Cockpit unavailable

- **WHEN** the user requested Cockpit but it cannot open
- **THEN** the runtime MUST record a display-surface fallback and require chat
  route-sign/status projection rather than treating Cockpit failure as proof of
  route completion or route blockage.

#### Scenario: Cockpit attempts direct state write

- **WHEN** a UI action attempts to edit route, packet, lease, evidence, or
  closure state directly
- **THEN** the runtime MUST reject the action unless it is represented as a
  typed event consumed by the router.

### Requirement: Full-System Evidence Gate

The complete FlowPilot system SHALL distinguish scoped foundation evidence from
complete-system evidence.

#### Scenario: Fake-agent checks pass

- **WHEN** deterministic fake-agent, unit, or model checks pass
- **THEN** the system MAY claim scoped routine confidence
- **AND** it MUST NOT claim full FlowPilot completion until host integration,
  Cockpit/status evidence, historical replay, install sync, background
  regressions, and required live-run evidence are current.

#### Scenario: Background check has progress only

- **WHEN** a background check has progress logs but lacks final exit and proof
  artifacts
- **THEN** the release/full-system gate MUST remain blocked.

### Requirement: Migration And Cutover

The complete FlowPilot system SHALL keep old runtime surfaces as reference or
diagnostic material until the new complete runtime has passed full-system
evidence gates and install sync.

#### Scenario: Old runtime artifact reused

- **WHEN** old router output, old route file, old screenshot, old result, or
  old UI evidence is reused
- **THEN** it MUST be recorded as imported read-only evidence with provenance
  and MUST NOT become current route authority.

#### Scenario: Public entrypoint cutover

- **WHEN** the public FlowPilot skill entrypoint is changed to prefer the new
  complete runtime
- **THEN** OpenSpec validation, FlowGuard checks, tests, install sync, install
  audit, local install check, and final git evidence MUST be current.
