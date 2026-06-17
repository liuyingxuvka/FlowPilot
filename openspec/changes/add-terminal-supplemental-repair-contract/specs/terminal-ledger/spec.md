## ADDED Requirements

### Requirement: Terminal Ledger Includes Supplemental Repair Closure
FlowPilot terminal final ledger construction SHALL include every active
terminal supplemental repair contract and repair item before closure can pass.

#### Scenario: Supplemental repair item remains unresolved
- **WHEN** a terminal supplemental repair contract has an active repair item
  without current high-quality closure evidence
- **THEN** the final route-wide ledger MUST include an unresolved supplemental
  repair row
- **AND** final closure MUST remain blocked unless runtime has reached
  `repair_rounds_exhausted`.

#### Scenario: Supplemental contract closes
- **WHEN** every active repair item in a terminal supplemental repair contract
  has current passing evidence
- **THEN** the final route-wide ledger MUST mark that supplemental contract as
  closed
- **AND** the final requirement evidence matrix MUST include the matching
  supplemental evidence rows.

### Requirement: Terminal Replay Covers Supplemental Repair Targets
FlowPilot terminal backward replay SHALL include runtime-issued segment targets
for active supplemental repair contracts and repair items.

#### Scenario: Terminal replay omits supplemental repair segment
- **WHEN** runtime issues terminal replay targets containing supplemental repair
  contract or repair item segments
- **AND** Reviewer submits a terminal replay result missing one of those
  segments
- **THEN** runtime MUST mechanically block the terminal replay result
- **AND** final closure MUST remain unavailable.

#### Scenario: Terminal replay passes supplemental repair
- **WHEN** Reviewer submits a terminal replay result covering all original and
  supplemental repair targets with `passed=true`
- **THEN** runtime MAY record accepted terminal replay closure evidence if all
  other closure blockers are clean.
