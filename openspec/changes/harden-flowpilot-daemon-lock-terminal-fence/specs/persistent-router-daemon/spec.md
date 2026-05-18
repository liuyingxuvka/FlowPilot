## ADDED Requirements

### Requirement: JSON write contention is daemon-deferrable
The Router daemon SHALL keep running when a runtime JSON write is blocked by a
live or uncertain active writer.

#### Scenario: Live writer blocks daemon JSON write
- **WHEN** a Router daemon tick cannot acquire a runtime JSON write lock because
  another writer is live or owner liveness is uncertain
- **THEN** the daemon MUST record the write as deferred for a later tick
- **AND** the daemon MUST NOT exit fatally solely because of that lock wait.

#### Scenario: Dead writer lock is recovered
- **WHEN** a Router daemon tick encounters a fresh runtime JSON write lock whose
  owner process is confirmed dead
- **THEN** the daemon MUST recover the lock, record takeover evidence, and
  continue through the normal persisted-state replay path.

### Requirement: Terminal daemon ticks do not schedule active work
The Router daemon SHALL treat terminal lifecycle state as a hard fence for
nonterminal startup, heartbeat, role, and route actions.

#### Scenario: Daemon tick sees terminal lifecycle
- **WHEN** a Router daemon tick loads a run whose lifecycle status is terminal
- **THEN** the daemon MUST write terminal daemon status and return terminal
  without scheduling startup rows, heartbeat automations, role starts, or route
  work.

#### Scenario: Terminal lifecycle appears during a tick
- **WHEN** terminal lifecycle is written while a daemon tick is processing
- **THEN** any nested startup or heartbeat scheduler reached by that tick MUST
  re-check the terminal fence before creating nonterminal side effects.
