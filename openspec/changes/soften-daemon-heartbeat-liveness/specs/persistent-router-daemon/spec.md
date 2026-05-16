## MODIFIED Requirements

### Requirement: Run-scoped Router lock
The Router daemon SHALL use a run-scoped lock to prevent two Router daemons from
writing the same run state.

#### Scenario: Duplicate daemon start
- **WHEN** a second Router daemon starts for a run with a live non-stale daemon lock
- **THEN** the second daemon MUST refuse to become the writer and report the existing daemon status

#### Scenario: Delayed daemon heartbeat requires liveness check
- **WHEN** foreground monitoring observes a daemon heartbeat older than five seconds
- **THEN** FlowPilot MUST report `heartbeat_status=check_liveness` rather than replacing the lock from heartbeat age alone

#### Scenario: Stale daemon lock after liveness check
- **WHEN** Controller liveness checking confirms that the current-run daemon process is not alive and the daemon lock is stale according to the configured stale-lock threshold
- **THEN** recovery MAY replace the stale lock and restart Router from persisted run state

#### Scenario: Active daemon appears during recovery
- **WHEN** Controller attempts recovery after `check_liveness` and discovers a live current-run daemon lock
- **THEN** FlowPilot MUST attach to the existing daemon and MUST NOT start a second writer
