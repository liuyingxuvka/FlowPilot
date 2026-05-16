## ADDED Requirements

### Requirement: PM recovery option is not execution authority
FlowPilot SHALL keep `recovery_option` and `repair_action` as PM policy context
and human-readable explanation, while `repair_transaction.plan_kind` controls
Router execution.

#### Scenario: Same recovery option can choose different executable plans
- **WHEN** PM selects a policy recovery option such as same-gate repair
- **THEN** PM must also select an executable `repair_transaction.plan_kind`, and Router executes the plan kind rather than inferring behavior from the recovery option.

#### Scenario: Repair action text does not commit route progress
- **WHEN** PM writes human-readable repair action text
- **THEN** Router does not treat that text as a queued repair action, a passed gate, or an event producer unless the repair transaction contains a validated executable plan.

### Requirement: PM guidance maps failures to executable repair plans
FlowPilot SHALL instruct PM when to choose each executable repair plan kind for
control-blocker recovery.

#### Scenario: PM selects operation replay for repeatable operations
- **WHEN** the blocked work can be safely repeated from a recorded operation
- **THEN** PM uses `operation_replay` and names the recorded operation instead of requesting an open-ended redo.

#### Scenario: PM selects Controller repair packet for bounded AI repair
- **WHEN** the fix requires Controller to perform limited repair work within current authority
- **THEN** PM uses `controller_repair_work_packet` and supplies bounded reads, writes, forbidden actions, and success evidence.

#### Scenario: PM selects route mutation only for structural changes
- **WHEN** the repair requires adding, removing, or changing route nodes, gates, or acceptance boundaries
- **THEN** PM uses `route_mutation` rather than using ordinary replay or reissue.
