## ADDED Requirements

### Requirement: Quiet standby patrol defaults to sixty seconds
The Controller patrol timer SHALL use a sixty-second default interval for quiet foreground standby while preserving Router daemon progress and daemon heartbeat/liveness semantics.

#### Scenario: Quiet standby command uses sixty seconds
- **WHEN** Router exposes `continuous_controller_standby` for a nonterminal active run with no ready ordinary Controller action
- **THEN** the Controller-facing command uses `controller-patrol-timer --seconds 60`
- **AND** the standby payload records `patrol_timer_seconds=60`.

#### Scenario: Router daemon tick remains unchanged
- **WHEN** the Controller patrol default changes to sixty seconds
- **THEN** Router daemon status still reports its daemon tick interval independently
- **AND** the patrol interval MUST NOT be used as the Router daemon tick interval.

#### Scenario: Sixty-second patrol remains anti-exit
- **WHEN** the patrol timer returns `continue_patrol`
- **THEN** Controller keeps `continuous_controller_standby` in progress
- **AND** Controller reruns the same patrol command and waits for the next output instead of final-answering.

#### Scenario: Ready Controller work still preempts quiet standby
- **WHEN** ready Controller work appears during or after the quiet patrol wait
- **THEN** the patrol returns `new_controller_work`
- **AND** Controller reads the Controller action ledger and resumes top-to-bottom row processing.
