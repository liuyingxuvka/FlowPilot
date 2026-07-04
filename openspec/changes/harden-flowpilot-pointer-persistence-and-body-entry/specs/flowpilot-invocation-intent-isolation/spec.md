## ADDED Requirements

### Requirement: Pointer recovery does not infer invocation intent
FlowPilot SHALL treat pointer recovery as repair of UI focus/default-target
metadata only. Recovery MUST NOT attach to, resume, stop, supersede, or mutate
an existing run unless the command already has explicit intent for that run.

#### Scenario: Fresh startup with corrupt pointer
- **WHEN** the user starts a fresh FlowPilot invocation and the existing current
  pointer is corrupt
- **THEN** FlowPilot MUST create a new run according to fresh-startup rules
- **AND** it MUST NOT recover or select an old run as resume intent.

#### Scenario: Ambiguous recovery candidates
- **WHEN** current/index pointer recovery finds multiple valid run candidates
- **THEN** FlowPilot MUST return an ambiguous recovery blocker or require an
  explicit run target
- **AND** it MUST NOT select the newest run by timestamp.

#### Scenario: Explicit run target bypasses corrupt current pointer
- **WHEN** a diagnostic or repair command supplies an explicit run id
- **THEN** FlowPilot MAY load that run directly from `.flowpilot/runs/<run-id>`
- **AND** it MUST NOT re-resolve a different run from `.flowpilot/current.json`.
