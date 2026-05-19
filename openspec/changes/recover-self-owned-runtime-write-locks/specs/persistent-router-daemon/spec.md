## ADDED Requirements

### Requirement: Self-Owned Stale Write-Lock Recovery Rejoins Daemon Flow

The Router daemon SHALL treat its own stale runtime JSON write-lock sentinel as
a recoverable mechanical persistence condition only after safe artifact checks.

#### Scenario: Daemon encounters its own stale lock

- **WHEN** the daemon needs to write a runtime JSON ledger
- **AND** the existing `.write.lock` names the same daemon process
- **AND** the lock is stale, target JSON is parseable, and no temp write
  artifact remains
- **THEN** the daemon records self-owned stale-lock recovery evidence
- **AND** clears the stale sentinel
- **AND** retries the write or replay step without creating a second daemon.

#### Scenario: Daemon encounters another live process lock

- **WHEN** the daemon needs to write a runtime JSON ledger
- **AND** the existing `.write.lock` names a different live process
- **THEN** the daemon defers progress as runtime write settlement
- **AND** it SHALL NOT clear the other process's lock.

#### Scenario: Self-owned recovery is unsafe

- **WHEN** the daemon sees its own stale lock
- **AND** target JSON is not parseable or temp write artifacts remain
- **THEN** the daemon does not clear the lock automatically
- **AND** the condition remains a mechanical runtime settlement blocker until
  repair evidence exists.
