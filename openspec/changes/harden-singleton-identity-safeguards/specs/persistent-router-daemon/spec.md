## ADDED Requirements

### Requirement: Daemon Singleton Evidence Is Auditable
FlowPilot SHALL expose per-run daemon writer evidence to the singleton authority audit, including lock status, owner process, run root, last tick, replacement basis, and terminal/released status.

#### Scenario: One live writer per run
- **WHEN** a run has one live daemon lock with a matching run root and nonterminal lifecycle
- **THEN** the singleton audit reports the daemon writer surface as safe for that run

#### Scenario: Duplicate daemon writer is blocked evidence
- **WHEN** a run has evidence of two live daemon writers or a live lock plus a second writer attempt
- **THEN** the singleton audit reports a daemon singleton risk and requires the normal stale-lock or attach path to resolve it
