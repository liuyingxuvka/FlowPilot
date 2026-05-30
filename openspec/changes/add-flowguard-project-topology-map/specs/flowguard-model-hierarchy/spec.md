## ADDED Requirements

### Requirement: Readiness surfaces include topology artifacts
The FlowGuard model hierarchy and local readiness surfaces SHALL verify that
project topology artifacts exist, are current, and are not confused with parent
or child model proof.

#### Scenario: Install readiness checks topology
- **WHEN** install readiness validation runs in this mature FlowGuard project
- **THEN** it MUST verify the topology generator, JSON artifact, Markdown
  artifact, and check command succeed
- **AND** it MUST continue to require the owning model, test, hierarchy, mesh,
  and install evidence for readiness claims.

#### Scenario: Hierarchy and topology stay distinct
- **WHEN** hierarchy evidence is evaluated for parent or child model confidence
- **THEN** topology artifacts MUST NOT be counted as child model evidence,
  parent reattachment evidence, or full-regression proof
- **AND** stale topology MUST be reported as an orientation-maintenance gap.
