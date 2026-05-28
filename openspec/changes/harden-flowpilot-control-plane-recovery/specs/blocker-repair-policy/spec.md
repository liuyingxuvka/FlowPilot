## ADDED Requirements

### Requirement: Same-family control blockers coalesce before new materialization
FlowPilot SHALL coalesce repeated control-plane blockers that share the same
attempt family instead of creating unbounded replacement blockers.

#### Scenario: Active same-family blocker is reused
- **WHEN** Router is about to materialize a control blocker
- **AND** an active blocker has the same attempt key, policy row, responsible
  role, originating action, and originating postcondition
- **THEN** Router MUST return or refresh the existing blocker family state
- **AND** Router MUST NOT write a new blocker artifact for the same failure.

#### Scenario: PM-pending same-family blocker remains pending
- **WHEN** a same-family blocker has already escalated to PM repair decision
- **THEN** Router MUST keep the existing PM repair lane active
- **AND** Router MUST NOT supersede it with another same-family blocker.

#### Scenario: Terminal same-family blocker prevents reopening
- **WHEN** a same-family blocker has been resolved by terminal stop,
  protocol-dead-end, or user stop
- **THEN** Router MUST return the terminal family disposition
- **AND** Router MUST NOT reopen the same family during heartbeat or manual
  resume.

### Requirement: Protocol dead-end writes durable blocker-family lifecycle
FlowPilot SHALL treat PM `protocol_dead_end` terminal decisions as durable
terminal outcomes for the originating blocker family.

#### Scenario: PM protocol dead-end closes active blocker
- **WHEN** PM submits an allowed control-blocker repair decision with
  `repair_transaction.plan_kind=terminal_stop`
- **AND** `recovery_option=protocol_dead_end`
- **THEN** Router MUST close the active blocker
- **AND** Router MUST write terminal lifecycle evidence naming the blocker,
  PM decision, repair transaction, originating action, and terminal reason.

#### Scenario: Later resume sees protocol dead-end
- **WHEN** heartbeat or manual resume evaluates the same originating action
  family after protocol-dead-end lifecycle has been written
- **THEN** Router MUST expose the terminal/protocol-repair boundary
- **AND** Router MUST NOT reissue the same action or create another blocker for
  that family.
