## ADDED Requirements

### Requirement: Router Owner External Contracts

FlowPilot SHALL treat a selected router owner module as externally contract-covered only when FlowGuard source-contract evidence and ordinary tests both prove the module's observable boundary.

#### Scenario: selected router owner module has direct contract evidence

- **WHEN** a router owner module is selected for contract coverage in this pass
- **THEN** the FlowGuard source-contract plan SHALL include a `CodeContract` for the module path and symbol
- **AND** ordinary test evidence SHALL directly call the symbol
- **AND** the test SHALL assert an externally visible result, persisted record, path/schema shape, state mutation, or explicit error contract

#### Scenario: broad facade coverage does not replace owner coverage

- **WHEN** a facade or aggregate test covers the same runtime family but does not call the selected owner symbol
- **THEN** the selected owner module SHALL remain incomplete for source-level external-contract coverage

### Requirement: Residual Diagnostic Honesty

FlowPilot SHALL keep remaining diagnostic gaps visible after each owner-contract batch.

#### Scenario: a router owner module remains untested or oversized

- **WHEN** the full model-code-test diagnostic runs after this pass
- **THEN** remaining `missing_test`, `needs_structure_split`, and `stale_evidence` findings SHALL stay in the JSON result
- **AND** local-only release evidence SHALL NOT be promoted to public release proof
