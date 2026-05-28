## ADDED Requirements

### Requirement: Critical runtime writes require FlowGuard gateway adoption
FlowPilot SHALL require every feasible production path that can write critical
runtime state to pass through an approved runtime gateway and SHALL validate
that adoption with FlowGuard.

#### Scenario: Complete writer inventory is required
- **WHEN** FlowPilot claims runtime-gateway adoption
- **THEN** the claim MUST include current evidence that production writer paths
  under `skills/flowpilot/assets` were inventoried
- **AND** the inventory MUST fail if a critical direct write is outside an
  approved gateway module with an assertion guard.

#### Scenario: Gateway ownership is enforced at runtime
- **WHEN** a writer attempts to mutate a known critical runtime state surface
- **THEN** `assert_runtime_gateway_write` MUST verify that the gateway owns
  that surface before the file write or append is performed
- **AND** a wrong gateway MUST raise a runtime gateway error instead of writing.

#### Scenario: All declared critical surfaces have FlowGuard evidence
- **WHEN** the runtime-gateway adoption check is run
- **THEN** every declared critical state surface MUST have an owning gateway
- **AND** every owning gateway MUST declare atomic commit, replay observation,
  step contract, code boundary, and proof artifact requirements
- **AND** every critical surface MUST have a current gateway writer observation.

#### Scenario: Legacy bypass declarations remain blocking
- **WHEN** a writer observation declares a direct legacy bypass for a critical
  state surface
- **THEN** FlowGuard MUST report a blocking finding
- **AND** completion MUST NOT treat the bypass as accepted runtime adoption.
