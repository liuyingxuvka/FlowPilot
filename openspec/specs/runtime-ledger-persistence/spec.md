# runtime-ledger-persistence Specification

## Purpose
TBD - created by archiving change harden-runtime-ledger-persistence. Update Purpose after archive.
## Requirements
### Requirement: Runtime Ledgers Remain Parseable After Every Write

Daemon-critical runtime ledgers SHALL remain valid JSON after every write.

#### Scenario: Router writes scheduler ledger

- **WHEN** Router records or updates a scheduler row
- **THEN** `router_scheduler_ledger.json` remains valid JSON
- **AND** Router can read the written file back before daemon progress depends
  on it.

#### Scenario: Controller action ledger is updated

- **WHEN** Controller action rows are written, completed, or reconciled
- **THEN** `controller_action_ledger.json` remains valid JSON
- **AND** a daemon tick can read it without `JSONDecodeError`.

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

### Requirement: Router Scheduler Ledger Has One Owner

The Router scheduler ledger SHALL be mutated only by Router-owned scheduling
code under the run's Router ownership rules.

#### Scenario: Foreground path runs while daemon owns scheduling

- **WHEN** the daemon owns startup or runtime scheduling
- **THEN** foreground diagnostic or catch-up paths may read scheduler rows
- **AND** they SHALL NOT independently append or overwrite scheduler rows
  outside the Router-owned write lane.

### Requirement: Daemon Liveness Status Matches Lock And Process Evidence

Daemon status SHALL NOT claim an active daemon unless lock state, lock
freshness, and process evidence agree.

#### Scenario: Lock is released with error

- **WHEN** the daemon lock status is `error`
- **THEN** daemon status reports an error or repair-needed lifecycle
- **AND** it SHALL NOT report `daemon_active`.

#### Scenario: Process is missing

- **WHEN** daemon status names a PID that is not live
- **THEN** status reports stale/dead daemon evidence
- **AND** Router/Controller treat the run as needing daemon repair or restart
  rather than as actively driven.

### Requirement: Atomic write verification uses transient-lock semantics
Runtime ledger persistence SHALL apply transient write-lock semantics to atomic
write verification and read-back, not only to the replace operation.

#### Scenario: Replace succeeds but verification is denied
- **WHEN** a runtime JSON write replaces a daemon-critical ledger successfully
- **AND** the immediate verification read receives a transient access-denied
  error
- **THEN** the write helper reports a retryable write-in-progress outcome
- **AND** the caller MUST NOT classify the ledger as corrupt or the daemon as
  failed from that transient denial alone.

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
