## ADDED Requirements

### Requirement: Wrong-path trace replay
Synthetic agent trace replay SHALL exercise route-authority wrong-path traces from invalid submission through structured rejection and corrected retry.

#### Scenario: PM wrong path then corrected path
- **WHEN** trace replay submits a project-manager route action outside the current legal action set, then resubmits using the required repair command
- **THEN** the first submission is rejected without state progress and the second submission returns to the accepted route-control path

#### Scenario: Old alias remains rejected
- **WHEN** trace replay submits a legacy action alias after wrong-path feedback
- **THEN** FlowPilot rejects the alias again and does not use fallback translation

### Requirement: Role-overreach trace replay
Synthetic agent trace replay SHALL include role-overreach traces for Worker, Reviewer, and FlowGuard operator route-control attempts.

#### Scenario: Worker cannot act as PM
- **WHEN** trace replay submits a PM route-control event from a Worker output
- **THEN** FlowPilot rejects the event and preserves current route/frontier state
