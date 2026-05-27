## ADDED Requirements

### Requirement: Role recovery readiness uses current transaction proof
FlowPilot SHALL treat a role recovery report as ready only when it proves the
latest role recovery transaction for the active run and affected role set.

#### Scenario: Stale report is rejected
- **WHEN** the latest role recovery transaction has id `T2`
- **AND** `role_recovery_report.json` has id `T1`
- **THEN** Router MUST NOT treat the report as current recovery readiness
- **AND** Router MUST expose recovery work or a concrete blocker before normal
  role-dependent work continues.

#### Scenario: Crew slot transaction mismatch blocks readiness
- **WHEN** the recovery report has transaction id `T2`
- **AND** an affected role slot has `last_role_recovery_transaction_id` other
  than `T2`
- **THEN** Router MUST NOT count that role as recovered for `T2`.

### Requirement: Role liveness proof is host addressability proof
FlowPilot SHALL distinguish role identity, replacement intent, and current host
addressability before allowing role-dependent work.

#### Scenario: Unknown liveness is not active
- **WHEN** a role slot has an agent id
- **AND** the slot host liveness is `unknown`, `missing`, `cancelled`,
  `completed`, or `timeout_unknown`
- **THEN** Router MUST NOT treat the role as active.

#### Scenario: Replacement intent is not liveness
- **WHEN** a role slot records that a replacement was spawned or requested
- **AND** no current host addressability proof exists for the replacement agent
- **THEN** Router MUST NOT mark host liveness as proven.

### Requirement: Active-holder leases require current liveness proof
FlowPilot SHALL validate packet active-holder leases against the current role
slot, current agent id, and current host addressability proof.

#### Scenario: Lease holder has no active host proof
- **WHEN** a packet active-holder lease names a role and agent id
- **AND** the matching crew slot lacks current active host liveness proof
- **THEN** the packet runtime MUST reject the lease as not currently live.

### Requirement: Report reclaim is transaction-scoped
FlowPilot SHALL only reclaim an existing role recovery report for idempotent
receipt handling when the report proves the same latest transaction.

#### Scenario: Blocked receipt sees old report
- **WHEN** a `recover_role_agents` receipt has no usable recovered-agent payload
- **AND** the existing role recovery report belongs to an older transaction
- **THEN** Router MUST NOT reclaim the old report
- **AND** Router MUST keep or reissue the current recovery obligation.

### Requirement: Role recovery status explains proof state
FlowPilot SHALL expose role recovery status using separate fields for recovery
request, replacement creation, memory seeding, and host liveness verification.

#### Scenario: Replacement exists but is not addressable
- **WHEN** a replacement agent id has been written
- **AND** host addressability is not verified
- **THEN** status output MUST report the role as recovery-incomplete rather than
  all roles ready.
