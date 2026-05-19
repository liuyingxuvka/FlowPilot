## MODIFIED Requirements

### Requirement: Runtime Ledger Writes Are Atomic

Daemon-critical runtime ledger writes SHALL use an atomic replace strategy so a
reader never observes a partially written JSON document, and recoverable target
file contention SHALL be exposed as runtime write-lock settlement rather than a
raw fatal filesystem exception.

#### Scenario: Daemon reads while a ledger is being updated

- **WHEN** a daemon tick reads a ledger during another runtime update
- **THEN** it sees either the old complete JSON document or the new complete
  JSON document
- **AND** it never sees a partial appended fragment.

#### Scenario: Daemon reads a temporarily incomplete ledger with a fresh write lock

- **WHEN** a daemon tick reads a daemon-critical ledger that is not parseable
- **AND** the ledger has a fresh runtime JSON write lock
- **THEN** the daemon defers progress until the next one-second tick
- **AND** it SHALL NOT release the daemon lock as an error
- **AND** it SHALL NOT report the ledger as corrupted while the write lock is
  still fresh.

#### Scenario: Daemon reads an incomplete ledger without a fresh write lock

- **WHEN** a daemon tick reads a daemon-critical ledger that is not parseable
- **AND** no fresh runtime JSON write lock exists for that ledger
- **THEN** the daemon reports a repair-needed corruption state
- **AND** it SHALL NOT continue scheduling from that ledger.

#### Scenario: Windows replace contention persists after bounded retry

- **WHEN** a runtime JSON writer owns its write lock but cannot replace the
  target file because the operating system reports `PermissionError`
- **AND** the bounded retry window is exhausted
- **THEN** the writer raises a runtime ledger write-in-progress condition naming
  the target path and lock metadata
- **AND** it SHALL NOT surface a raw `PermissionError` to daemon control flow.

#### Scenario: Dead-owner write lock is encountered before a retry

- **WHEN** a runtime JSON write lock names a process that is no longer live
- **THEN** the next writer records dead-owner takeover evidence
- **AND** clears the stale lock before retrying the atomic write.

#### Scenario: Writer cannot remove its own lock after a successful write

- **WHEN** a runtime JSON writer has written, replaced, and verified the target
  JSON
- **AND** removing the matching `.write.lock` fails after bounded retry
- **THEN** FlowPilot records runtime write-lock cleanup failure diagnostics
- **AND** it SHALL NOT silently discard the cleanup failure evidence.

#### Scenario: Later writer finds its own stale lock after successful cleanup failed

- **WHEN** a runtime JSON writer sees a stale `.write.lock` whose owner pid is
  the current process
- **AND** the target JSON is parseable
- **AND** no `.tmp-*` write artifact remains for that target directory
- **THEN** FlowPilot records self-owned stale-lock takeover evidence
- **AND** clears the stale lock before retrying the atomic write.

#### Scenario: Self-owned stale lock has unsafe artifacts

- **WHEN** a runtime JSON writer sees a stale `.write.lock` whose owner pid is
  the current process
- **AND** the target JSON is not parseable or a `.tmp-*` write artifact remains
- **THEN** FlowPilot SHALL NOT clear the lock automatically
- **AND** it reports the condition as unresolved mechanical runtime settlement.

#### Scenario: Self-owned lock is still fresh

- **WHEN** a runtime JSON writer sees a `.write.lock` whose owner pid is the
  current process
- **AND** the lock is still fresh
- **THEN** FlowPilot treats it as active write settlement
- **AND** it SHALL NOT clear the lock through the stale-lock takeover path.
