## ADDED Requirements

### Requirement: Runtime tests cover sequential parent replay review
FlowPilot runtime and route-tier validation SHALL include focused tests for
parent replay review sequencing, missing-review repair action selection,
terminal replay gating, and no-fallback old-state rejection.

#### Scenario: Missing review coverage is required
- **WHEN** the router/runtime tier claims coverage for parent backward replay
- **THEN** the tier SHALL include tests where child replay review is missing,
  top-level replay review is missing, and both are missing simultaneously

#### Scenario: Fake AI covers parent replay review state
- **WHEN** fake-AI E2E rehearsal runs a high-standard recursive route
- **THEN** the fake responder SHALL exercise parent replay raw pass, review
  pass, missing review, duplicate patrol, and terminal replay blocked-before-
  review states

#### Scenario: Old-state fallback is rejected by coverage
- **WHEN** a test fixture presents old or non-current parent replay evidence
- **THEN** FlowPilot SHALL keep it out of current completion evidence
- **AND** the test SHALL assert that no compatibility translation path is used
