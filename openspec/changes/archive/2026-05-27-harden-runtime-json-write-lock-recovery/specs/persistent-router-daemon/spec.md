## ADDED Requirements

### Requirement: Daemon Write-Lock Wait Path Does Not Self-Terminate

The Router daemon SHALL treat recoverable runtime ledger write locks as deferred
progress, including write locks encountered while recording wait status.

#### Scenario: Scheduler ledger write is temporarily blocked

- **WHEN** a daemon tick attempts to update `router_scheduler_ledger.json`
- **AND** the runtime JSON writer reports a write-in-progress condition for that
  ledger
- **THEN** the daemon records or returns a deferred tick for runtime ledger
  settlement
- **AND** it SHALL NOT release the daemon lock with `daemon_error`.

#### Scenario: Run state is locked while recording write-lock wait status

- **WHEN** daemon tick work raises `RouterLedgerWriteInProgress`
- **AND** the daemon's recovery/status path also hits
  `RouterLedgerWriteInProgress` for `router_state.json`
- **THEN** the daemon keeps the run in a deferred runtime write-lock wait
- **AND** it SHALL NOT convert the nested wait into a fatal daemon error.

#### Scenario: Dead-owner lock takeover rejoins daemon flow

- **WHEN** a runtime JSON write lock is owned by a dead process
- **THEN** takeover evidence is recorded
- **AND** the daemon resumes normal replay or terminal reconciliation from
  persisted state after the lock is cleared.
