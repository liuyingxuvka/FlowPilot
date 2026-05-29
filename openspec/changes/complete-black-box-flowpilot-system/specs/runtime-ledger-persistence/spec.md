## ADDED Requirements

### Requirement: Complete Runtime Ledger Persistence

Runtime ledger persistence SHALL cover the complete black-box system state,
including routes, route mutations, packets, results, leases, FlowGuard work
orders, reviews, validation evidence, Cockpit projections, lifecycle events,
and final closure records.

#### Scenario: Router resumes after interruption

- **WHEN** the router resumes a current run after interruption
- **THEN** it MUST load the current run ledger, event log, route pointer,
  packet/result envelopes, leases, FlowGuard orders, reviews, and evidence
  before selecting the next action.

### Requirement: Projection Files Are Derived

Runtime projection files SHALL be derived views over canonical ledger state and
SHALL NOT authorize route advancement by themselves.

#### Scenario: Status projection says complete while ledger has blockers

- **WHEN** `console/status.json` or a chat route sign says complete
- **AND** the ledger still has unresolved blockers or missing closure evidence
- **THEN** the router MUST treat the run as incomplete.
