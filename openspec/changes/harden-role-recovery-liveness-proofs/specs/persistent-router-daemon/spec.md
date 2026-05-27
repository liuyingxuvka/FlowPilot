## ADDED Requirements

### Requirement: Daemon fatal errors include actionable diagnostics
The Router daemon SHALL write bounded structured diagnostics when a fatal
runtime error occurs.

#### Scenario: Daemon hits memory pressure
- **WHEN** the daemon records a fatal `MemoryError`
- **THEN** daemon status or event artifacts MUST include the error type,
  traceback or traceback-unavailable reason, current action id when present,
  current wait type when present, and bounded runtime artifact size metadata.

### Requirement: Routine daemon state output is compact by default
FlowPilot SHALL avoid dumping full runtime ledgers in routine CLI state output
used by heartbeat, daemon, or Controller monitoring loops.

#### Scenario: Controller asks for state summary
- **WHEN** the state command is invoked without a full-output option
- **THEN** the command MUST return compact summaries for daemon status and
  Controller action ledger
- **AND** full ledger content MUST remain available through explicit full output
  or direct artifact reads.
