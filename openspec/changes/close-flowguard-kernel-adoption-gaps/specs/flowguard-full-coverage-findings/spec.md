## ADDED Requirements

### Requirement: Full diagnostic findings block adoption completion claims
FlowPilot SHALL NOT claim FlowGuard-kernel adoption closure while the current
full model-test-code diagnostic reports unresolved actionable findings for
in-scope runtime-owner surfaces.

#### Scenario: Subset alignment cannot hide full diagnostic findings
- **WHEN** selected model-test alignment passes
- **AND** the full diagnostic still reports `internal_only_test`,
  missing-contract, stale-evidence, or boundary-mismatch findings for an
  in-scope runtime-owner surface
- **THEN** completion remains blocked or explicitly scoped
- **AND** the final evidence report names the unresolved finding class

#### Scenario: Resolved findings are validated by executable evidence
- **WHEN** the missing contract or test evidence is added
- **THEN** focused tests and the full model-test-code diagnostic run again
- **AND** adoption completion only proceeds if the relevant findings are absent
  from the current diagnostic artifact
