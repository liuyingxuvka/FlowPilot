# control-plane-friction-root Specification

## Purpose
TBD - created by archiving change harden-control-plane-friction-root. Update Purpose after archive.
## Requirements
### Requirement: Controller Work Identity Is Work-Unit Scoped

Controller actions and router scheduler rows MUST distinguish concrete packet,
request, batch, and recipient work units before reusing an existing row or
closed action.

#### Scenario: Two PM role-work requests share a label but not identity

- **GIVEN** two relay actions have the same action type and label
- **AND** they target different `request_id`, `packet_id`, `packet_ids`,
  `batch_id`, or `to_role`
- **WHEN** FlowPilot projects them into Controller/scheduler ledgers
- **THEN** their identity fingerprints and scheduler idempotency keys differ

### Requirement: Failed Delivery Cannot Close A Controller Receipt

Controller receipts marked `done` MUST NOT be accepted when their payload
reports a failed host or message delivery.

#### Scenario: Done receipt includes failed agent delivery

- **GIVEN** a Controller receipt has `status=done`
- **AND** its payload has `message_delivery_status=failed_agent_not_found`
- **WHEN** FlowPilot records the receipt
- **THEN** the receipt is rejected before the action or scheduler row can close

### Requirement: Packet Ledger Writes Are Atomic And Recoverable

Packet ledger writes MUST use serialized atomic replacement with readback
verification. Ledger reads used by packet runtime updates MUST recover from
corrupt duplicate-tail JSON by preserving a corrupt backup and continuing from
a valid object when possible.

#### Scenario: Corrupt packet ledger has duplicate trailing JSON

- **GIVEN** `packet_ledger.json` contains one valid JSON object followed by
  trailing duplicate bytes
- **WHEN** packet runtime updates a packet record
- **THEN** FlowPilot writes a corrupt backup, restores a valid ledger, records
  recovery metadata, and does not crash

### Requirement: Active Holder Lease Requires Live Role Evidence

Active-holder leases MUST be issued only to the packet `to_role` and exact
current agent id proven by the run's live crew ledger evidence.

#### Scenario: Holder agent id is not current for role

- **GIVEN** the target role has no live crew slot for the requested agent id
- **WHEN** the packet runtime tries to issue an active-holder lease
- **THEN** the lease is rejected

### Requirement: Material Gate Evidence Authority Is Runtime-Backed

Material artifact maps and PM formal gate packages MUST NOT advertise raw
result-body authority for a reviewer unless runtime relay/open evidence grants
that role. PM formal gate packages MUST require source result contract
self-checks to be present, parseable, matching, and passed.

#### Scenario: PM releases a material formal gate package with bad source self-check

- **GIVEN** a source result envelope has missing or failed `contract_self_check`
- **WHEN** PM records an absorbed package disposition
- **THEN** FlowPilot blocks formal gate package release for source result repair
