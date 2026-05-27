## ADDED Requirements

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
