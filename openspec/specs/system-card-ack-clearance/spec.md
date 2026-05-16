# system-card-ack-clearance Specification

## Purpose
TBD - created by archiving change enforce-gate-scoped-card-ack-clearance. Update Purpose after archive.
## Requirements
### Requirement: System Card ACKs Clear Scoped Read Obligations
The system SHALL treat system-card ACKs as mechanical read receipts scoped to a route gate, node, bundle, or work-packet preflight, and SHALL NOT treat a Controller delivery receipt as target-role work completion.

#### Scenario: Controller delivery closes only Controller work
- **WHEN** Controller relays a system-card envelope or formal work-packet envelope
- **THEN** Router records only the Controller-owned delivery step as done and keeps the target-role wait open until the target role returns the required ACK, report, or result event

#### Scenario: ACK does not complete semantic work
- **WHEN** a role submits a valid system-card ACK
- **THEN** Router may clear the scoped read obligation but MUST keep any PM, reviewer, officer, or worker semantic decision/result gate open until its own report or result event arrives

### Requirement: Gate And Node Movement Requires ACK Clearance
Before entering or leaving a route gate or node boundary, the system SHALL check pending required system-card ACKs for that boundary and SHALL NOT move the route boundary while any required ACK for that scope is unresolved.

#### Scenario: Missing ACK blocks gate transition
- **WHEN** Router is about to move across a gate or node boundary and a required system-card pending return for that scope is unresolved
- **THEN** Router keeps the route at the current boundary and exposes an ACK wait/reminder action instead of advancing or creating a PM repair blocker

#### Scenario: Cleared ACK allows boundary movement
- **WHEN** all required system-card ACKs for the current boundary have valid runtime read receipts and direct Router ACK envelopes
- **THEN** Router may continue evaluating the next legal gate or node action

### Requirement: Formal Work Packet Relay Requires Target ACK Preflight
Before relaying a formal work packet to a role, the system SHALL check that the target role has cleared required system-card ACKs for the current scope.

#### Scenario: Work packet waits for target-role ACK
- **WHEN** Router is about to relay a formal work packet to a role and that role has an unresolved required system-card ACK in the current scope
- **THEN** Router returns an ACK wait/reminder action for that role and MUST NOT relay the work packet yet

#### Scenario: Work packet proceeds after ACK
- **WHEN** the target role's required system-card ACKs for the current scope are valid and resolved
- **THEN** Router may relay the formal work packet without requiring extra screenshot or heavyweight proof

### Requirement: Missing ACK Uses Original-Card Reminder
When a required system-card ACK is missing and the original committed card or bundle artifact is intact, the system SHALL remind the target role to ACK the original card or bundle and SHALL NOT duplicate the system card as the normal recovery path.

#### Scenario: Reminder references original envelope
- **WHEN** a required ACK is missing but the original card or bundle envelope, expected read receipt path, and expected ACK path are recorded
- **THEN** Router's wait action identifies the original envelope and expected ACK path and tells Controller/role to complete the original runtime ACK loop

#### Scenario: Duplicate delivery is not normal recovery
- **WHEN** a required ACK is merely missing
- **THEN** Router MUST NOT issue a second copy of the same system card unless the original committed artifact is invalid, lost, stale, or tied to a replaced role identity
