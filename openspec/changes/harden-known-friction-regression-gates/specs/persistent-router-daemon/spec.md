## ADDED Requirements

### Requirement: Daemon replay covers repair finalization interleavings
The Router daemon SHALL be covered by regression evidence for PM repair
decision finalization interleavings that can expose half-committed
control-blocker state.

#### Scenario: Daemon observes PM repair transaction immediately after commit
- **WHEN** PM submits a valid repair decision and the daemon computes the next
  action in the same live run before any manual clean reload
- **THEN** the daemon MUST observe a coherent post-decision state and MUST NOT
  fail because a repair event requires an unsatisfied PM decision flag.

#### Scenario: Daemon status reports scoped repair blocker
- **WHEN** repair finalization cannot produce an executable next action
- **THEN** daemon status MUST report a concrete repair blocker with current
  required facts rather than a generic non-executable event error.

### Requirement: Daemon evidence cannot be model-only for live misses
FlowPilot SHALL require runtime daemon evidence for known live daemon misses.

#### Scenario: Persistent daemon check skips conformance replay
- **WHEN** a persistent daemon result skips conformance replay or runs in
  abstract model-only mode
- **THEN** that result MUST NOT be counted as full evidence for a historical
  daemon miss replay.
