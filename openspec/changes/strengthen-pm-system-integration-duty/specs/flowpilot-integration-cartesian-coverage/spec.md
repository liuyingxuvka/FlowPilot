## ADDED Requirements

### Requirement: Integration coverage uses declared Cartesian axes
FlowPilot SHALL validate this change with a model-scoped Cartesian matrix that declares finite axes and expected outcomes before claiming broad coverage.

#### Scenario: Matrix declares full integration axes
- **WHEN** integration-duty coverage is generated
- **THEN** it SHALL include stage, role, artifact family, failure class, severity, authority, evidence timing, and outcome axes.

#### Scenario: Matrix covers common artifact families
- **WHEN** the Cartesian matrix is reviewed
- **THEN** it SHALL include software/code, UI/app, writing/report, research/source-backed, and skill/workflow artifact families.

#### Scenario: Matrix covers hard and soft severities
- **WHEN** integration cases are generated
- **THEN** the matrix SHALL include hard-failure, PM-decision-support, and nonblocking-note severities.

### Requirement: Integration coverage tests underblocking and overblocking
FlowPilot SHALL test both missed hard failures and incorrect hard-blocking of advisory integration improvements.

#### Scenario: Hard composition failure cannot pass as advisory
- **WHEN** a required parent or final artifact cannot satisfy the root intent because child outputs do not compose
- **THEN** the expected outcome SHALL be repair, route mutation, model-miss triage, or terminal block.

#### Scenario: Advisory quality improvement cannot become a runtime hard block
- **WHEN** a suggestion improves concision, elegance, ordering, or optional deduplication without proving a current minimum failure
- **THEN** the expected outcome SHALL be PM decision support or nonblocking note, not runtime mechanical rejection.

#### Scenario: Worker remains bounded executor
- **WHEN** a worker result lacks global integration judgement but satisfies its bounded package
- **THEN** the matrix SHALL route the integration judgement to PM absorption, Reviewer replay, or FlowGuard process review rather than requiring the worker to become system integrator.

### Requirement: Coverage evidence is consumed by TestMesh and MTA
FlowPilot SHALL connect generated integration cases to test ownership and model-test alignment evidence before broad claims.

#### Scenario: Cartesian cases have test ownership
- **WHEN** generated Cartesian case ids are required for the claim
- **THEN** TestMesh SHALL identify the owning focused tests or suites for those case ids.

#### Scenario: Cartesian cases bind model obligations
- **WHEN** generated Cartesian case ids represent model obligations
- **THEN** Model-Test Alignment SHALL bind them to the corresponding model obligation, code or prompt contract owner, and current test evidence.
