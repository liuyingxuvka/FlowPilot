## ADDED Requirements

### Requirement: Unchanged daemon ticks do not mutate semantic authority
The Router daemon SHALL preserve the existing observation cadence while
producing zero router-state, action, scheduler, wait, or semantic-history
writes when the observed inputs and resulting semantic state are unchanged.
Liveness MAY update only through the existing bounded daemon lock/status
surface.

#### Scenario: Ten thousand unchanged ticks
- **WHEN** the daemon processes ten thousand ticks with identical relevant inputs
- **THEN** router-state, action-ledger, scheduler-ledger, and semantic-history hashes and modification times remain unchanged
- **AND** daemon liveness remains current through its bounded liveness surface

#### Scenario: First real semantic change
- **WHEN** a new current receipt or other relevant input changes the route state
- **THEN** the daemon persists exactly one semantic transition through the existing durable write owner
- **AND** the next unchanged tick produces no second semantic write

### Requirement: Daemon terminal output is bounded
The Router daemon SHALL report aggregate tick counts, the last tick,
semantic-change count, no-change count, and terminal state without retaining
or returning an unbounded per-tick array.

#### Scenario: Long-running daemon returns
- **WHEN** a daemon runs for a large number of ticks and reaches a return condition
- **THEN** its serialized terminal result remains at or below 64 KiB
- **AND** it contains no unbounded `ticks` collection
