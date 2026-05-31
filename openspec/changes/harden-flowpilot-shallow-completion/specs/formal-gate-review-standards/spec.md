## ADDED Requirements

### Requirement: Formal review blocks current shallow-completion traps
FlowPilot Reviewer gates SHALL treat an unresolved current shallow-completion
trap as a hard current-gate blocker when the reviewed gate claims to satisfy
the final user's practical outcome.

#### Scenario: Reviewer finds practical next step missing
- **WHEN** Reviewer reviews a PM formal gate package
- **AND** the accepted user outcome requires a runnable, operational,
  implementation-ready, or handoff-ready result
- **AND** the reviewed evidence still leaves the user's practical next step
  undefined
- **THEN** Reviewer SHALL return a blocked review with a PM-actionable
  recommended resolution
- **AND** Reviewer SHALL NOT pass the gate by classifying the issue only as a
  higher-standard suggestion.

#### Scenario: Reviewer passes bounded planning-only output
- **WHEN** the accepted user outcome is explicitly planning-only
- **AND** the reviewed artifact clearly states its planning boundary without
  claiming runnable or operational readiness
- **THEN** Reviewer MAY pass the gate if all other acceptance sources are met.
