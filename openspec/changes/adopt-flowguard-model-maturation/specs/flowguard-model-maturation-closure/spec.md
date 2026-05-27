## ADDED Requirements

### Requirement: FlowPilot Runs Model Maturation Before Broad Confidence
FlowPilot SHALL run a FlowGuard model maturation closure gate before claiming broad maintenance, install, release, or full-model confidence from model, test, mesh, or background evidence.

#### Scenario: Open maturation signal scopes confidence
- **WHEN** current model, test, mesh, code-boundary, or freshness evidence contains an unresolved required maturation signal
- **THEN** FlowPilot reports scoped confidence and lists the required model action before claiming broad confidence

#### Scenario: No maturation signal allows full confidence
- **WHEN** all in-scope required maturation signals are resolved and current
- **THEN** FlowPilot may report full confidence for the bounded claim covered by those signals

### Requirement: Maturation Gate Emits Concrete Model Actions
The model maturation gate SHALL map every current signal to concrete actions: add state field, add transition case, add invariant, add same-class scenario, add code-boundary observation, add model obligation, split child model, reattach parent model, refresh evidence, or downgrade claim.

#### Scenario: Coarse state signal becomes model action
- **WHEN** a signal says a modeled state is too coarse
- **THEN** the gate emits `add_state_field` or another explicit model-upgrade action instead of only reporting a generic gap

#### Scenario: Stale evidence signal becomes refresh action
- **WHEN** a model or checker artifact is newer than the result being consumed
- **THEN** the gate emits `refresh_evidence` and blocks unscoped confidence until fresh evidence exists

### Requirement: Maturation Evidence Is Install-Visible
FlowPilot SHALL make the focused model maturation result visible to local install readiness checks and maintenance documentation.

#### Scenario: Install check validates maturation artifact
- **WHEN** local install readiness is checked
- **THEN** the check verifies the model maturation checker, result artifact, and successful current decision boundary exist

#### Scenario: Missing maturation artifact blocks readiness
- **WHEN** the maturation checker or result artifact is missing
- **THEN** install readiness fails or reports an explicit scoped confidence gap
