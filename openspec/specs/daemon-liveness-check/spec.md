# daemon-liveness-check Specification

## Purpose
Define Router daemon status-tick liveness checks without treating historical
scheduled-continuation automation as a current workflow feature.

## Requirements
### Requirement: Monitor exposes daemon liveness status
FlowPilot SHALL expose daemon liveness to Controller as `ok` or
`check_liveness`, using a thirty-second grace window over the daemon's last
status tick time.

#### Scenario: Status tick within grace window
- **WHEN** the Router daemon status or lock tick is at most thirty seconds old
- **THEN** the monitor MUST report `daemon_patrol_status=ok` and MUST NOT
  request daemon recovery

#### Scenario: Status tick exceeds grace window
- **WHEN** the Router daemon status tick age is greater than thirty seconds
- **THEN** the monitor MUST report `daemon_patrol_status=check_liveness`
- **AND** the monitor MUST instruct Controller to check whether the daemon
  process is still alive before any recovery attempt

### Requirement: Monitor does not decide recovery
FlowPilot SHALL NOT use status-tick age alone to classify a daemon as requiring
restart or lock replacement.

#### Scenario: Delayed status tick
- **WHEN** status-tick age exceeds thirty seconds but the daemon process may
  still be alive
- **THEN** monitor output MUST avoid `needs_recover`,
  `daemon_repair_or_restart`, or equivalent recovery conclusions
- **AND** Controller MUST be told to inspect liveness and either continue
  attached or recover

#### Scenario: User-visible wording
- **WHEN** status-tick age exceeds thirty seconds before Controller has checked
  daemon liveness
- **THEN** user-facing text MUST describe delayed daemon status that needs
  checking, not a stale or dead daemon

### Requirement: Controller decides attach or recover after liveness check
FlowPilot SHALL let Controller choose continue/attach or daemon recovery only
after checking process and lock evidence for the current run.

#### Scenario: Daemon alive after delayed status
- **WHEN** Controller receives `check_liveness` and the daemon process is still
  alive for the current run
- **THEN** Controller MUST continue attached and MUST NOT start another daemon
  writer

#### Scenario: Daemon dead after delayed status
- **WHEN** Controller receives `check_liveness` and the daemon process is not
  alive for the current run
- **THEN** Controller MAY execute the safe daemon recovery path for that same
  run
- **AND** recovery MUST still attach instead of starting a second writer if a
  live daemon appears during recovery
