## ADDED Requirements

### Requirement: Runtime-known formal artifacts are registry-owned
FlowPilot SHALL maintain a current-contract registry of AI-submitted,
file-backed formal artifacts that runtime can require alongside a result body.

#### Scenario: Registry includes required FlowGuard formal evidence
- **WHEN** FlowPilot issues a formal FlowGuard packet that requires packet-owned
  evidence
- **THEN** the registry MUST include `flowguard_evidence.json` with its
  packet-owned root field and required internal decision field.

#### Scenario: Registry excludes internal runtime persistence
- **WHEN** FlowPilot writes ledgers, packet envelopes, route snapshots, indexes,
  or other runtime-owned persistence files
- **THEN** those files MUST NOT be treated as AI-submitted formal artifacts in
  the registry.

#### Scenario: Registry excludes logical subject artifact ids
- **WHEN** FlowPilot requires logical subject artifact ids such as
  `subject_packet:<id>` or `target_result:<id>`
- **THEN** those ids MUST remain result-body consumption requirements and MUST
  NOT be treated as file-backed formal artifacts.

### Requirement: Registry coverage fails closed
FlowPilot SHALL fail coverage checks when a registered formal artifact lacks
fake-AI cells, contract-exhaustion cells, or runtime feedback expectations.

#### Scenario: New artifact without fake-AI cells fails
- **WHEN** a new file-backed formal artifact is added to the registry
- **AND** the synthetic fake-AI matrix has no lifecycle cells for it
- **THEN** the coverage check MUST fail instead of silently passing.

#### Scenario: New artifact without contract-exhaustion cells fails
- **WHEN** a new file-backed formal artifact is added to the registry
- **AND** ContractExhaustionMesh has no required cells for it
- **THEN** the coverage check MUST fail instead of silently passing.
