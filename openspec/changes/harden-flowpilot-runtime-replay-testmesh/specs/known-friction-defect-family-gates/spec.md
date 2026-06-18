## ADDED Requirements

### Requirement: Real-run anomalies are backfed before closure
FlowPilot SHALL require each accepted real-run anomaly to be converted into a
structured regression seed with source evidence, defect family, fake-AI
profile, contract cell, Cartesian row, expected runtime reaction, and replay
test evidence before the anomaly is closed.

#### Scenario: New anomaly enters the backfeed registry
- **WHEN** a real run exposes a new control-plane, contract-projection,
  review-window, singleton-authority, retry, or break-glass anomaly
- **THEN** the anomaly MUST be recorded in the backfeed registry with the source
  run/event/result references and without copying sealed bodies.

#### Scenario: Backfed anomaly is closed only after replay evidence
- **WHEN** a backfed anomaly has no current runtime replay test evidence for
  its fake-AI profile and contract cell
- **THEN** the anomaly MUST remain open or scoped and MUST NOT support a full
  defect-family closure claim.

### Requirement: Backfeed registry does not create compatibility surfaces
FlowPilot SHALL use backfed anomalies to reject, repair, reissue, or escalate
current-contract failures; it MUST NOT teach runtime to silently accept legacy
aliases, missing defaults, prose wrappers, or historical artifact fallbacks.

#### Scenario: Legacy-shaped anomaly stays rejected
- **WHEN** a real issue came from a legacy alias, wrapper, stale artifact, or
  unsupported old shape
- **THEN** the backfeed regression MUST preserve the current-contract rejection
  or repair expectation rather than adding a compatibility acceptance path.
