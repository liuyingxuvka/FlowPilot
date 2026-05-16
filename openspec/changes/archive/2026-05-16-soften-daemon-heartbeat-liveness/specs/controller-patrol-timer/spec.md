## MODIFIED Requirements

### Requirement: Controller Patrol Timer Command
FlowPilot SHALL provide a Controller-facing patrol timer command that waits for
a requested interval, reads the existing Router daemon monitor and Controller
action ledger, and returns a concrete Controller instruction.

#### Scenario: Quiet monitor continues patrol
- **WHEN** the Router daemon heartbeat is at most five seconds old, no ordinary Controller action is ready, and Controller runs the patrol timer command
- **THEN** the command returns `patrol_result=continue_patrol`, includes the anti-exit purpose, names the next command, and instructs Controller to rerun that command and wait for its next output

#### Scenario: Delayed daemon heartbeat asks for liveness check
- **WHEN** the Router daemon heartbeat is older than five seconds and no ordinary Controller action is ready
- **THEN** the command returns a liveness-check instruction rather than a daemon repair or restart conclusion
- **AND** the instruction tells Controller to check whether the daemon is still running, continue attached if alive, and recover only if stopped

#### Scenario: New Controller work wakes patrol
- **WHEN** a ready Controller action exists while Controller runs the patrol timer command
- **THEN** the command returns `patrol_result=new_controller_work` and instructs Controller to read the Controller action ledger and process ready rows from top to bottom

#### Scenario: Terminal state permits exit
- **WHEN** the monitored run is terminal and `controller_stop_allowed` is true
- **THEN** the command returns `patrol_result=terminal_return` and allows the foreground Controller to end
