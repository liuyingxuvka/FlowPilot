## ADDED Requirements

### Requirement: Control-plane blocker repair uses defect-family closure
FlowPilot SHALL bind control-plane blocker repair to a defect-family decision
so repeated blockers produce reusable FlowGuard obligations instead of
incident-only repairs.

#### Scenario: Same-family blockers exist
- **WHEN** Recovery Supervisor opens a transaction for a control-plane blocker
- **AND** prior blockers share the same family id, source surface, or stale
  proof mode
- **THEN** the recovery transaction MUST record same-family cases and MUST close
  only after the current repair evidence covers the observed case and at least
  one generalized same-family hazard
