## MODIFIED Requirements

### Requirement: PM repair transactions are executable
FlowPilot SHALL require each PM control-blocker repair decision to provide a
`repair_transaction.plan_kind` that Router can validate as executable before
committing the repair transaction, and FlowPilot SHALL keep multi-round fake AI
rehearsal evidence for repair decisions that would otherwise create a
no-producer follow-up wait.

#### Scenario: Router commits only executable repair decisions
- **WHEN** PM submits a control-blocker repair decision for the active blocker
- **THEN** Router validates the selected `repair_transaction.plan_kind` and commits the transaction only when the plan has a concrete queued action, an existing event producer, a named Router handler, or a terminal stop.

#### Scenario: Router rejects empty waits
- **WHEN** PM submits a repair transaction that asks Router to wait for an event with no current producer or queued action
- **THEN** Router rejects the PM decision and leaves the original control blocker active for a corrected PM decision.

#### Scenario: Multi-round rehearsal covers no-producer repair waits
- **WHEN** prepared fake AI work packages exercise a bad package followed by a no-producer PM repair decision
- **THEN** the multi-round rehearsal evidence MUST show that the bad repair cannot advance the route
- **AND** the corrected repair MUST demonstrate current producer evidence before the route continues.
