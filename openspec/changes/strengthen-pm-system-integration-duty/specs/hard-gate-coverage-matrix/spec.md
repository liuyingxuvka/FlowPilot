## ADDED Requirements

### Requirement: Hard gate coverage includes integration underblocking
FlowPilot SHALL include hard-gate coverage for integration defects that must not pass as local completion.

#### Scenario: Parent composition failure is hard
- **WHEN** required child outputs cannot compose into the parent goal
- **THEN** the hard-gate coverage matrix SHALL expect an existing parent repair or route mutation outcome.

#### Scenario: Final root-goal failure is hard
- **WHEN** the delivered artifact is structurally scattered enough that it cannot satisfy root intent
- **THEN** the hard-gate coverage matrix SHALL expect terminal block, repair, route mutation, or model-miss triage.

### Requirement: Hard gate coverage includes integration overblocking
FlowPilot SHALL include hard-gate coverage for advisory integration suggestions that must not become hard blockers.

#### Scenario: Optional concision improvement is not hard
- **WHEN** the artifact passes minimum acceptance but could be made more concise
- **THEN** the matrix SHALL expect PM decision support rather than hard blocker.

#### Scenario: Optional duplicate reduction is not hard
- **WHEN** repeated material is harmless reinforcement rather than conflicting duplication
- **THEN** the matrix SHALL expect PM decision support or nonblocking note rather than hard blocker.

#### Scenario: Runtime mechanical rejection remains limited
- **WHEN** an integration issue is substantive quality feedback and the structured payload is mechanically valid
- **THEN** runtime mechanical rejection SHALL NOT be the expected authority unless an existing runtime contract is actually violated.
