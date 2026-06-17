## ADDED Requirements

### Requirement: Historical Success Is Process Baseline

The historical run `run-20260613-140526` SHALL be used as a process-route
baseline, not an exact field-shape baseline. Tests SHALL prove the successful
mainline is not blocked by fields moved or deleted from early packets.

#### Scenario: Historical mainline is replayed
- **WHEN** the replay suite loads the historical successful run
- **THEN** it SHALL verify that the mainline package order remains compatible
  with the reduced current lifecycle

### Requirement: Later Failure Is One Regression Among All Families

The later first-packet failure SHALL be covered as a regression, but coverage
SHALL also include every packet family in the mainline lifecycle.

#### Scenario: First-packet failure replayed
- **WHEN** the replay suite loads the later failing run
- **THEN** it SHALL classify the early terminal-evidence blocker as invalid
  under the reduced high-standard contract

#### Scenario: All packet families covered
- **WHEN** the replay suite reports coverage
- **THEN** it SHALL include high standard, discovery, skill standard, planning,
  node acceptance plan, node result, FlowGuard check, Reviewer review, PM
  repair, PM disposition, parent replay, and terminal replay families
