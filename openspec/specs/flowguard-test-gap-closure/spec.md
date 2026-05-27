# flowguard-test-gap-closure Specification

## Purpose
TBD - created by archiving change close-flowguard-test-gaps. Update Purpose after archive.
## Requirements
### Requirement: Inventory Gap Classes Are Test-Owned

FlowPilot SHALL keep every gap class from the full FlowGuard coverage inventory
assigned to an ordinary test strategy.

#### Scenario: gap classes are present

- **WHEN** the full model coverage inventory reports prioritized gap groups
- **THEN** the ordinary test suite SHALL fail if any reported gap class is not
  assigned to a known closure strategy.

### Requirement: Abstract Model Runners Have Ordinary Test Evidence

FlowPilot SHALL provide ordinary test evidence for every runner reported as
`abstract_without_detected_ordinary_test_reference`.

#### Scenario: abstract runner has no ordinary evidence

- **WHEN** a runner appears in the abstract-without-test-reference group
- **THEN** the focused coverage-gap tests SHALL either execute that runner,
  inspect its result contract, or assert a deliberate scoped boundary for it.

### Requirement: Scoped Replay Gaps Stay Visible

FlowPilot SHALL not report missing or scoped replay adapters as passed tests.

#### Scenario: replay adapter is scoped out

- **WHEN** a model runner reports skipped replay evidence
- **THEN** an ordinary test SHALL assert that the skip is visible and classified
  as scoped evidence rather than pass evidence.

### Requirement: Not-OK Runners Are Failure Sentinels

FlowPilot SHALL preserve ordinary tests that expose current not-OK and unparsed
runner states until those underlying issues are repaired.

#### Scenario: runner is not OK or unparsed

- **WHEN** a model runner is not OK or cannot be parsed
- **THEN** the focused coverage-gap tests SHALL fail if that diagnostic is
  accidentally dropped without the inventory and result artifacts becoming
  genuinely green.
