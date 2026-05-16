# parallel-flowpilot-run-isolation Specification

## Purpose
TBD - created by archiving change parallel-flowpilot-run-isolation. Update Purpose after archive.
## Requirements
### Requirement: Daemon Run Binding

The Router daemon SHALL bind to one immutable run identity at startup.

#### Scenario: Daemon ticks after UI focus changes

- **GIVEN** run A has a live Router daemon
- **AND** run B becomes the top-level current/focus run
- **WHEN** run A's daemon performs a later tick
- **THEN** it reads and writes run A state only
- **AND** it does not reload run B through `.flowpilot/current.json`

### Requirement: Parallel Run Locks

FlowPilot SHALL enforce one Router writer per run while permitting different
runs to have independent daemon locks.

#### Scenario: Two runs are active

- **GIVEN** run A and run B both exist
- **WHEN** each run has one Router daemon writer
- **THEN** neither run is rejected merely because the other is running
- **AND** a second writer for either same run is rejected.

### Requirement: Current Pointer Is UI Focus

The top-level current pointer SHALL be treated as UI focus/default target only,
not daemon authority.

#### Scenario: Non-current run remains active

- **GIVEN** run A is running
- **AND** run B is the current/focus run
- **WHEN** active task metadata is rebuilt
- **THEN** run A remains running/background-active unless independent stale,
  stopped, terminal, or superseded evidence exists.

### Requirement: Targeted Stop

Daemon stop operations SHALL support explicit run targeting.

#### Scenario: Stop run A while run B is active

- **GIVEN** run A and run B both have daemon locks
- **WHEN** the operator stops run A by run id or run root
- **THEN** only run A's lock/status is released
- **AND** run B remains active.

### Requirement: Released Locks Stay Non-Active

Released, error, stale, or terminal daemon locks SHALL NOT be refreshed back to
active by a later tick.

#### Scenario: Daemon observes released lock

- **GIVEN** a daemon's lock has status `released`
- **WHEN** the daemon loop observes the lock on the next tick
- **THEN** it exits or reports stopped
- **AND** it does not write `status: active`.

### Requirement: Active Work Board Counts

Controller work board summaries SHALL distinguish historical done rows from
active unfinished work.

#### Scenario: Done-only controller ledger

- **GIVEN** a controller action ledger has one `done` row and no pending,
  waiting, in-progress, blocked, or repair rows
- **WHEN** status metadata is projected
- **THEN** active work count is zero
- **AND** UI/checkers can report audit history separately from live work.
