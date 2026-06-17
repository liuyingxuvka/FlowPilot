## ADDED Requirements

### Requirement: Reviewer Blocks Current Stage Only

Reviewer gates SHALL remain formal blocking gates. A Reviewer block SHALL name
a fixed blocker class allowed for the current subject family and SHALL point to
the fixed next action declared in the stage matrix.

#### Scenario: Reviewer blocks node execution quality
- **WHEN** a node result lacks current evidence or is progress-only
- **THEN** Reviewer SHALL be able to block with the node-stage current-evidence
  blocker class

#### Scenario: Reviewer tries terminal blocker during preplanning
- **WHEN** Reviewer blocks a preplanning packet for missing terminal replay
- **THEN** Runtime SHALL reject the blocker class because it is not allowed for
  that packet family

### Requirement: Terminal Review Remains Strict

Terminal backward replay SHALL remain the strict final gate for final artifact
evidence, acceptance item closure, route segment replay, and waiver validity.

#### Scenario: Terminal evidence missing
- **WHEN** terminal replay lacks final current evidence for an active
  acceptance item
- **THEN** Reviewer SHALL block terminal completion

