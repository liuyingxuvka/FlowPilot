## ADDED Requirements

### Requirement: Fake AI replay covers current-shaped contradictory FlowGuard results
FlowPilot SHALL include fake AI replay cases where a FlowGuard result uses the
current JSON shape but contradicts its own hard evidence, and those cases MUST
fail before route progress or Reviewer dispatch.

#### Scenario: Current-shaped failed self-check is rejected
- **WHEN** fake AI submits a FlowGuard result with all required current fields
- **AND** top-level `passed` is true
- **AND** the contract self-check says required fields or runtime mechanical
  validation failed
- **THEN** runtime MUST reject or block the result
- **AND** the fake run MUST NOT advance to Reviewer.

#### Scenario: Current-shaped blocked child evidence is rejected
- **WHEN** fake AI submits a FlowGuard result with all required current fields
- **AND** top-level `passed` is true
- **AND** a child evidence report says blocked or revalidation required
- **THEN** runtime MUST reject or block the result
- **AND** the fake run MUST NOT advance to Reviewer.

#### Scenario: Corrected current FlowGuard result can recover
- **WHEN** fake AI later submits a current FlowGuard result whose top-level
  outcome, self-check, and child hard evidence statuses all pass
- **THEN** runtime MAY accept that corrected result
- **AND** the run MAY continue through the legal current route.
