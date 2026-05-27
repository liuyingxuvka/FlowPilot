# runtime-owner-contract-coverage Specification

## Purpose
TBD - created by archiving change add-runtime-owner-contracts-and-safe-splits. Update Purpose after archive.
## Requirements
### Requirement: Runtime Owner Module External Contracts

FlowPilot SHALL treat a runtime owner module as externally contract-covered only when the model-test alignment source-contract plan contains a code contract for that module path and ordinary test evidence that directly calls the symbol.

#### Scenario: owner module contract is directly tested

- **WHEN** a selected runtime owner module exposes an owner-boundary function
- **THEN** the source-contract alignment plan SHALL include a `CodeContract` for the module path and symbol
- **AND** at least one ordinary test evidence row SHALL call that symbol
- **AND** the test SHALL assert an externally visible output, schema, path, state, or error contract

#### Scenario: mention-only evidence stays incomplete

- **WHEN** a test file only imports or mentions a module without calling the contract symbol
- **THEN** the diagnostic SHALL NOT treat that as full external-contract coverage for the runtime owner module

### Requirement: Residual Gap Honesty

FlowPilot SHALL keep residual runtime owner gaps visible until each module has direct source-level contract evidence.

#### Scenario: remaining module lacks direct contract evidence

- **WHEN** a runtime owner module has model binding and test mentions but no source-level external contract
- **THEN** the full diagnostic SHALL report `internal_only_test`
- **AND** the repair type SHALL remain `upgrade_to_external_contract_test`
