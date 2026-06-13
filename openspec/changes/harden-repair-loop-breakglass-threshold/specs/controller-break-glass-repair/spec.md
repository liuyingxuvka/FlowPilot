# controller-break-glass-repair Delta

## ADDED Requirements

### Requirement: Repair-loop threshold is a valid break-glass trigger
FlowPilot SHALL allow Controller break-glass evaluation when current-run
metadata shows that a normalized same-family repair chain has exceeded the
ordinary repair threshold.

#### Scenario: Threshold false alarm can return to normal
- **WHEN** Controller opens break-glass because the repair-loop threshold was
  exceeded
- **AND** Controller determines from current-run metadata that normal repair is
  still legal and the threshold was a false alarm
- **THEN** Controller records a diagnostic break-glass disposition and returns
  to normal Router/Controller flow without creating route evidence.

#### Scenario: Threshold exposes control-plane fault
- **WHEN** Controller opens break-glass because the repair-loop threshold was
  exceeded
- **AND** current-run metadata shows the normal repair lane is looping,
  contradictory, or unable to produce a legal next action
- **THEN** Controller may use the existing break-glass or Recovery Supervisor
  path to repair the FlowPilot control plane.

#### Scenario: Threshold cannot approve project work
- **WHEN** break-glass was opened from a repair-loop threshold
- **THEN** break-glass artifacts MUST NOT approve node completion, PM decisions,
  Reviewer decisions, FlowGuard Operator decisions, route mutation, terminal
  closure, or target-project work.
