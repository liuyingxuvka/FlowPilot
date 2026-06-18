## ADDED Requirements

### Requirement: Review-window completeness validation is tiered and current
FlowPilot SHALL include review-window completeness tests in the focused
validation tier and FlowGuard matrix checks. Broad completion or release
confidence MUST not count stale, skipped, progress-only, or ownerless
review-window evidence as passing.

#### Scenario: Focused tier runs review-window checks
- **WHEN** the focused validation tier is run for this change
- **THEN** it MUST execute the review-window runtime tests, fake-AI responder
  profile tests, and completeness matrix checks.

#### Scenario: Changed matrix stales downstream evidence
- **WHEN** the review-window completeness declarations, fake-AI profiles, or
  generated cell ids change
- **THEN** prior focused test, model-test alignment, topology, and install-sync
  evidence MUST be considered stale
- **AND** the affected checks MUST be rerun before completion is claimed.

#### Scenario: Background regression needs final artifacts
- **WHEN** broad model regressions are run in the background
- **THEN** their stdout, stderr, combined output, exit code, and metadata
  artifacts MUST exist before they count as pass evidence.
