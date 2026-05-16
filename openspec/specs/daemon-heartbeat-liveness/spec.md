# daemon-heartbeat-liveness Specification

## Purpose
TBD - created by archiving change soften-daemon-heartbeat-liveness. Update Purpose after archive.
## Requirements
### Requirement: Monitor exposes heartbeat check status
FlowPilot SHALL expose daemon heartbeat health to Controller as `ok` or
`check_liveness`, using a five-second grace window over the daemon's last
heartbeat time.

#### Scenario: Heartbeat within grace window
- **WHEN** the Router daemon status or lock heartbeat is at most five seconds old
- **THEN** the monitor MUST report `heartbeat_status=ok` and MUST NOT request daemon recovery

#### Scenario: Heartbeat exceeds grace window
- **WHEN** the Router daemon heartbeat age is greater than five seconds
- **THEN** the monitor MUST report `heartbeat_status=check_liveness`
- **AND** the monitor MUST instruct Controller to check whether the daemon process is still alive before any recovery attempt

### Requirement: Monitor does not decide recovery
FlowPilot SHALL NOT use heartbeat age alone to classify a daemon as requiring
restart or lock replacement.

#### Scenario: Delayed heartbeat
- **WHEN** heartbeat age exceeds five seconds but the daemon process may still be alive
- **THEN** monitor output MUST avoid `needs_recover`, `daemon_repair_or_restart`, or equivalent recovery conclusions
- **AND** Controller MUST be told to inspect liveness and either continue attached or recover

#### Scenario: User-visible wording
- **WHEN** heartbeat age exceeds five seconds before Controller has checked daemon liveness
- **THEN** user-facing text MUST describe a delayed heartbeat that needs checking, not a stale or dead daemon

### Requirement: Controller decides attach or recover after liveness check
FlowPilot SHALL let Controller choose continue/attach or daemon recovery only
after checking process and lock evidence for the current run.

#### Scenario: Daemon alive after delayed heartbeat
- **WHEN** Controller receives `check_liveness` and the daemon process is still alive for the current run
- **THEN** Controller MUST continue attached and MUST NOT start another daemon writer

#### Scenario: Daemon dead after delayed heartbeat
- **WHEN** Controller receives `check_liveness` and the daemon process is not alive for the current run
- **THEN** Controller MAY execute the safe daemon recovery path for that same run
- **AND** recovery MUST still attach instead of starting a second writer if a live daemon appears during recovery
