## ADDED Requirements

### Requirement: BCL And PPA Obligations Bind To Current Evidence
FlowPilot model-test alignment SHALL bind Behavior Commitment Ledger and
Primary Path Authority obligations to owner code contracts, model obligations,
canonical negative cases, and ordinary test evidence before broad no-fallback
claims are trusted.

#### Scenario: No-fallback alignment is inspected
- **WHEN** the model-test alignment runner inspects no-fallback or path-authority obligations
- **THEN** it SHALL find rows that bind the commitment id, PPA boundary, owner code contract, generated case or shard id, and current passing test evidence.

#### Scenario: Alignment row is missing
- **WHEN** a commitment or PPA obligation lacks current model, code, generated-case, or test evidence
- **THEN** alignment SHALL report the gap instead of allowing broad no-fallback confidence.

### Requirement: Field Lifecycle Projections Bind To Tests
FlowPilot model-test alignment SHALL consume field lifecycle projections for
behavior-bearing fields and reject field confidence when tests only cover
helper internals or stale source rows.

#### Scenario: Behavior-bearing field is reviewed
- **WHEN** a field lifecycle projection marks a field behavior-bearing
- **THEN** model-test alignment SHALL bind that projection to an owner code contract and external or mixed-scope test evidence.
