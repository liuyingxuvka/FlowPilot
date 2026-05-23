## ADDED Requirements

### Requirement: Fresh write locks defer incomplete ledger reads
Daemon-critical runtime ledger reads SHALL treat a fresh runtime JSON write
lock plus an incomplete target ledger as in-progress write evidence unless the
lock is stale enough for takeover.

#### Scenario: Fresh lock and incomplete target with ambiguous liveness
- **WHEN** a daemon-critical ledger is temporarily not parseable
- **AND** a fresh runtime JSON write lock exists for that ledger
- **AND** process-liveness evidence is unavailable, delayed, or contradictory
- **THEN** Router MUST defer progress as runtime ledger write-in-progress
- **AND** Router MUST NOT classify the ledger as corrupted until the lock is
  stale or the target remains invalid without fresh write evidence

#### Scenario: Dead owner with valid target remains takeover-eligible
- **WHEN** a runtime JSON write lock names a dead owner
- **AND** the target ledger is valid JSON
- **THEN** Router MAY take over and clean up the stale lock according to the
  existing write-lock policy
