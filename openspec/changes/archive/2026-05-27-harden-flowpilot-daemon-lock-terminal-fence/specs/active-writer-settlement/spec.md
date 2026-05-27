## ADDED Requirements

### Requirement: Dead-owner write locks are immediately recoverable
FlowPilot SHALL distinguish a live active writer from a fresh JSON write lock
whose recorded owner process is not alive.

#### Scenario: Fresh write lock owner is dead
- **WHEN** Router attempts to write a runtime JSON file and its `.write.lock`
  is fresh but the recorded owner process is confirmed dead
- **THEN** Router MUST replace the lock without waiting for the stale-lock age
  threshold
- **AND** Router MUST record dead-owner takeover evidence for the affected
  path.

#### Scenario: Fresh write lock owner is alive
- **WHEN** Router attempts to write a runtime JSON file and its `.write.lock`
  is fresh with a live recorded owner process
- **THEN** Router MUST treat the file as active writer settlement in progress
  and defer the competing write instead of taking over the lock.

### Requirement: Writer crash evidence remains visible
FlowPilot SHALL preserve diagnostic evidence when it recovers a JSON write lock
left by a dead writer.

#### Scenario: Dead-owner takeover occurs
- **WHEN** Router replaces a JSON write lock because the owner process is dead
- **THEN** the takeover evidence MUST include the lock path, target JSON path,
  previous owner pid when available, classification, and timestamp
- **AND** the evidence MUST NOT mark the recovered write as a clean live-writer
  settlement.
