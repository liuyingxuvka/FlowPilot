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

### Requirement: High-risk PM repair decisions are gated before application
The runtime SHALL stage PM repair decisions that can mutate route state or
waive a blocker until FlowGuard, reviewer, system validation, and closure gates
pass for the PM decision.

#### Scenario: PM route mutation repair waits for gates
- **WHEN** PM submits a repair decision with `mutate_route`
- **THEN** the runtime MUST record the PM decision as staged
- **AND** the runtime MUST issue a FlowGuard packet for the PM decision
- **AND** the runtime MUST NOT mutate the route before the PM decision gate is
  closed.

#### Scenario: PM waiver waits for gates
- **WHEN** PM submits a repair decision with `waive_with_authority`
- **THEN** the runtime MUST record the PM decision as staged
- **AND** the blocker MUST NOT be waived before the PM decision gate is closed.

### Requirement: Low-risk PM repair decisions stay direct
The runtime SHALL apply low-risk PM repair decisions directly when they only
reissue work, collect evidence, rerun a legacy validation packet, quarantine
evidence, or stop for user input.

#### Scenario: PM sender reissue remains direct
- **WHEN** PM submits a repair decision with `sender_reissue`
- **THEN** the runtime MUST issue the fresh repair packet without requiring a
  PM decision FlowGuard gate
- **AND** the original blocker MUST remain active until the required recheck
  role passes.

### Requirement: High-risk PM disposition decisions are gated before application
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
