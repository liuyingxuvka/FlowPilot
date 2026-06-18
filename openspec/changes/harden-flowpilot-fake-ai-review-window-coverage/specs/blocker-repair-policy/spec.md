## ADDED Requirements

### Requirement: Reviewer blockers are not PM-overridden
FlowPilot SHALL NOT resolve a Reviewer hard blocker by PM text alone when the
Reviewer gate remains available for repair and recheck.

#### Scenario: PM cannot bypass a Reviewer hard blocker
- **WHEN** Reviewer blocks a current gate with a hard blocker
- **AND** normal repair routing remains available
- **THEN** PM MUST NOT mark the gate passed solely by disagreeing with Reviewer
- **AND** PM MUST select a supported repair, route mutation, terminal stop, user question, or break-glass escalation path.

#### Scenario: Repair returns to same review gate
- **WHEN** PM selects an executable repair path for a Reviewer hard blocker
- **THEN** FlowPilot MUST preserve the blocker lineage
- **AND** the repaired evidence MUST be submitted to the same review gate or a recorded replacement gate before closure.

### Requirement: Repeated reviewer repair conflict escalates cleanly
FlowPilot SHALL escalate repeated irreconcilable Reviewer/repair failures only
after ordinary repair attempts cannot produce a legal next action or the
configured same-family threshold is reached.

#### Scenario: Repeated no-delta reviewer blocker reaches escalation
- **WHEN** the same Reviewer blocker family recurs without repair delta through the configured threshold
- **THEN** FlowPilot MUST escalate to user stop, protocol blocker, route mutation, or Controller break-glass according to the existing policy
- **AND** the escalation record MUST preserve the blocker lineage and repair attempts.
