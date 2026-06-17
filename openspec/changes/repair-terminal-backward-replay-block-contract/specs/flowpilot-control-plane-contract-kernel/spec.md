## ADDED Requirements

### Requirement: Terminal replay result contract has pass and block branches
FlowPilot SHALL mechanically accept a terminal backward replay Reviewer result
when it uses the current terminal result shape and either records a complete
passing replay or records a complete blocking replay. The blocking branch MUST
NOT be rejected solely because top-level `passed` is `false`.

#### Scenario: Passing terminal replay closes
- **WHEN** runtime issues a terminal backward replay packet with segment targets
- **AND** Reviewer submits a current result with `passed=true`
- **AND** every segment review matches one runtime-issued target, has
  `passed=true`, `pm_segment_decision=continue`, reviewer identity, and direct
  evidence paths
- **THEN** runtime MUST accept the result mechanically
- **AND** runtime MAY record accepted terminal replay evidence for closure.

#### Scenario: Blocking terminal replay remains semantic
- **WHEN** runtime issues a terminal backward replay packet with segment targets
- **AND** Reviewer submits a current result with `passed=false`
- **AND** the result has at least one failing segment, explicit blockers,
  reviewer identity, direct evidence paths, PM repair decision, and
  `repair_restart_policy`
- **THEN** runtime MUST accept the result mechanically
- **AND** runtime MUST route it through terminal semantic blocker handling
- **AND** runtime MUST NOT record accepted terminal replay closure evidence.

#### Scenario: Malformed blocking terminal replay is still mechanical
- **WHEN** Reviewer submits `passed=false`
- **AND** the result omits runtime-issued segments, lacks blockers, lacks a
  repair restart policy, lacks direct evidence paths, or uses an unexpected
  segment id
- **THEN** runtime MUST reject the result as a mechanical contract failure
- **AND** runtime MUST issue a current-contract correction packet rather than
  recording a semantic blocker.

### Requirement: Terminal replay reissue preserves runtime target context
FlowPilot SHALL preserve the terminal replay target context when a terminal
backward replay result fails mechanical contract validation and a correction
packet is issued.

#### Scenario: Terminal reissue includes segment targets
- **WHEN** a terminal backward replay result is mechanically blocked
- **THEN** the reissue packet body MUST include the runtime-issued
  `segment_targets`
- **AND** the reissue packet body MUST identify the terminal replay contract
  family, route scope, route version, final ledger source, and validation
  evidence context needed to submit a current correction.
