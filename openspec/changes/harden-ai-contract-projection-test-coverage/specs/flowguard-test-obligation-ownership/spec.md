## ADDED Requirements

### Requirement: Test obligation ownership distinguishes validator, projection, and retry evidence
FlowPilot SHALL classify conditional contract test evidence by the exact behavior it proves: runtime validator rejection, AI-facing packet projection, or rejection-to-corrected-retry convergence.

#### Scenario: Validator-only evidence leaves projection obligation open
- **WHEN** a model obligation requires an AI-facing conditional field contract to be usable by the producing role
- **THEN** Model-Test Alignment MUST keep the projection obligation open unless a current test proves the field appears on packet-local AI-facing contract surfaces with exact field names, expected type, and finite options.

#### Scenario: Projection-only evidence leaves retry obligation open
- **WHEN** a packet-local contract projection test passes but no test submits a wrong package through runtime and observes a corrected retry
- **THEN** Model-Test Alignment MUST keep the rejection-to-corrected-retry obligation open.

#### Scenario: ContractExhaustionMesh cases feed TestMesh child ownership
- **WHEN** ContractExhaustionMesh generates conditional contract projection or retry convergence cases
- **THEN** TestMesh MUST own those case ids or shard ids with current child-suite evidence before parent coverage can be called complete.
