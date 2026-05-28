## ADDED Requirements

### Requirement: Known friction confidence consumes packet-result family parity
FlowPilot known-friction and final-confidence gates SHALL consume the
FlowGuard packet-result obligation-family parity decision before treating the
durable-result reconciliation class as closed.

#### Scenario: Family parity is current and complete
- **WHEN** the packet-result obligation-family decision is current, passing, and backed by external runtime evidence
- **THEN** known-friction confidence MAY treat the packet-result reconciliation class as closed for the bounded claim.

#### Scenario: Family parity is missing, stale, or scoped
- **WHEN** the packet-result obligation-family decision is missing, stale, scoped, or blocked
- **THEN** known-friction confidence MUST block or downgrade the durable-result reconciliation claim
- **AND** final confidence MUST NOT silently accept old defect-family rows as complete.
