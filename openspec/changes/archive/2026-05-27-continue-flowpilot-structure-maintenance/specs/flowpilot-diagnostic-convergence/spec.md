## MODIFIED Requirements

### Requirement: Full model-test-code convergence evidence
FlowPilot SHALL maintain an executable diagnostic that compares model
obligations, externally visible code contracts, ordinary test evidence,
structure boundaries, and background evidence across the full diagnostic
surface.

#### Scenario: No unresolved non-deferred gaps
- **WHEN** the full diagnostic is regenerated after structure maintenance
- **THEN** the report SHALL show zero unresolved non-deferred gaps and SHALL keep any remaining StructureMesh debt explicitly deferred

#### Scenario: Runner split does not weaken evidence
- **WHEN** the model-test alignment runner delegates its implementation to child modules
- **THEN** the same diagnostic command SHALL still emit the same top-level result fields and known-bad sanity checks
