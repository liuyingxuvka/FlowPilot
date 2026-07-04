## ADDED Requirements

### Requirement: FlowPilot pointer writes use runtime JSON atomic persistence
FlowPilot SHALL write `.flowpilot/current.json` and `.flowpilot/index.json`
through the Router-owned runtime JSON atomic write lane, including temporary
file write, flush, fsync, atomic replace, and readback verification.

#### Scenario: Current pointer is written during run shell creation
- **WHEN** FlowPilot creates a new run shell and updates `.flowpilot/current.json`
- **THEN** the current pointer write MUST use atomic JSON replacement with
  readback verification
- **AND** readers MUST observe either the prior complete pointer or the new
  complete pointer, never a partial JSON document.

#### Scenario: Run index is written during run shell creation
- **WHEN** FlowPilot updates `.flowpilot/index.json` for a new or refreshed run
- **THEN** the index write MUST use atomic JSON replacement with readback
  verification
- **AND** FlowPilot MUST NOT change `.flowpilot/current.json` to a new run if
  the corresponding index update failed.

#### Scenario: Terminal status refresh updates pointer files
- **WHEN** FlowPilot refreshes current pointer status from the current run ledger
- **THEN** both current and index writes MUST use the same runtime JSON atomic
  persistence lane.
