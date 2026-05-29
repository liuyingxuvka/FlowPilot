## ADDED Requirements

### Requirement: Validation Detects Shadow Result Drift
FlowPilot tiered validation SHALL include maintenance evidence that duplicate or
shadow validation artifacts are visible before release or install confidence is
claimed.

#### Scenario: Shadow artifacts exist
- **WHEN** validation artifacts include both canonical and shadow result files
- **THEN** maintenance tooling reports the shadow pair count and exact duplicate
  count
- **AND** final confidence must either remove the shadow files, prove they are the
  only current artifacts for their family, or report the cleanup as incomplete.
