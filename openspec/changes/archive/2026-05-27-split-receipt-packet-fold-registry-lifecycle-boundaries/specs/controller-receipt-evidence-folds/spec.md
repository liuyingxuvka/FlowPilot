## MODIFIED Requirements

### Requirement: Evidence-backed Controller receipts fold through registered handlers
FlowPilot SHALL keep receipt-fold registration, evidence validation, and
lifecycle writeback explicit and separately testable.

#### Scenario: Packet-fold registry is internally split without changing actions
- **WHEN** FlowPilot lists registered Controller receipt evidence-fold actions
- **THEN** the packet-fold parent still exposes the same registry and action
  helper names
- **AND** the registry child MUST preserve the existing packet, result, and
  control-blocker action metadata without becoming a Router state authority

#### Scenario: Packet-fold lifecycle is internally split without changing writes
- **WHEN** FlowPilot applies packet/result lifecycle writeback after receipt
  evidence is satisfied
- **THEN** the lifecycle child MUST select only the declared packet or
  recipient-specific result lifecycle states
- **AND** the lifecycle child MUST update only the batch and PM role-work
  lifecycle records already owned by the receipt-fold contract
- **AND** packet and result evidence validation MUST remain separate from
  lifecycle writeback
