## MODIFIED Requirements

### Requirement: High-risk exceptional branches require governed replay status

The synthetic agent coverage matrix SHALL classify high-risk exceptional
FlowPilot branches by risk tier and replay requirement.

#### Scenario: P0 branch has synthetic replay evidence

- **GIVEN** a P0 exceptional branch is marked `synthetic_replay_required`
- **WHEN** the coverage matrix is generated
- **THEN** the branch SHALL have a current passing synthetic replay row
- **AND** the row SHALL identify its covered failure mode.

#### Scenario: P0 branch cannot be synthetically replayed

- **GIVEN** a P0 exceptional branch cannot be exercised through current fake AI
  runtime APIs
- **WHEN** the coverage matrix is generated
- **THEN** the branch SHALL be marked `synthetic_replay_status:
  not_replayable`
- **AND** it SHALL provide a non-empty `non_replayable_reason`
- **AND** ordinary runtime/model evidence SHALL remain present.

#### Scenario: Required replay is missing

- **GIVEN** a P0 or P1 row is marked `synthetic_replay_required`
- **AND** no synthetic replay row or non-replayable reason exists
- **WHEN** the coverage matrix is validated
- **THEN** validation SHALL fail with a missing replay finding.

### Requirement: Synthetic exception packages preserve evidence boundaries

Synthetic exception packages SHALL prove only control-flow, runtime contract,
and evidence-boundary behavior.

#### Scenario: Fake package does not claim live AI quality

- **GIVEN** a synthetic or fixture replay row
- **WHEN** the coverage matrix validates evidence boundaries
- **THEN** `live_completion_allowed` SHALL be false
- **AND** the boundary SHALL not claim live AI semantic quality.

#### Scenario: Control blocker package escalates through runtime evidence

- **GIVEN** a fake worker/control-plane scenario reaches retry exhaustion
- **WHEN** the synthetic replay package is executed
- **THEN** it SHALL show the branch blocks or escalates using runtime-visible
  evidence rather than direct hidden state mutation.

#### Scenario: PM repair package rejects invalid targets

- **GIVEN** a fake PM repair decision points to an unregistered, stale, or
  non-receivable target
- **WHEN** the synthetic replay package is executed
- **THEN** the result SHALL be rejected or blocked before writing a successful
  wait/repair completion.

### Requirement: Install and model evidence remain synchronized

After synthetic exception replay changes, the repository SHALL refresh the
affected generated evidence and local installed skill copy.

#### Scenario: Final validation after implementation

- **GIVEN** synthetic exception trace code or matrix logic changed
- **WHEN** final validation is performed
- **THEN** focused synthetic tests, matrix tests, model-test alignment, fast
  tier, relevant router child suites, background Meta/Capability checks, and
  install sync/audit/check SHALL run or be explicitly reported as blocked.
