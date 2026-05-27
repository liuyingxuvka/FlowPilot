## ADDED Requirements

### Requirement: Worker batch waits derive roles from members
Worker batch wait summaries SHALL derive missing roles from refreshed batch
members before falling back to event-name role inference.

#### Scenario: Two-worker material batch is waiting
- **WHEN** a material scan batch has active holder members for `worker_a` and
  `worker_b`
- **AND** neither result has returned
- **THEN** current-work and Controller-facing wait summaries name both
  `worker_a` and `worker_b` as missing roles.

#### Scenario: One worker remains missing
- **WHEN** `worker_a` has returned and `worker_b` remains active in the same
  batch
- **THEN** current-work and reminder projections name `worker_b` as the missing
  role
- **AND** they MUST NOT collapse the wait to `worker_a` because the event name
  starts with `worker_`.
