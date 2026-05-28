## ADDED Requirements

### Requirement: Packet result families reconcile durable envelopes before waiting
Router durable wait reconciliation SHALL fold complete durable result-envelope
evidence into the existing result-return event for every supported
packet-result family before selecting a next action or materializing a wait
reminder.

#### Scenario: Full packet-result family joins from durable envelopes
- **WHEN** all blocking result envelopes exist for an active `material_scan`, `research`, `current_node`, or `pm_role_work` packet batch
- **AND** the family-specific relay and prerequisite flags are satisfied
- **THEN** Router records the existing family result-return event from envelope metadata
- **AND** the next action MAY use the existing result relay path to the project manager.

#### Scenario: Mixed manual and durable member results
- **WHEN** one batch member has already produced a manual result-return event
- **AND** another member's durable result envelope exists before the next Router tick
- **THEN** Router folds the durable member evidence into the same batch state
- **AND** Router MUST NOT keep waiting for or reminding that completed member.

#### Scenario: Wrong recipient does not satisfy family reconciliation
- **WHEN** a result envelope exists for a packet-result family member
- **AND** the envelope is not addressed to the expected next recipient
- **THEN** Router MUST NOT record the family result-return event from that envelope
- **AND** the wait remains open or routes repair according to the existing wait contract.

### Requirement: Packet result family reconciliation preserves sealed bodies
Router packet-result family reconciliation SHALL use only packet ids, request
ids, batch ids, result envelope paths, result envelope hashes, target roles,
next-recipient metadata, and durable batch status.

#### Scenario: Durable result body exists beside envelope
- **WHEN** a sealed result body exists beside a valid result envelope
- **THEN** Router reconciles family completion without reading or summarizing the result body
- **AND** body access remains deferred to the addressed role or project manager relay path.
