## ADDED Requirements

### Requirement: Validation Uses New-Only Runtime Evidence
FlowPilot validation SHALL prove current runtime behavior and rejection of old
inputs without requiring legacy equivalence or legacy-full checks as current
release gates.

#### Scenario: Current validation suite runs
- **WHEN** the current validation suite is executed after compatibility removal
- **THEN** it includes current startup, event, transaction, prompt-boundary,
  install, and model-alignment evidence

#### Scenario: Legacy equivalence check exists
- **WHEN** a legacy-to-router, barrier-equivalence, legacy-prompt, or
  legacy-full check remains in the repository
- **THEN** it is not required for install freshness or current release
  confidence
- **AND** it SHALL NOT be reported as proof that old runtime paths remain
  supported
