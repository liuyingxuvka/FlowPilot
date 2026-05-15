## ADDED Requirements

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
reader never observes a partially written JSON document.

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
