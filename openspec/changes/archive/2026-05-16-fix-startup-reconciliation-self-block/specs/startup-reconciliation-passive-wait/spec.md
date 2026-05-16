## ADDED Requirements

### Requirement: Startup Reconciliation Ignores Passive Wait Status Rows
The system SHALL NOT treat Router-owned passive wait status rows as unresolved
startup Controller work during startup pre-review reconciliation.

#### Scenario: Startup reconciliation wait does not block itself
- **WHEN** all startup-local obligations are reconciled and the only remaining
  startup-scoped Controller row is an `await_current_scope_reconciliation`
  passive wait status row
- **THEN** startup pre-review reconciliation reports no pending startup
  Controller-row blocker and the Router may clear the passive wait

#### Scenario: Ordinary startup work still blocks review
- **WHEN** a startup-scoped ordinary Controller work row is not closed and
  Router-reconciled
- **THEN** startup pre-review reconciliation reports a pending startup
  Controller-row blocker before Reviewer startup fact work

#### Scenario: Passive wait side effects remain blocking when declared
- **WHEN** a wait-shaped startup action declares a Controller side effect or
  Controller receipt requirement
- **THEN** startup pre-review reconciliation may treat it as ordinary work
  until its side effect is closed and Router-reconciled
