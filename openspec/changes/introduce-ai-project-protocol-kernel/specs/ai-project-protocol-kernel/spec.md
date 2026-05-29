## ADDED Requirements

### Requirement: Legacy Snapshot Boundary

The protocol work SHALL preserve a legacy source snapshot before new protocol
implementation and SHALL define what may and may not be reused from the old
system.

#### Scenario: Legacy assets are reused

- **GIVEN** a new protocol implementation wants to reuse an old startup panel
  image, icon, wording pattern, or known failure case
- **WHEN** the reuse is recorded
- **THEN** the item MUST be listed as allowed legacy reference material
- **AND** the reuse MUST NOT import old runtime state, stale evidence, or fixed
  role topology.

### Requirement: Black-Box Ledger Authority

The AI project protocol SHALL treat the project black-box ledger as the single
source of truth for route state, agent lifecycle, packet lifecycle, evidence,
review, and final closure claims.

#### Scenario: Chat memory conflicts with ledger state

- **GIVEN** an agent remembers that a packet was completed
- **AND** the black-box ledger does not contain an accepted result packet and
  review for that packet
- **WHEN** the router chooses the next action
- **THEN** the router MUST treat the packet as not complete.

### Requirement: Dynamic Agent Lease Lifecycle

The protocol SHALL lease background agents on demand by responsibility and
SHALL permit lease close, retry, and replacement without treating a fixed set
of named agents as mandatory.

#### Scenario: Agent lease is closed

- **GIVEN** an agent lease has status `closed`, `expired`, or `superseded`
- **WHEN** that agent later submits output
- **THEN** the output MUST NOT become authoritative
- **AND** the router MUST require a new lease or packet before continuing.

### Requirement: ACK Is Liveness Only

The protocol SHALL treat ACK and progress signals as liveness evidence only,
not as completion evidence.

#### Scenario: Agent acknowledges but never returns a result

- **GIVEN** a leased agent sends ACK for a task packet
- **WHEN** the timeout passes without a valid result packet
- **THEN** the packet MUST remain incomplete
- **AND** the agent lease MUST become retryable, expired, or blocked according
  to the route policy.

### Requirement: Sealed Task And Result Packets

The protocol SHALL separate packet envelopes from packet bodies so routing,
worker execution, review, and evidence checks can stay isolated.

#### Scenario: Router receives a result packet

- **GIVEN** a result packet has an envelope and body
- **WHEN** the router updates project state
- **THEN** the router MUST verify envelope fields including packet id, producer
  lease id, route version, output type, touched paths, evidence ids, and
  freshness
- **AND** it MUST NOT mark the packet accepted until the required reviewer and
  FlowGuard evidence gates pass.

### Requirement: Independent Review Gate

The protocol SHALL require an independent review for accepted work and SHALL
reject self-review.

#### Scenario: Worker reviews its own result

- **GIVEN** a result packet was produced by lease A
- **WHEN** the review packet is also produced by lease A or by the same agent
  identity under a non-independent responsibility
- **THEN** the review MUST be rejected
- **AND** the result packet MUST remain unaccepted.

### Requirement: FlowGuard Route Scheduler

The protocol SHALL select FlowGuard routes by the thing being modeled and the
risk being checked.

#### Scenario: Development process risk is checked

- **GIVEN** the risk concerns step order, stale evidence, peer writes,
  validation freshness, or completion claims
- **WHEN** a FlowGuard work order is created
- **THEN** the route MUST select development-process modeling
- **AND** the work order MUST NOT claim to have modeled the target product
  instead of the development process.

### Requirement: Route Version Packet Quarantine

The protocol SHALL quarantine or rebind open packets when a route version
changes.

#### Scenario: Route changes while old packets remain open

- **GIVEN** route version `v1` has open packets
- **WHEN** route version `v2` becomes active
- **THEN** old open packets MUST be closed, quarantined, or explicitly rebound
  with a new envelope
- **AND** output from old packets MUST NOT be accepted into `v2` silently.

### Requirement: Evidence Freshness Gate

The protocol SHALL compare evidence timestamps and source fingerprints against
the latest relevant route, packet, and source changes before accepting a claim.

#### Scenario: Evidence predates a source change

- **GIVEN** a result packet cites validation evidence
- **AND** the evidence was produced before the latest relevant source or route
  change
- **WHEN** the reviewer evaluates the packet
- **THEN** the evidence MUST be marked stale
- **AND** the packet MUST remain blocked or scoped until fresh evidence exists.

### Requirement: Final Backward Closure

The protocol SHALL close a project only by walking backward from the user goal
to route version, packets, reviews, FlowGuard evidence, executable validation,
and remaining gaps.

#### Scenario: Final report lacks backward evidence

- **GIVEN** a final report claims completion
- **WHEN** it cannot link the user goal to accepted packets, independent
  reviews, FlowGuard checks, and fresh executable validation
- **THEN** the project MUST NOT be reported complete.
