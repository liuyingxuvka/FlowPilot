## MODIFIED Requirements

### Requirement: System Card ACKs Clear Scoped Read Obligations
The system SHALL treat system-card ACKs as mechanical read receipts scoped to a route gate, node, bundle, or work-packet preflight, and SHALL NOT treat a Controller delivery receipt as target-role work completion.

#### Scenario: Controller delivery closes only Controller work
- **WHEN** Controller relays a system-card envelope or formal work-packet envelope
- **THEN** Router records only the Controller-owned delivery step as done and keeps the target-role wait open until the target role returns the required ACK, report, or result event

#### Scenario: ACK-only system-card ACK clears read wait
- **WHEN** a role submits a valid ACK for a system card classified as `ack_only_prompt`
- **THEN** Router may clear the scoped ACK/read wait for that card
- **AND** the role is not kept busy by that ACK-only card after the wait is reconciled

#### Scenario: Output-bearing card ACK does not complete semantic work
- **WHEN** a role submits a valid system-card ACK for a card classified as `output_bearing_work_package`
- **THEN** Router may clear the scoped read obligation
- **AND** Router MUST keep any PM, reviewer, officer, or worker semantic decision/result gate open until its own report, result, decision, or packet-spec event arrives
