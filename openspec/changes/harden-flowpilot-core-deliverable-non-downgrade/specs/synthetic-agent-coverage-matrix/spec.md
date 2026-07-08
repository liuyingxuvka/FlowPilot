## ADDED Requirements

### Requirement: Synthetic Matrix Covers Core Deliverable Downgrade Branches
FlowPilot synthetic coverage SHALL include generic fake-AI and replay branches where PM, Worker, or Reviewer replaces a concrete user deliverable with a weaker status-only, reachable-only, report-only, honest-missing, partial-quantity, unverified-test, or child-skill-lowered substitute.

#### Scenario: Generic downgrade branches are present
- **WHEN** the synthetic agent coverage matrix is generated
- **THEN** it SHALL include non-live regression rows for PM route downgrade, Worker honest-missing substitute, Reviewer shallow pass, final ledger status-only closure, and child-skill lower-standard branches across finite deliverable classes.

#### Scenario: Matrix does not overclaim live completion
- **WHEN** a downgrade branch is covered by fake-AI or synthetic replay evidence
- **THEN** the matrix SHALL classify the row as regression evidence and SHALL NOT use it as live project completion evidence.
