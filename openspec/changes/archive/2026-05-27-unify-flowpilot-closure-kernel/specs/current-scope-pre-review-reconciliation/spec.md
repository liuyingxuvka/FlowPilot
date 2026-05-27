## ADDED Requirements

### Requirement: Current-Scope Blockers Use Closure Kernel
Current-scope pre-review reconciliation SHALL decide whether local obligations
still block review by using the shared FlowPilot closure kernel rather than a
module-local list of closed statuses.

#### Scenario: Resolved reconciled Controller action does not block review
- **WHEN** a current-scope Controller action has `status=resolved` and its Router
  reconciliation evidence is complete for the same obligation
- **THEN** pre-review reconciliation treats the action as nonblocking and does
  not keep the current scope in a passive wait

#### Scenario: Closed Worker or PM lifecycle row does not block review
- **WHEN** a current-scope Worker or PM lifecycle record has role-specific
  closed evidence accepted by the closure kernel
- **THEN** pre-review reconciliation treats the record as nonblocking without
  requiring Controller-specific status vocabulary
