# full-model-test-code-diagnostics Specification

## ADDED Requirements

### Requirement: Clean closure requires no material-map structure split gap

Clean FlowPilot control-plane closure SHALL require model-test-code diagnostics
to report `alignment_ok=true`, `full_diagnostic_ok=true`, and
`full_coverage_ok=true` for the current source tree.

#### Scenario: Diagnostics still report a material-map split gap
- **WHEN** diagnostics report `needs_structure_split` for
  `flowpilot_material_artifact_map`
- **THEN** clean closure MUST remain blocked until the split is implemented and
  diagnostics are rerun against current sources.

### Requirement: New split child modules map to model and test evidence

Any child module introduced by the material-map split SHALL have model/test/code
binding evidence or the clean closure claim MUST remain blocked.

#### Scenario: A child module is missing evidence
- **WHEN** diagnostics find a new material-map child module without code
  contract or test evidence
- **THEN** model-test-code alignment MUST fail or report a blocking gap.
