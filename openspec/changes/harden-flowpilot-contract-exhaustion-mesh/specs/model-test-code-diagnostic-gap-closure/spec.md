## ADDED Requirements

### Requirement: Diagnostics report contract-exhaustion gaps
The model-test-code diagnostic SHALL report generated contract-exhaustion gaps,
stale matrix evidence, and missing code/test bindings as actionable findings.

#### Scenario: Generated cell has no owner code contract
- **WHEN** a generated contract-exhaustion cell has no owner runtime code
  contract or no current external-contract test evidence
- **THEN** the diagnostic MUST report an actionable gap with the cell id,
  contract family, expected oracle outcome, owner surface, and missing evidence

#### Scenario: Matrix result is stale
- **WHEN** packet/result contracts, FlowGuard evidence policy, reviewer
  manifest behavior, break-glass loop identity, or runtime validation code
  changes after a matrix result was produced
- **THEN** the diagnostic MUST classify the old matrix result as stale rather
  than reusable pass evidence

#### Scenario: Generated owner is not a TestMesh child suite
- **WHEN** a generated contract-exhaustion cell names an evidence owner that is
  absent from the current TestMesh child-suite map
- **THEN** the diagnostic or model-test alignment report MUST expose that
  owner-consumption gap before coverage can be treated as complete

### Requirement: Diagnostics do not accept current live blockers as closed
The diagnostic SHALL distinguish "detected current live blocker" from
"covered and repaired behavior".

#### Scenario: Current run projection finds control-plane stuck
- **WHEN** process liveness, ModelMesh, or coverage inventory reports a current
  `control_plane_stuck` lifecycle guard or equivalent live-runtime finding
- **THEN** the diagnostic MUST keep the finding open until the current runtime
  path repairs or explicitly disposes the run and regenerated evidence removes
  the live-runtime gap
