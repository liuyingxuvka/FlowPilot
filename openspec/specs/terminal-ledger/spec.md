# terminal-ledger Specification

## Purpose
TBD - created by archiving change split-terminal-ledger-source-entry-policy. Update Purpose after archive.
## Requirements
### Requirement: Terminal Ledger Source-Entry Child Boundary

The terminal ledger traceability module SHALL preserve existing helper names
while delegating source-of-truth entry construction to a child module.

#### Scenario: Source entry construction remains behavior-preserving

- **WHEN** terminal final ledger construction asks for root replay, route node,
  superseded node, child-skill, evidence, and generated-resource entries
- **THEN** the returned entry shapes and gate families SHALL keep the current
  final ledger behavior contract
- **AND** the parent facade helper names SHALL remain available

#### Scenario: Child boundary has direct evidence

- **WHEN** model-test alignment audits the new child source-entry boundary
- **THEN** the child source contracts SHALL be split into leaf model obligations
  for source-entry construction and requirement-trace projection
- **AND** each leaf obligation SHALL have its own current focused primary
  boundary evidence
- **AND** source audit SHALL report no undeclared side-effect or missing-symbol
  findings for the child boundary
