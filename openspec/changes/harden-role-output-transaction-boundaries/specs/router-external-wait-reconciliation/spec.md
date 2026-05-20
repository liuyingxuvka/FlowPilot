## ADDED Requirements

### Requirement: External wait reconciliation enforces role-output contract mode
FlowPilot SHALL reconcile external waits against the expected role-output contract mode before accepting a Router event as satisfying the wait.

#### Scenario: Wait expects role-output runtime envelope
- **WHEN** the active wait expects a registry-backed role-output runtime envelope
- **THEN** Router MUST require a valid runtime envelope and receipt for the expected output contract
- **AND** Router MUST reject or quarantine a plain manual event envelope for the same event

#### Scenario: Wait closes only after transaction completion
- **WHEN** a PM package disposition event is accepted by Router
- **THEN** the external wait MUST remain open until the registered control transaction reaches a complete or quarantined outcome
