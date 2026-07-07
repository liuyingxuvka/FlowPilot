## ADDED Requirements

### Requirement: Fake reviewer profiles cover specific and generic behavior
FlowPilot SHALL extend contract-driven fake AI review-window behavior so tests
exercise both stage-specific Reviewer challenge and low-quality generic
Reviewer output.

#### Scenario: Specific challenge profile is generated
- **WHEN** fake AI generates a legal Reviewer pass for a declared review window
- **THEN** the payload SHALL include current-stage challenge text that names
  the review flow, reviewed object, weakest evidence or failure hypothesis, and
  PM-actionable decision support.

#### Scenario: Generic optimization profile is represented as bad behavior
- **WHEN** fake AI represents a low-quality generic review
- **THEN** the payload SHALL expose that the review copied mechanical pass
  style, omitted stage-specific challenge, or gave only generic optimization
  advice
- **AND** focused tests SHALL detect that behavior as a coverage case without
  adding production result fields.

### Requirement: Review-window Cartesian coverage remains exhaustive
FlowPilot SHALL preserve full Cartesian fake-AI coverage for declared review
flows, fake-AI profiles, material-state classes, and retry-count classes.

#### Scenario: Every cell exists
- **WHEN** the fake-AI review-window behavior matrix is enumerated
- **THEN** every
  `review_flow_id x fake_ai_profile x material_state_class x retry_count_class`
  cell SHALL exist.

#### Scenario: New profiles participate in retry coverage
- **WHEN** a new fake-AI reviewer profile is added
- **THEN** it SHALL be included across every declared material-state and retry
  class
- **AND** fifth same-failure retry cells SHALL still project the existing
  break-glass threshold behavior.
