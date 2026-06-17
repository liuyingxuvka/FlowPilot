## ADDED Requirements

### Requirement: Hard-gate matrix covers terminal repair-return loop
FlowPilot hard-gate coverage SHALL include evidence for the complete terminal
final-review rejection repair loop, not only the first blocker branch.

#### Scenario: Full terminal blocker repair evidence exists
- **WHEN** model-test alignment claims terminal replay blocker handling is
  covered
- **THEN** the evidence MUST include an observed-regression test for terminal
  block -> PM repair -> terminal rerun -> blocker clear -> closure
- **AND** the evidence MUST include a fake E2E or current-contract public-path
  test that exercises the same class of behavior.
