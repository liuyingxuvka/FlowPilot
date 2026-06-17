## ADDED Requirements

### Requirement: Closure Requires Clean Supplemental Repair State
FlowPilot final closure SHALL require the original frozen contract evidence and
all active terminal supplemental repair contracts to be clean.

#### Scenario: Original contract clean but supplemental contract open
- **WHEN** original contract evidence is clean
- **AND** an active terminal supplemental repair contract has unresolved repair
  items
- **THEN** final closure MUST remain blocked.

#### Scenario: Repair rounds exhausted
- **WHEN** terminal supplemental repair reaches the hard round limit with
  unresolved blocking items
- **THEN** runtime MUST stop with terminal status `repair_rounds_exhausted`
- **AND** runtime MUST NOT claim successful completion.

### Requirement: Completion Report Preserves Exhausted Repair Summary
FlowPilot terminal stopped reports SHALL preserve a controller-visible summary
of unresolved supplemental repair item ids after repair exhaustion without
using that summary as a new repair input.

#### Scenario: Exhausted report is emitted
- **WHEN** runtime stops because terminal supplemental repair rounds are
  exhausted
- **THEN** the terminal report MUST include unresolved supplemental repair item
  ids and contract ids
- **AND** Controller MUST NOT use the report to reopen PM or Reviewer work.
