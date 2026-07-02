# material-artifact-map Specification

## ADDED Requirements

### Requirement: Material artifact-map facade stays split and behavior-compatible

The material artifact-map public facade SHALL preserve its existing public
functions, schema name, output shape, and index-only authority while delegating
packet/result indexing and ordinary work-material scanning to focused child
modules.

#### Scenario: Material map is refreshed after the split
- **WHEN** the runtime refreshes a material artifact map
- **THEN** the written document MUST still exclude sealed body text
- **AND** sealed packet/result/report body refs MUST still require runtime open
- **AND** ordinary non-sealed project/run files MUST remain readable under the
  ordinary material policy even when absent from the navigation index.

#### Scenario: Public facade split debt is evaluated
- **WHEN** full model-test-code diagnostics inspect the material artifact-map
  facade
- **THEN** the facade MUST NOT produce a `needs_structure_split` finding.
