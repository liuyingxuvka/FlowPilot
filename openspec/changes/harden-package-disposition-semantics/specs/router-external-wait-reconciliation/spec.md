## ADDED Requirements

### Requirement: Wait replay distinguishes idempotent package replay from package conflict
Router external-event wait reconciliation SHALL close waits for idempotent PM package-result replays only when the replay matches the already-recorded semantic package identity and conflict evidence.

#### Scenario: Matching replay closes stale wait
- **WHEN** a PM package-result disposition has already been recorded
- **AND** the same package disposition is replayed while a matching wait row remains open
- **THEN** the Router closes the wait row from already-recorded evidence
- **AND** it does not write duplicate package side effects

#### Scenario: Conflicting replay does not close stale wait as success
- **WHEN** a PM package-result disposition has already been recorded
- **AND** a different PM body is submitted for the same semantic package identity while a matching wait row remains open
- **THEN** the Router rejects the conflict instead of closing the wait as a successful replay
- **AND** the run remains blocked until an authorized repair or reissue path handles the conflict
