## ADDED Requirements

### Requirement: Historical Failures Are Full-System Gates

Historical live-run replay SHALL be a required full-system confidence gate for
known FlowPilot failure families.

#### Scenario: Known failure lacks replay

- **WHEN** a known historical failure family affects startup, display,
  packet/result authority, background liveness, stale evidence, FlowGuard
  target selection, route mutation, install sync, or final closure
- **THEN** full-system confidence MUST remain blocked until a replay row covers
  that family with current evidence.

### Requirement: Historical Replay Covers Same-Class Failures

Historical replay SHALL cover the observed bad case and a same-class generalized
case when the failure family is recurring or high risk.

#### Scenario: Only observed bad case is tested

- **WHEN** only the exact observed historical failure is tested
- **AND** the failure family can recur through sibling surfaces
- **THEN** the replay gate MUST remain scoped or blocked until same-class
  evidence is current.
