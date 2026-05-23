## ADDED Requirements

### Requirement: Missing relay evidence is mechanically repairable by Controller
When a packet/result relay receipt is missing runtime relay evidence but the envelope is otherwise valid and relayable, Router SHALL create a Controller-owned mechanical repair/replay path before escalating to PM.

#### Scenario: Missing relay signature has valid envelope
- **WHEN** Router reconciles a relay `done` receipt and finds `packet_dispatch_evidence_missing` only because `controller_relay` is absent from an otherwise relayable envelope
- **THEN** Router MUST issue or preserve Controller work to perform the runtime relay operation
- **AND** Router MUST NOT immediately materialize a PM-handled control blocker for that omission

#### Scenario: Relay repair succeeds
- **WHEN** the Controller mechanical repair writes valid runtime relay evidence for the missing envelope
- **THEN** Router MUST reconcile the original relay postcondition and supersede or resolve the repair row without requiring a PM repair decision
