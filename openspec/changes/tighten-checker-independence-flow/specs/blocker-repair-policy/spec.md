## ADDED Requirements

### Requirement: Active blocker projections use current-effective blockers
FlowPilot SHALL preserve blocker history while deriving current active-blocker
status, console rows, final preflight blockers, and gate decisions only from
blockers that are current-effective or from explicit PM decision gates.

#### Scenario: Historical blocker remains in raw ledger but not current projection
- **WHEN** a blocker row remains in `active_blockers`
- **AND** its current target packet or repair packet is no longer current for
  that blocker
- **THEN** FlowPilot MAY retain the row as audit history
- **AND** current active-blocker projections MUST exclude it.

#### Scenario: Final preflight ignores stale repaired blocker
- **WHEN** a blocker's repair packet has been accepted or superseded so the
  blocker no longer has a current effective target
- **THEN** FlowPilot MUST NOT report that blocker as a final preflight active
  blocker.

#### Scenario: PM decision gate remains visible while awaiting PM
- **WHEN** a blocker is explicitly awaiting PM decision gate
- **THEN** FlowPilot MAY show it in active-blocker projections even if ordinary
  current-target validation would not classify it as a role repair blocker
- **AND** the projection MUST identify the PM decision gate as the current
  owner instead of treating historical repair rows as active.
