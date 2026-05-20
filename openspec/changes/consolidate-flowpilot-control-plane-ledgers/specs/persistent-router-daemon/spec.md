## ADDED Requirements

### Requirement: Daemon defers transient scheduler ledger contention
The Router daemon SHALL treat transient scheduler-ledger access contention as a
retryable tick condition rather than a daemon-fatal error.

#### Scenario: Scheduler ledger read-back is temporarily denied
- **WHEN** the daemon or Router-owned fold verifies or reads
  `router_scheduler_ledger.json`
- **AND** the operating system reports a transient access-denied condition while
  the runtime ledger has fresh write activity
- **THEN** the daemon records a deferred tick
- **AND** it keeps the daemon lock active
- **AND** it retries on the next tick instead of releasing the lock with status
  `error`.
