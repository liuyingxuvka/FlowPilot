## ADDED Requirements

### Requirement: Historical replay packages preserve current-run authority under parallel pressure
The system SHALL include high-parallel replay package rows that attempt peer
proof reuse, current pointer overwrite, shared artifact reuse, and stale route
evidence reuse.

#### Scenario: Parallel package cannot cross-contaminate runs
- **WHEN** two replay packages operate against different run roots, background
  artifacts, or route versions
- **THEN** the current run remains authoritative and peer evidence is marked
  stale, scoped, blocked, or non-current
