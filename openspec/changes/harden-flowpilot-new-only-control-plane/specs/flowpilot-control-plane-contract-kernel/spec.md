## ADDED Requirements

### Requirement: New-only packet outcomes are explicit JSON decisions

FlowPilot SHALL accept packet outcomes only from the current strict JSON result
contract and SHALL NOT infer success from prose, aliases, missing fields, or
unknown decision values.

#### Scenario: Result body lacks a decision
- **WHEN** a packet result body does not contain a top-level `decision`
- **THEN** runtime MUST treat the result as a mechanical protocol block
- **AND** runtime MUST NOT default the packet outcome to pass.

#### Scenario: Result body uses an old alias
- **WHEN** a packet result body uses `status`, `outcome`, prose declarations, or
  another old alias instead of top-level `decision`
- **THEN** runtime MUST reject that result for the current control path
- **AND** runtime MUST NOT translate the alias into a valid current decision.

### Requirement: PM repair decisions have one current shape

FlowPilot SHALL accept PM repair decisions only as a top-level JSON object with
the current required fields and SHALL NOT use nested wrappers or fallback reason
fields.

#### Scenario: PM decision uses nested wrapper
- **WHEN** a PM repair decision result places the decision under
  `repair_decision` or `pm_repair_decision`
- **THEN** runtime MUST reject the result as mechanically invalid
- **AND** runtime MUST NOT unwrap the nested value.

#### Scenario: PM decision omits current reason
- **WHEN** a PM repair decision omits top-level `reason`
- **THEN** runtime MUST reject the result as mechanically invalid
- **AND** runtime MUST NOT use `summary`, `recommended_resolution`, or prose as
  a fallback reason.

### Requirement: Same-family blockers converge to one current authority

FlowPilot SHALL retire older same-family active or awaiting-recheck blockers
when a newer repair, recheck, or PM decision path becomes the current authority.

#### Scenario: New repair packet supersedes old blocker
- **WHEN** an active blocker has a newer same-family repair or recheck packet
- **THEN** runtime MUST mark the older blocker with a non-active retired status
- **AND** final preflight MUST NOT block on that retired historical blocker.

#### Scenario: Stale live blocker remains active
- **WHEN** final preflight sees an active or awaiting-recheck blocker whose
  packet/result target is noncurrent and no current repair path owns it
- **THEN** runtime MUST report a current control-plane blocker
- **AND** runtime MUST NOT silently pass completion.

### Requirement: Superseded accepted evidence is historical only

FlowPilot SHALL keep accepted result evidence as history without allowing an
accepted-but-superseded packet to remain a current runtime target.

#### Scenario: Accepted result remains on superseded packet
- **WHEN** a packet has been superseded after repair
- **AND** the packet still records accepted result evidence for audit history
- **THEN** runtime MUST treat that packet as noncurrent
- **AND** routing, blocker selection, PM decisions, and final preflight MUST NOT
  use that accepted evidence as live authority.

### Requirement: Formal FlowPilot entrypoints expose only the current runtime

FlowPilot SHALL expose only the current runtime path through formal CLI/help
and installed skill surfaces.

#### Scenario: Formal entrypoint lists old router path
- **WHEN** a user or install check inspects the FlowPilot formal entrypoint
- **THEN** old router compatibility, legacy fallback, or bypass commands MUST
  NOT be advertised as runtime options
- **AND** any test-only rehearsal helper MUST be clearly outside the formal
  runtime path.
