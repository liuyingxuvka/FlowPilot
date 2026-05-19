## ADDED Requirements

### Requirement: Evidence-backed Controller receipts fold through registered handlers
FlowPilot SHALL register every evidence-backed packet/result relay Controller action that writes a Router-owned postcondition flag with an idempotent receipt evidence-fold handler.

#### Scenario: Registered packet relay receipt with evidence
- **WHEN** Controller records a `done` receipt for a registered packet relay action and Router-visible packet relay evidence validates
- **THEN** Router MUST set the registered Router-owned postcondition flag
- **AND** Router MUST mark the receipt reconciled without creating a control blocker

#### Scenario: Registered result relay receipt with evidence
- **WHEN** Controller records a `done` receipt for a registered result relay action and Router-visible result relay evidence validates
- **THEN** Router MUST set the registered Router-owned postcondition flag
- **AND** Router MUST mark the receipt reconciled without reading sealed result bodies

### Requirement: Evidence folds use Router-visible records only
FlowPilot SHALL fold packet/result relay receipts from Router-visible evidence and SHALL NOT inspect sealed packet or result bodies during receipt reconciliation.

#### Scenario: Packet dispatch evidence exists
- **WHEN** packet ledger, packet envelopes, Controller relay history, parallel batch state, active-holder leases, packet-open records, or ACK/progress records prove packet dispatch
- **THEN** Router MAY use those records to satisfy the packet relay postcondition
- **AND** Router MUST NOT read packet body content

#### Scenario: Result relay evidence exists
- **WHEN** result envelopes and Controller relay metadata prove result relay to the expected recipient
- **THEN** Router MAY use those records to satisfy the result relay postcondition
- **AND** Router MUST NOT read result body content

### Requirement: Missing evidence remains repairable
FlowPilot SHALL reserve retry and control-blocker paths for relay receipts whose required Router-visible evidence is missing, invalid, or contradictory.

#### Scenario: Receipt is done but evidence is missing
- **WHEN** Controller records a `done` relay receipt but Router cannot prove the registered evidence fold
- **THEN** Router MUST NOT set the postcondition flag
- **AND** Router MUST schedule bounded retry or control-blocker evidence using the existing Controller repair path

### Requirement: Packet-open evidence leads to wait, not reissue
FlowPilot SHALL treat packet-open, ACK, active-holder, or progress evidence as proof that packet work is in progress and SHALL NOT reissue the same packet relay action as ordinary work.

#### Scenario: Worker opened packet but result is pending
- **WHEN** a worker has opened or ACKed a relayed packet and the result envelope is not yet returned
- **THEN** Router MUST wait for the worker result or authorized blocker
- **AND** Router MUST NOT issue a duplicate packet relay action for the same packet family and packet ids
