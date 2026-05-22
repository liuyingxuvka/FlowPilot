## ADDED Requirements

### Requirement: Runtime State Persistence Child Boundary

The runtime-state module SHALL preserve existing helper names while delegating
run-state persistence and stale-save reconciliation to a child module.

#### Scenario: Stale-save merge behavior remains behavior-preserving

- **WHEN** a loaded run state is saved after the file changed on disk
- **THEN** append-only lists, compatible pending waits, reminder fields, and
  concurrently raised flags SHALL be merged with the current save payload using
  the existing behavior
- **AND** volatile load metadata SHALL not be written to disk

#### Scenario: Child boundary has direct evidence

- **WHEN** model-test alignment audits the new child persistence boundary
- **THEN** the child source contracts SHALL be split into leaf obligations for
  stale-save merge and load/save persistence behavior
- **AND** each leaf obligation SHALL have current focused primary evidence for
  its own code boundary
- **AND** source audit SHALL report no undeclared side-effect or missing-symbol
  findings for the child boundary
