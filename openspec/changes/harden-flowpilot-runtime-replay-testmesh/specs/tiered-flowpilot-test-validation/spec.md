## ADDED Requirements

### Requirement: Runtime replay suites are TestMesh-owned child evidence
FlowPilot SHALL register fake-AI runtime replay suites as TestMesh child
evidence targets, with owned cell ids, current result artifacts, freshness
status, and parent coverage consumption.

#### Scenario: Replay child owner is missing
- **WHEN** a required runtime replay cell has no registered child suite owner
  or current result evidence
- **THEN** the parent coverage claim MUST fail or remain scoped and identify
  the missing child evidence.

#### Scenario: Parent coverage consumes current replay evidence
- **WHEN** all required replay cells have current passing child evidence and no
  stale verifier/source gap
- **THEN** TestMesh and model-test alignment MAY allow the parent matrix to
  count those cells as runtime-replayed non-live control-plane evidence.

### Requirement: Validation distinguishes routine and release evidence
FlowPilot SHALL keep routine local replay evidence, heavyweight background
evidence, install sync evidence, and release/publish evidence separately
visible. Background progress alone SHALL NOT satisfy replay completion.

#### Scenario: Background progress is not replay completion
- **WHEN** a replay or model regression is running in the background and has
  progress output but no final exit/result artifact
- **THEN** the validation report MUST classify it as liveness only, not passing
  evidence.
