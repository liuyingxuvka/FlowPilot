## ADDED Requirements

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
