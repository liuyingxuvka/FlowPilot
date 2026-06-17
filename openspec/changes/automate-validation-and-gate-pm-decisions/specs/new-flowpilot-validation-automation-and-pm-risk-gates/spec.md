## ADDED Requirements

### Requirement: Ordinary reviewer pass records system validation evidence
The fresh FlowPilot runtime SHALL record validation evidence automatically
after a reviewer pass on an ordinary subject packet, without issuing a
validator AI work packet on the ordinary success path.

#### Scenario: Reviewer pass skips validator packet
- **WHEN** a task packet result has matching FlowGuard evidence
- **AND** the reviewer packet result records `pass`
- **THEN** the runtime MUST record a passed validation evidence row owned by
  the system
- **AND** the runtime MUST issue a closure packet
- **AND** the runtime MUST NOT issue a new validator packet for that ordinary
  success path.

#### Scenario: System validation is not terminal closure
- **WHEN** system validation evidence is recorded
- **THEN** final completion MUST still require a closure packet result
- **AND** closure blockers MUST still reject active blockers, missing
  FlowGuard evidence, missing reviewer acceptance, stale evidence, and
  non-passing validation evidence.

### Requirement: Legacy validation packets remain enforceable
The runtime SHALL continue to parse and enforce validation packet pass/fail
outcomes for existing validation packets and repair paths.

#### Scenario: Existing validation failure remains blocking
- **WHEN** an existing validation packet result says validation failed
- **THEN** the runtime MUST record failed validation evidence
- **AND** the runtime MUST NOT issue closure from that failed validation result
- **AND** the runtime MUST create an active blocker that requires validator
  recheck or a PM-authorized compatible repair path.

### Requirement: PM continue-repair decisions are gated before application
The runtime SHALL stage PM repair decisions that continue repair work until
FlowGuard, reviewer, system validation, and closure gates pass for the PM
decision.

#### Scenario: PM current-scope repair waits for gates
- **WHEN** PM submits a repair decision with `repair_current_scope`
- **THEN** the runtime MUST record the PM decision as staged
- **AND** the runtime MUST issue a FlowGuard packet for the PM decision
- **AND** the runtime MUST NOT open the resulting repair work before the PM decision gate is
  closed.

#### Scenario: PM route redesign waits for gates
- **WHEN** PM submits a repair decision with `redesign_route`
- **THEN** the runtime MUST record the PM decision as staged
- **AND** the runtime MUST issue a FlowGuard packet for the PM decision
- **AND** the runtime MUST NOT mutate the route before the PM decision gate is
  closed.

### Requirement: Route-mutating PM disposition decisions are gated before application
The runtime SHALL stage PM disposition decisions that mutate route structure
until FlowGuard, reviewer, system validation, and closure gates pass for the
PM disposition.

#### Scenario: PM node route mutation waits for gates
- **WHEN** PM submits a node disposition with `mutate_route`
- **THEN** the runtime MUST record the PM disposition as staged
- **AND** the runtime MUST issue a FlowGuard packet for the PM disposition
- **AND** the route version MUST NOT change before the PM disposition gate is
  closed.

#### Scenario: PM node accept remains direct after node closure
- **WHEN** PM submits a node disposition with `accept` after the node work has
  completed its required gates
- **THEN** the runtime MAY accept the node directly
- **AND** no extra PM decision gate is required.
