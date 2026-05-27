## ADDED Requirements

### Requirement: Oversized Parents Expose Child Maturation Status
FlowPilot parent model hierarchy SHALL expose child-level model maturation status for oversized parent families before parent confidence is promoted.

#### Scenario: Parent has unresolved child maturation signal
- **WHEN** a Meta, Capability, control-plane friction, or other oversized parent consumes child evidence with an unresolved required maturation signal
- **THEN** parent confidence is scoped until the child action is resolved or explicitly out of scope

#### Scenario: Parent consumes current child maturation evidence
- **WHEN** all child evidence ids are current and no required maturation signal is open
- **THEN** the parent hierarchy may treat the child as current for the bounded parent claim

### Requirement: Parent Maturation Keeps Thin And Full Evidence Distinct
FlowPilot SHALL distinguish routine thin-parent maturation evidence from full legacy parent regression evidence.

#### Scenario: Thin parent passes while full regression is stale
- **WHEN** thin parent and maturation checks pass but full parent regression proof is stale, missing, or deferred
- **THEN** FlowPilot reports routine confidence separately from release-level full-regression confidence
