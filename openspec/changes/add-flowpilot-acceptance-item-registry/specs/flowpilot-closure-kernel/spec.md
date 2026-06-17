## ADDED Requirements

### Requirement: Closure Blocks On Unresolved Acceptance Items
FlowPilot closure SHALL remain blocked while any active acceptance item is
missing, orphaned, stale, low-quality, waived without authority, superseded
without replacement trace, or omitted from terminal replay.

#### Scenario: All route nodes accepted but item remains open
- **WHEN** all effective route nodes are accepted
- **AND** at least one active acceptance item remains unresolved
- **THEN** closure kernel MUST classify final completion as blocked
- **AND** PM MUST repair, reroute, waive with authority, supersede, or stop
  through the existing current-runtime path.
