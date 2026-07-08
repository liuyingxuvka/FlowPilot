## ADDED Requirements

### Requirement: Reviewers Block Core Deliverable Substitution
FlowPilot Reviewer gates SHALL block a current gate when the current evidence only inventories, labels, explains, or honestly reports missing work while the user required a concrete deliverable, unless the user explicitly approved the lowered scope.

#### Scenario: Honest missing status is not completion
- **WHEN** a worker or PM formal gate package reports missing, inaccessible, not extracted, not run, unavailable, partial, or current-reachable-only status for a user-required deliverable
- **THEN** Reviewer SHALL treat the report as blocker or clarification evidence, not completion evidence.

#### Scenario: Nonblocking quality suggestion remains scoped
- **WHEN** Reviewer finds an optional improvement that does not prove a hard user-intent failure, missing proof, semantic downgrade, role-boundary failure, or protocol violation
- **THEN** Reviewer SHALL record the item as PM decision support through existing suggestion fields instead of converting it into a hard blocker.
