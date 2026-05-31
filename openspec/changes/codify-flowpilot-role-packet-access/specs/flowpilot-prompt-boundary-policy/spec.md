## MODIFIED Requirements

### Requirement: Runtime Card Return Authority

FlowPilot runtime cards SHALL describe the current return path for ACKs, packet opening, work-packet results, and formal role outputs without asking roles to wait for ad hoc Controller permission or obsolete Controller relay signatures.

#### Scenario: Role receives current work authority

- **WHEN** a role card, phase card, event card, or packet identity prompt describes current work-packet authority
- **THEN** it MUST name the generated handoff plus `flowpilot_new.py lease-agent`, `flowpilot_new.py ack`, `flowpilot_new.py open-packet`, and `flowpilot_new.py submit-result` as the current work-packet path
- **AND** it MUST NOT tell the role that `controller_relay`, chat-only permission, or ACK body exposure is required before current work can proceed.
