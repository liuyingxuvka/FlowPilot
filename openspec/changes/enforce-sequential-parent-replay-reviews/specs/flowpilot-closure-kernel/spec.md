## ADDED Requirements

### Requirement: Terminal replay waits for reviewed parent replay evidence
FlowPilot SHALL NOT issue terminal backward replay while any effective
parent/module/top-level replay result is missing its current independent
review.

#### Scenario: Terminal replay blocked by missing parent replay review
- **WHEN** final route-wide ledgers are otherwise clean
- **AND** an effective parent replay result lacks accepted independent review
- **THEN** FlowPilot SHALL NOT issue terminal backward replay
- **AND** FlowPilot SHALL expose the missing parent replay review as the next
  dependency-ordered repair

### Requirement: Closure diagnostics do not define repair ordering
FlowPilot SHALL keep final closure diagnostics separate from actionable repair
ordering. Final closure MAY aggregate all unresolved closure blockers for
diagnostics, but repair selection SHALL use current route topology and evidence
dependencies rather than sorted blocker text.

#### Scenario: Diagnostic list contains downstream blockers
- **WHEN** final closure reports both a child/module replay review gap and a
  top-level replay review gap
- **THEN** FlowPilot SHALL keep both blockers visible in diagnostics
- **AND** FlowPilot SHALL select the child/module gap as the only current
  actionable repair
