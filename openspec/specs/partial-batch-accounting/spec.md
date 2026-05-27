# partial-batch-accounting Specification

## Purpose
TBD - created by archiving change optimize-flowpilot-wait-reconciliation. Update Purpose after archive.
## Requirements
### Requirement: Batch members have independent status
Each Router-owned packet batch SHALL track every member packet with packet id, target role, holder, dependency class, relay state, ACK/progress state, result state, and result envelope reference.

#### Scenario: One member returns before another
- **WHEN** worker A returns a valid result and worker B remains pending in the same batch
- **THEN** the batch records worker A as returned, worker B as missing, and the aggregate returned count as one

### Requirement: Batch summaries name remaining work accurately
The user-facing and controller-facing batch summary SHALL derive missing roles and counts from refreshed member state, not from stale expected-role fields.

#### Scenario: Old expected role differs from actual pending role
- **WHEN** the old wait names worker A but worker A has returned and worker B is still pending
- **THEN** the status summary says worker A returned and worker B remains pending

### Requirement: Protected joins require all blocking members
The Router SHALL NOT mark a blocking batch as joined, reviewed, PM-absorbed, or stage-advanceable until all blocking member packets have returned or been explicitly canceled or superseded by an authorized PM decision.

#### Scenario: Blocking member still missing
- **WHEN** a material-scan batch has one missing blocking member
- **THEN** material sufficiency, PM final absorption, reviewer formal gate, and stage advancement remain unavailable

### Requirement: Partial batch accounting distinguishes dispatch from completion
FlowPilot SHALL allow relay/open/ACK evidence to prove packet dispatch while still requiring result evidence for worker completion.

#### Scenario: Batch has relayed packets and partial results
- **WHEN** all packet envelopes in a batch have relay evidence
- **AND** one worker result has returned while another worker result is still pending
- **THEN** Router MUST satisfy the packet-dispatch postcondition
- **AND** Router MUST keep the result-completion wait open for the pending worker

#### Scenario: Packet dispatch is proven by worker open evidence
- **WHEN** an addressed worker has opened or ACKed its packet
- **THEN** Router MAY use that evidence to prove the packet was dispatched to that worker
- **AND** Router MUST NOT treat that open or ACK as the worker's result completion

### Requirement: Partial result relay folds only returned results
FlowPilot SHALL fold result relay postconditions only from returned result envelopes that were relayed to the expected recipient.

#### Scenario: Result relay is attempted before every worker returns
- **WHEN** a result relay action covers only returned result envelopes
- **AND** other workers in the batch are still pending
- **THEN** Router MUST reconcile the relay postcondition only for the returned result scope
- **AND** Router MUST continue waiting or repairing the unresolved worker scope separately

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

### Requirement: Batch member summaries expose PM outcomes
Each Router-owned packet batch SHALL record the PM package disposition outcome for each member packet when a PM package-result disposition is recorded.

#### Scenario: Mixed PM packet outcomes
- **WHEN** a PM disposition records accepted outcome for one packet and rework outcome for another packet in the same batch
- **THEN** the batch summary records each packet's PM outcome next to its packet id and target role
- **AND** aggregate advancement remains blocked until the rework outcome is resolved through an authorized path

### Requirement: Absorption requires all blocking members accepted
The Router SHALL NOT mark a package batch as PM-absorbed when any blocking member packet has a PM outcome other than accepted.

#### Scenario: Aggregate absorbed contradicts packet rework
- **WHEN** a PM package-result disposition has aggregate decision `absorbed`
- **AND** any member packet outcome is `rework_requested`, `blocked`, `canceled`, or `route_or_node_mutation_required`
- **THEN** the Router rejects the disposition instead of writing a contradictory absorbed batch state
