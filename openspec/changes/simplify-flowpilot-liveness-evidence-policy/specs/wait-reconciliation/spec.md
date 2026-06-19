# wait-reconciliation Spec Delta

## MODIFIED Requirements

### Requirement: Wait Reconciliation Uses Source Closure Classification
FlowPilot wait reconciliation SHALL settle passive waits, ACK waits,
role-output waits, and scheduler waits from the closure classification of their
source obligation and from current ACK/progress liveness evidence age. It SHALL
NOT use host liveness probe status, `timeout_unknown`, or bounded wait timeout
labels as current wait authority.

#### Scenario: ACK wait reminder and replacement use lease age
- **WHEN** a packet lease has not been acknowledged
- **AND** less than 5 minutes have elapsed since lease creation
- **THEN** runtime keeps the wait in patrol
- **AND** it does not emit a role replacement duty.

#### Scenario: Missing ACK reminder
- **WHEN** a packet lease has not been acknowledged
- **AND** at least 5 minutes but less than 10 minutes have elapsed since lease
  creation
- **THEN** runtime emits the fixed ACK reminder duty.

#### Scenario: Missing ACK replacement
- **WHEN** a packet lease has not been acknowledged
- **AND** at least 10 minutes have elapsed since lease creation
- **THEN** runtime emits the current reissue-or-replace duty for that packet
  lease.

#### Scenario: ACK and progress are the only result-wait liveness evidence
- **WHEN** a packet lease has been acknowledged and no result is accepted
- **THEN** runtime computes liveness evidence from `ack_received_at` and
  `last_progress_at`
- **AND** runtime ignores host-liveness status fields for the current wait
  decision.

#### Scenario: Result wait progress reminder
- **WHEN** a packet lease has been acknowledged
- **AND** no accepted result exists
- **AND** at least 10 minutes but less than 30 minutes have elapsed since the
  latest ACK/progress evidence
- **THEN** runtime emits the fixed strong progress reminder duty
- **AND** it does not replace the lease.

#### Scenario: Result wait replacement after no evidence
- **WHEN** a packet lease has been acknowledged
- **AND** no accepted result exists
- **AND** at least 30 minutes have elapsed since the latest ACK/progress
  evidence
- **THEN** runtime emits the current reissue-or-replace duty for that packet
  lease.

#### Scenario: Legacy timeout fields are rejected
- **WHEN** current wait state or submitted liveness payload provides
  `timeout_unknown`, `host_liveness_status`, or
  `bounded_wait_result=timeout_unknown` as the basis for a wait decision
- **THEN** runtime rejects or ignores that unsupported current-contract input
- **AND** runtime does not translate it into a valid replacement decision.
