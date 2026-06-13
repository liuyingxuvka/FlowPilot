## ADDED Requirements

### Requirement: FlowPilot run ledger writes are atomic
FlowPilot SHALL write the current run ledger through a complete same-directory temporary file followed by an atomic replacement of the target ledger.

#### Scenario: Reader observes a ledger during write
- **WHEN** a status, patrol, or foreground command reads the current run ledger while another command is writing it
- **THEN** the reader MUST see either the previous complete JSON document or the next complete JSON document
- **AND** it MUST NOT observe a partially written target ledger from the normal write path.

### Requirement: FlowPilot run ledger reads retry transient incomplete JSON
FlowPilot SHALL retry briefly when reading the current run ledger encounters an empty or incomplete JSON document that may be caused by an in-progress write.

#### Scenario: Transient incomplete read recovers
- **WHEN** the first read of the current run ledger sees empty content or `JSONDecodeError`
- **AND** a bounded retry reads a valid JSON ledger
- **THEN** FlowPilot MUST continue with the valid ledger instead of surfacing a raw JSON decode failure.

#### Scenario: Persistent corruption still fails
- **WHEN** all bounded read retries still see missing, empty, or invalid JSON
- **THEN** FlowPilot MUST fail with a clear runtime ledger read error
- **AND** it MUST NOT silently synthesize a default ledger or compatibility fallback.
