## MODIFIED Requirements

### Requirement: Runtime Card Return Authority

FlowPilot runtime cards SHALL describe the current return path for ACKs,
work-packet results, and formal role outputs without asking roles to wait for
obsolete Controller relay signatures.

#### Scenario: Role receives current work authority

- **WHEN** a role card, phase card, event card, or packet identity prompt
  describes current work-packet authority
- **THEN** it MUST name the current lease/ACK/result path as the work-packet
  authority path
- **AND** it MUST NOT tell the role that `controller_relay`, `open-packet`, or
  `run-packet` is required before current work can proceed.
