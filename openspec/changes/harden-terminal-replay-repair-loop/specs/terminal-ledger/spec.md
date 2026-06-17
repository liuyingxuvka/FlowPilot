## ADDED Requirements

### Requirement: Terminal replay blocker repair returns to passing replay
FlowPilot terminal ledger state SHALL require a later current passing terminal
backward replay before final closure completes after a terminal replay blocker.

#### Scenario: Terminal repair loop clears blocker before closure
- **WHEN** a mechanically valid terminal backward replay result records
  `passed=false`
- **AND** PM submits a valid current repair decision for that blocker
- **AND** Reviewer later submits a mechanically valid terminal backward replay
  result with `passed=true` for the current runtime-issued targets
- **THEN** runtime MUST clear the terminal blocker
- **AND** runtime MUST record accepted terminal replay closure evidence
- **AND** final closure MAY complete only after all other closure blockers are
  clean.

#### Scenario: Open terminal repair work blocks closure
- **WHEN** a terminal replay blocker has an open current repair or reissue
  packet
- **THEN** FlowPilot MUST NOT treat the route as ready to close
- **AND** the next router action MUST dispatch or recover that current packet
  before attempting `close_project`.
