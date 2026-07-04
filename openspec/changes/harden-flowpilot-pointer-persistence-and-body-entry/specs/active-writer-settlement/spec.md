## ADDED Requirements

### Requirement: Pointer reads honor active writer settlement
FlowPilot SHALL treat current/index pointer reads with fresh runtime JSON write
locks as settlement-in-progress evidence rather than immediate corruption
evidence.

#### Scenario: Fresh pointer write lock with incomplete target
- **WHEN** `.flowpilot/current.json` or `.flowpilot/index.json` is not parseable
- **AND** the target has a fresh runtime JSON write lock
- **THEN** FlowPilot MUST defer, retry, or report write settlement in progress
- **AND** it MUST NOT classify the pointer as permanently corrupt from that
  transient read alone.

#### Scenario: Dead pointer writer with valid target
- **WHEN** a pointer write lock names a dead owner process
- **AND** the target pointer file is valid JSON
- **THEN** the next Router-owned pointer writer MAY clear the stale lock through
  the existing dead-owner takeover rules.

#### Scenario: Corrupt pointer without active writer evidence
- **WHEN** a pointer file is not parseable
- **AND** no fresh active writer evidence exists
- **THEN** FlowPilot MUST either recover from unambiguous current evidence or
  return a structured blocker without waiting indefinitely.
