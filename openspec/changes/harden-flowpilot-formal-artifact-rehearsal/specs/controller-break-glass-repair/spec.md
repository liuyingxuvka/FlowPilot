## ADDED Requirements

### Requirement: Break-glass threshold covers same-family mechanical artifact loops
FlowPilot SHALL route repeated same-family formal-artifact mechanical failures
to the existing Controller break-glass lane at the fifth same failure while
preserving normal current-contract repair attempts before that threshold.

#### Scenario: Mechanical artifact loop reaches break-glass on fifth attempt
- **WHEN** the same current repair lineage repeats the same formal-artifact
  mechanical failure five consecutive times
- **THEN** Runtime MUST expose a Controller break-glass required action using
  the existing break-glass lane
- **AND** the break-glass evidence MUST identify the repeated mechanical
  failure family, missing artifact or field, and affected packet lineage.

#### Scenario: Successful artifact repair resets the loop
- **WHEN** a formal-artifact mechanical failure is followed by a current
  accepted result for the same packet family
- **THEN** the same-failure break-glass counter MUST reset or close for that
  lineage
- **AND** a later different failure MUST NOT inherit the prior attempt count.
