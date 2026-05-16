## ADDED Requirements

### Requirement: Router exposes wait target metadata
Router daemon status SHALL expose controller-visible wait target metadata when
the foreground Controller is expected to remain in standby.

#### Scenario: Role report wait names target and expected evidence
- **WHEN** Router daemon is waiting for a role report or result
- **THEN** `current_wait` includes the wait class, target role, wait reason,
  expected controller-visible event/path metadata, started time, reminder
  cadence, and Router-authored reminder text

#### Scenario: Liveness is a probe obligation not cached truth
- **WHEN** `current_wait` targets a background role
- **THEN** the monitor records whether liveness checking is required and may
  record last-check evidence, but MUST NOT expose a stale current-alive boolean
  as the authority for skipping a new liveness check

### Requirement: ACK waits use reminder then blocker
Controller standby SHALL remind a target role during ACK waits after three
minutes and SHALL raise a Router-visible blocker if the ACK remains absent
after ten minutes.

#### Scenario: ACK reminder due
- **WHEN** an ACK wait has lasted at least three minutes and the expected ACK is
  absent
- **THEN** Controller sends the Router-authored reminder to the target role and
  records reminder metadata without reading any sealed body

#### Scenario: ACK blocker due
- **WHEN** an ACK wait has lasted at least ten minutes and the expected ACK is
  still absent
- **THEN** Controller records a Router-visible blocker for PM-routed recovery

### Requirement: Report and result waits repeat liveness checks
Controller standby SHALL remind the target role every ten minutes during role
report/result waits and SHALL perform a fresh liveness check on each reminder
cycle.

#### Scenario: Healthy role continues work
- **WHEN** a report/result wait reminder is due and the target role responds or
  otherwise proves it is still working
- **THEN** Controller records the fresh liveness evidence and continues standby
  without escalating only because total elapsed time is long

#### Scenario: Lost role becomes blocker
- **WHEN** a report/result wait reminder is due and the target role is missing,
  cancelled, unknown, unresponsive, or reports it is blocked
- **THEN** Controller records a Router-visible blocker for PM-routed recovery

### Requirement: Controller-local waits SHALL trigger self-audit
Controller SHALL audit its action ledger and receipts rather than reminding any
background role when Router status indicates that the foreground wait is for
Controller-local work.

#### Scenario: Controller has pending local action
- **WHEN** `current_wait.wait_class` is `controller_local_action`
- **THEN** Controller scans pending and in-progress actions, checks receipts,
  performs any dependency-satisfied local action it can complete, and rescans
  the ledger before entering role standby

#### Scenario: Controller local action cannot complete
- **WHEN** Controller cannot complete its own pending local action
- **THEN** Controller records a Controller blocker with controller-visible facts
  for Router and PM handling

### Requirement: Recovery remains Router and PM owned
Controller SHALL NOT decide role replacement, route progress, report quality,
or node completion when a wait-target liveness problem is found.

#### Scenario: PM decides replacement
- **WHEN** Controller reports a lost-role wait blocker
- **THEN** Router enters the existing blocker path and PM decides whether to
  continue waiting, re-remind, reissue the card/task, supersede the old role, or
  start a replacement role from current role memory
