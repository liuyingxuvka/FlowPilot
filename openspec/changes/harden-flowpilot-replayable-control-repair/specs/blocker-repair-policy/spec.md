## ADDED Requirements

### Requirement: Control-plane blockers prefer Controller break-glass before user stop
FlowPilot PM repair guidance SHALL route control-plane blockers such as
non-replayable package artifacts, package handoff defects, and evidence-entry
defects to the Controller break-glass repair lane before choosing user stop,
unless break-glass is unavailable, unsafe, or outside its authority.

#### Scenario: PM receives non-replayable package blocker
- **WHEN** reviewer blocks because a package-produced script cannot be replayed
  without a concrete active packet or one-time FlowPilot phase
- **THEN** PM first considers Controller break-glass repair as a control-plane
  recovery path rather than immediately choosing `stop_for_user`.

#### Scenario: Break-glass is not appropriate
- **WHEN** the blocker requires user preference, external access, product scope
  change, or target-project work outside Controller break-glass authority
- **THEN** PM may choose `stop_for_user` or another supported non-break-glass
  repair path.
