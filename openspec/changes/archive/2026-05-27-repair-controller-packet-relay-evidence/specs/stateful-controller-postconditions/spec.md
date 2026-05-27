## ADDED Requirements

### Requirement: Packet relay receipts require runtime relay evidence
The Router SHALL NOT reconcile a Controller packet or result relay `done` receipt until every addressed envelope has verified Controller relay evidence in the envelope and matching packet ledger holder/status evidence.

#### Scenario: Done receipt without relay signature stays incomplete
- **WHEN** Controller records a `done` receipt for a packet/result relay action but an addressed envelope lacks a valid `controller_relay`
- **THEN** Router MUST NOT set the relay postcondition flag
- **AND** Router MUST mark the original Controller action as incomplete, retry-pending, or repair-pending rather than reconciled

#### Scenario: Done receipt with verified relay evidence closes
- **WHEN** Controller records a `done` receipt for a packet/result relay action and every addressed envelope has valid Controller relay evidence plus matching packet ledger holder/status evidence
- **THEN** Router MUST reconcile the receipt, set the declared relay postcondition, and avoid reissuing the same relay action

### Requirement: Active-holder relay postconditions include lease evidence
For packet relay actions that declare an active-holder fast lane, the Router SHALL require valid active-holder lease evidence after runtime relay whenever a live target agent id is available.

#### Scenario: Relay signature exists but required lease is missing
- **WHEN** a packet relay action declares active-holder fast-lane lease issuance and the target live agent id is known, but the packet has no valid active-holder lease
- **THEN** Router MUST keep the relay postcondition incomplete or repair-pending
- **AND** Router MUST expose the missing lease as Controller/Router mechanical evidence, not Worker completion evidence
