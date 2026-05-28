## ADDED Requirements

### Requirement: Runtime owner diagnostic gaps require external contract evidence
FlowPilot SHALL treat a runtime-owner module reported by the full
model-test-code diagnostic as externally relevant only when the
model-test-alignment source-contract plan contains a `CodeContract` for that
module path and ordinary test evidence that directly calls the claimed symbol.

#### Scenario: Controller wait audit is externally contract-covered
- **WHEN** the full model-test-code diagnostic inspects
  `skills/flowpilot/assets/flowpilot_router_controller_wait_audit.py`
- **THEN** the diagnostic finds a source-level `CodeContract` and ordinary
  external-contract test evidence for the public wait-audit symbol
- **AND** the module is not reported as `internal_only_test`

#### Scenario: Runtime gateway is externally contract-covered
- **WHEN** the full model-test-code diagnostic inspects
  `skills/flowpilot/assets/flowpilot_runtime_gateway.py`
- **THEN** the diagnostic finds a source-level `CodeContract` and ordinary
  external-contract test evidence for the public gateway enforcement symbol
- **AND** the module is not reported as `internal_only_test`
