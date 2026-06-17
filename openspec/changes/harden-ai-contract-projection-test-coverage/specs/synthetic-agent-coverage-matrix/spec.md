## ADDED Requirements

### Requirement: AI-facing conditional contract projection is a covered branch family
FlowPilot SHALL treat AI-facing projection of conditional packet-result contracts as a first-class synthetic coverage branch family, separate from runtime validator coverage.

#### Scenario: Conditional field projection has coverage ownership
- **WHEN** a current packet family can require conditional result fields such as `semantic_recheck.*`
- **THEN** the synthetic coverage matrix MUST include rows proving the required field paths, allowed value options, minimal valid shape, and forbidden near-synonym fields are visible on AI-facing packet contract surfaces
- **AND** those rows MUST name an external-contract test owner rather than relying only on runtime validator tests.

#### Scenario: Runtime validator evidence cannot substitute for packet projection evidence
- **WHEN** runtime has a validator that rejects a missing or invalid conditional result field
- **THEN** the coverage matrix MUST still fail if no current test proves the corresponding AI-facing packet projection surface exposes the exact field name, expected value type, and finite allowed option when applicable.

#### Scenario: All finite packet-result options are expanded into coverage cells
- **WHEN** a current packet-result contract family declares an `allowed_value_options` field
- **THEN** ContractExhaustionMesh MUST include a runtime-owned row for missing AI-facing projection of that exact finite option field
- **AND** it MUST include a fake-AI-owned row for a wrong submitted value for that same field.

#### Scenario: Conditional result-contract profiles are expanded into coverage cells
- **WHEN** a result-contract profile adds required fields, field type requirements, finite allowed values, or forbidden aliases to a packet-result contract
- **THEN** ContractExhaustionMesh MUST include profile-owned rows for each added exact field or alias
- **AND** those rows MUST not be satisfied by a base contract family row that does not name the active profile.

#### Scenario: Fake-AI-owned cells are reachable by the mechanical responder
- **WHEN** ContractExhaustionMesh assigns a packet/result contract cell to fake-AI responder ownership
- **THEN** the contract-driven fake-AI responder MUST generate a matching `(contract_family_id, contract_path, mutation_kind)` cell from the AI-facing required report contract
- **AND** the coverage check MUST fail if the model requires a fake-AI-owned field, option, alias, type, branch, or retry cell that the responder cannot derive from packet-local `minimal_valid_shape`, `branch_valid_shapes`, `allowed_value_options`, `field_type_requirements`, or forbidden-alias projection.

#### Scenario: Every finite option value is materialized by the responder
- **WHEN** an AI-facing packet-result contract declares a finite `allowed_value_options` list for a field
- **THEN** the contract-driven fake-AI responder MUST generate a branch-valid payload for each declared option value of that field
- **AND** the coverage check MUST fail if any declared option value lacks a reachable minimal or branch-valid payload shape.

### Requirement: Rejection-to-corrected-retry convergence is a covered branch family
FlowPilot SHALL treat runtime rejection feedback and corrected fake-AI retries as a first-class synthetic coverage branch family.

#### Scenario: Bad package followed by corrected retry reaches legal continuation
- **WHEN** a prepared fake-AI package submits a conditional contract mistake and runtime reissues a current-contract packet
- **THEN** the coverage matrix MUST require a follow-up row where a corrected fake-AI package uses the reissue feedback and returns to the legal runtime path before GlassBreak.

#### Scenario: Partial retry remains blocked without overclaiming recovery
- **WHEN** the corrected fake-AI package fixes only part of the reported contract failure
- **THEN** the coverage matrix MUST require a negative row proving runtime keeps the packet blocked or reissued and does not count the partial retry as recovery evidence.
