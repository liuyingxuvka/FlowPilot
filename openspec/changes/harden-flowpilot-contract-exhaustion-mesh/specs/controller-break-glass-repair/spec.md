## ADDED Requirements

### Requirement: Break-glass loop identity includes root cause
Controller break-glass eligibility SHALL track stable root-cause identity for
control-plane loops in addition to surface blocker family.

#### Scenario: Surface blocker changes but root cause repeats
- **WHEN** the same control-plane evidence-chain root cause repeats through
  different surface blocker classes, gate kinds, or reissue packets without
  actionable repair delta
- **THEN** Controller MUST count the repeat toward the same root-cause loop
  instead of resetting solely because the surface blocker family changed

#### Scenario: Ordinary repair progress does not trigger break-glass
- **WHEN** a repeated blocker includes a new actionable repair delta, a new
  current evidence artifact, a corrected authorized read, or a different root
  cause
- **THEN** Controller MUST NOT treat the event as the same no-delta
  root-cause loop

### Requirement: Break-glass is an alarm, not rehearsal success
Controller break-glass SHALL be used to detect unrepaired repeated
control-plane loops, not to certify that a formal FlowPilot rehearsal is
healthy.

#### Scenario: Five same-root repeats require alarm evidence
- **WHEN** the same root-cause blocker repeats at the configured threshold with
  no actionable repair delta
- **THEN** Controller MUST expose GlassBreak eligibility as an alarm

#### Scenario: Formal rehearsal enters break-glass
- **WHEN** a formal FlowPilot rehearsal enters GlassBreak before the normal
  repair route resolves the blocker
- **THEN** the rehearsal MUST be treated as failing and the normal repair route
  MUST be fixed before confidence can be claimed

#### Scenario: Current stuck guard is visible before break-glass
- **WHEN** the current lifecycle guard reports `control_plane_stuck`
- **THEN** Controller, ModelMesh, and process-liveness evidence MUST expose the
  current stuck state as a blocker instead of treating prior stuck absorption
  as permission to continue
