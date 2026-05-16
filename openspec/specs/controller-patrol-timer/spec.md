# controller-patrol-timer Specification

## Purpose
TBD - created by archiving change add-controller-patrol-timer. Update Purpose after archive.
## Requirements
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

### Requirement: Existing Monitor Remains Source Of Truth
FlowPilot MUST keep the Router daemon monitor automatic and MUST NOT make
Controller's patrol timer a second source of daemon truth.

#### Scenario: Patrol reads existing monitor
- **WHEN** Controller runs the patrol timer command
- **THEN** the command reads the existing daemon status, Controller action
  ledger, and Controller receipts rather than creating a separate monitor state

#### Scenario: Router progress remains daemon owned
- **WHEN** Controller is in the patrol timer loop
- **THEN** Controller is not authorized to drive normal progress through
  `next`, `apply`, or `run-until-wait`

### Requirement: Continuous Standby Is Anti-Exit In Progress Duty
FlowPilot SHALL represent `continuous_controller_standby` as an in-progress
foreground keepalive duty whose purpose is to prevent accidental Controller
foreground exit while FlowPilot is still running.

#### Scenario: Standby row names command
- **WHEN** Router exposes `continuous_controller_standby`
- **THEN** the standby payload contains the patrol timer command, anti-exit
  purpose, loop rule, monitor source, and a completion rule that only allows
  exit on `terminal_return` with `controller_stop_allowed=true`

#### Scenario: Restarting command is not completion
- **WHEN** the patrol timer returns `continue_patrol`
- **THEN** `continuous_controller_standby` remains `in_progress`, and command
  start, command restart, timer finish, monitor checked once, no new work, and
  `continue_patrol` are all forbidden completion evidence

### Requirement: Controller Prompt Surfaces Name Patrol Command
FlowPilot SHALL put the exact patrol timer command and anti-exit semantics in
the Controller role card, Controller resume/reentry card, generated Controller
table prompt, and `continuous_controller_standby` row payload.

#### Scenario: Controller sees command at task time
- **WHEN** Controller reaches the final standby row in the action ledger
- **THEN** the row payload and table prompt both tell Controller to run the
  patrol timer command and wait for its output

#### Scenario: Resume preserves patrol duty
- **WHEN** Controller resumes into `foreground_required_mode=watch_router_daemon`
- **THEN** the resume/reentry prompt tells Controller not to final-answer and
  to run the patrol timer command, rerunning it and waiting for the next output
  when it returns `continue_patrol`
