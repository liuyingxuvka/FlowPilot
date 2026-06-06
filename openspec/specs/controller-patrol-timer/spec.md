# controller-patrol-timer Specification

## Purpose
TBD - created by archiving change add-controller-patrol-timer. Update Purpose after archive.
## Requirements
### Requirement: Controller Patrol Timer Command
FlowPilot SHALL provide a Controller-facing patrol timer command that waits for
a requested interval, reads the existing Router daemon monitor and Controller
action ledger, and returns a concrete Controller instruction.

#### Scenario: Quiet monitor continues patrol
- **WHEN** the Router daemon status tick is at most thirty seconds old, no ordinary Controller action is ready, and Controller runs the patrol timer command
- **THEN** the command returns `patrol_result=continue_patrol`, includes the anti-exit purpose, names the next command, and instructs Controller to rerun that command and wait for its next output

#### Scenario: Delayed daemon status asks for liveness check
- **WHEN** the Router daemon status tick is older than thirty seconds and no ordinary Controller action is ready
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

### Requirement: Controller patrol surfaces repeat break-glass reminder
FlowPilot SHALL include the same short, restrictive break-glass reminder in
Controller daemon-monitor and patrol surfaces used during long foreground
standby.

#### Scenario: Daemon status carries reminder
- **WHEN** Router writes `runtime/router_daemon_status.json` for an active run
- **THEN** the status includes a Controller-visible break-glass reminder with
  the playbook path and ordinary-defect exclusion

#### Scenario: Patrol timer carries reminder
- **WHEN** Controller runs the patrol timer command and receives a nonterminal
  patrol output
- **THEN** the output includes the break-glass reminder with the playbook path
  and ordinary-defect exclusion

#### Scenario: Continuous standby payload carries reminder
- **WHEN** Router exposes `continuous_controller_standby`
- **THEN** the standby row or payload includes the break-glass reminder while
  keeping standby as an in-progress monitor duty, not a finishable checklist
  item

### Requirement: Patrol timer carries explicit stop preflight

The Controller patrol timer SHALL include a Controller-facing stop preflight in
every result. The preflight SHALL state whether the Controller may final-answer,
which conditions block final exit, and whether `continuous_controller_standby`
remains the active foreground duty.

#### Scenario: Continue patrol blocks final answer

- **WHEN** the patrol timer returns `patrol_result=continue_patrol`
- **THEN** the stop preflight reports `final_answer_allowed=false`,
  `controller_stop_allowed=false`, and
  `continuous_controller_standby_status=in_progress`
- **AND** the instruction tells Controller to rerun the patrol command and wait
  for the next output.

#### Scenario: Nonterminal return duty blocks final answer

- **WHEN** the patrol timer returns a nonterminal duty such as user input,
  liveness check, wait-target check, blocker recording, or reissue handling
- **THEN** the stop preflight reports `final_answer_allowed=false` unless the
  result is `terminal_return` with `controller_stop_allowed=true`.

#### Scenario: Terminal return allows final answer

- **WHEN** the patrol timer returns `terminal_return` and
  `controller_stop_allowed=true`
- **THEN** the stop preflight reports `final_answer_allowed=true`.

### Requirement: Patrol timer rejects display projection as stop authority

The Controller patrol timer SHALL name Router daemon status and the Controller
action ledger as the normal progress and stop authority. It SHALL NOT allow a
current status summary, display plan, or stale `next_step` projection to
authorize foreground Controller exit.

#### Scenario: Stale display action projection cannot stop patrol

- **WHEN** the current status summary references a completed display action but
  the daemon/ledger still require `continuous_controller_standby`
- **THEN** the patrol timer returns a nonterminal instruction and keeps final
  answer disallowed.

### Requirement: Patrol timer remains downstream of standby policy

The Controller patrol timer SHALL derive its user-facing result from the
foreground standby state and stop-preflight policy, without creating a second
progress or stop authority.

#### Scenario: Patrol result follows standby state

- **WHEN** standby returns pending Controller work, terminal return, daemon
  liveness check, live daemon watching, or another nonterminal duty
- **THEN** patrol timer returns the corresponding Controller instruction and
  preserves final-answer preflight.

#### Scenario: Patrol timer does not override stop authority

- **WHEN** standby final-answer preflight is false
- **THEN** patrol timer also reports final-answer disallowed unless the result
  is terminal return with `controller_stop_allowed=true`.
