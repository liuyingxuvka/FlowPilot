## ADDED Requirements

### Requirement: Native FlowGuard Cartesian Evidence Is Consumed
The system SHALL derive FlowGuard-native Cartesian combination cases, coverage
shards, and a model coverage receipt from the existing FlowPilot Cartesian
control-plane axes.

#### Scenario: Native combination cases exist
- **WHEN** the Cartesian runner evaluates the model
- **THEN** it MUST report a passing FlowGuard contract-exhaustion decision with one generated combination case for every declared full-product cell

#### Scenario: Coverage shards are owned
- **WHEN** TestMesh reviews the Cartesian evidence
- **THEN** every required native or FlowPilot-owned coverage shard id MUST be owned by a current passing child suite

#### Scenario: Coverage receipt exists
- **WHEN** the native FlowGuard report is produced
- **THEN** it MUST include a current model coverage receipt covering the generated combination cases and required shard ids

### Requirement: Source Mutation Bridges Are Exact
The system SHALL preserve mutation identity from upstream contract-exhaustion
and historical failure sources into the Cartesian layer.

#### Scenario: Known source mutation
- **WHEN** an upstream source row names a mutation kind that exists in the Cartesian mutation alphabet
- **THEN** the bridge row MUST keep the same mutation kind

#### Scenario: Unknown source mutation
- **WHEN** an upstream source row names a mutation kind absent from the Cartesian mutation alphabet
- **THEN** the runner MUST report the mutation as a missing family and MUST NOT map it to another known mutation

### Requirement: Synthetic Coverage Carries Shard Receipts
The system SHALL expose Cartesian shard and receipt identifiers in synthetic
coverage rows that claim Cartesian obligations.

#### Scenario: Cartesian coverage row
- **WHEN** synthetic-agent coverage rows are generated for a Cartesian cell
- **THEN** the row MUST include the cell's combination case id, coverage shard id, and coverage receipt id
