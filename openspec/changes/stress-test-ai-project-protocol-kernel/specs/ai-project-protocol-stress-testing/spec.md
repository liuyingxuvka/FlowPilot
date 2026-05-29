## ADDED Requirements

### Requirement: Fake AI agents are deterministic protocol actors
The system SHALL provide fake AI agent actors that simulate lease lifecycle,
ACK, progress, typed result submission, invalid result shape, timeout, closure,
late output, review behavior, FlowGuard work-order behavior, evidence freshness,
route mutation, and final closure behavior without calling external AI
services.

#### Scenario: ACK-only worker is not completion
- **WHEN** a fake worker sends ACK and progress but no typed result packet
- **THEN** the stress check blocks completion and records the failure as an
  ACK-without-output path.

#### Scenario: Closed worker returns late output
- **WHEN** a fake worker's lease is closed and that worker later submits output
- **THEN** the stress check rejects the late output as non-authoritative.

### Requirement: Multi-round scenarios enforce current lease and route authority
The stress harness SHALL run scripted multi-round scenarios where multiple
leases, packets, route versions, reviews, and evidence generations interact in
one project ledger.

#### Scenario: Replacement worker succeeds after dead worker
- **WHEN** a first worker ACKs and then times out, the lease is closed, and a
  replacement worker receives a new packet on the current route
- **THEN** only the replacement worker's valid, reviewed, fresh result can be
  accepted.

#### Scenario: Old route output appears after route mutation
- **WHEN** the route mutates and an old packet later returns output from the
  previous route version
- **THEN** the stress check blocks that output unless it has been explicitly
  closed, quarantined, or rebound through a current-route packet.

### Requirement: Seeded random long runs are reproducible
The stress harness SHALL run seeded pseudo-random protocol event sequences and
record enough seed and step information to reproduce any violation.

#### Scenario: Random run finds a false acceptance
- **WHEN** a seeded random run reaches accepted status without every acceptance
  gate being satisfied
- **THEN** the runner fails and reports the seed, step index, event, and state
  summary for reproduction.

#### Scenario: Random run remains clean
- **WHEN** all seeded random runs finish without accepting an unsafe state
- **THEN** the result artifact records the seeds, step count, zero violations,
  and pass status.

### Requirement: Historical bad cases are executable replay cases
The stress harness SHALL include named replay cases for known failure families:
ACK without output, closed-agent late output, route mutation stale output,
stale evidence reuse, progress-only background evidence, wrong FlowGuard target,
weak review, self-review, and final closure gap.

#### Scenario: Known bad family is replayed
- **WHEN** the historical replay pack runs
- **THEN** every known bad case is blocked with the expected classification.

### Requirement: FlowGuard model exploration guards protocol acceptance
The stress harness SHALL use the real FlowGuard package to explore the protocol
stress model and assert that completion cannot be reached unless all lease,
packet, route, review, FlowGuard target, freshness, and backward-closure gates
are satisfied.

#### Scenario: FlowGuard detects unsafe completion
- **WHEN** a stress-model state is marked complete without satisfying the full
  acceptance predicate
- **THEN** the FlowGuard invariant fails and the runner reports the violation.

### Requirement: TestMesh evidence controls parent stress confidence
The stress result SHALL include a TestMesh-style evidence matrix with named
child rows for focused kernel compatibility, deterministic multi-round
scenarios, seeded random long runs, historical replay, FlowGuard exploration,
background project regressions, and install-surface parity.

#### Scenario: Child evidence is missing or stale
- **WHEN** any required child evidence row is missing, stale, skipped,
  progress-only, failed, or not run
- **THEN** the parent stress gate is not allowed to report pass.

#### Scenario: All child evidence is current
- **WHEN** every required child evidence row has current passing final evidence
- **THEN** the parent stress gate may report pass.
