## ADDED Requirements

### Requirement: Declared Finite Cartesian Boundary Matrix
The system SHALL declare a finite FlowPilot control-plane matrix over boundary
materials, mutation kinds, handoff contexts, downstream consumers, and recovery
expectations.

#### Scenario: Full product is generated
- **WHEN** the Cartesian exhaustion runner executes
- **THEN** it MUST report the full declared product count, applicable cell count, skipped cell count, and every skipped cell reason

#### Scenario: No silent filtering
- **WHEN** a boundary/mutation/context/consumer combination is not applicable
- **THEN** the matrix MUST record the combination with a non-empty skip reason instead of dropping it silently

### Requirement: Applicable Cells Have Repair Oracles
The system SHALL attach a current-contract repair oracle to every applicable
Cartesian cell.

#### Scenario: Repairable material defect
- **WHEN** an applicable cell represents a missing body, missing field, wrong field type, stale identity, wrong path, missing evidence, unauthorized read, duplicate packet, or unsupported command
- **THEN** the cell MUST name the current subject, mechanical owner, expected reaction, required repair command, and evidence owner

#### Scenario: Unsupported compatibility surface
- **WHEN** an applicable cell represents a legacy alias, wrapper, fallback prose, unsupported command, or old-router shape
- **THEN** the expected reaction MUST reject the current packet/result and MUST NOT translate the unsupported shape into a valid current result

### Requirement: Normal Repair Does Not Pass Through GlassBreak
The system SHALL treat GlassBreak as a threshold-probe liveness alarm, not a
successful normal repair path.

#### Scenario: Ordinary repair drill
- **WHEN** a generated cell belongs to a normal intake, dispatch, review, repair, reissue, route mutation, or terminal-closure context
- **THEN** the cell MUST NOT expect GlassBreak as the successful recovery reaction

#### Scenario: Repeat threshold probe
- **WHEN** a generated cell explicitly models repeated same-blocker delivery at the GlassBreak threshold
- **THEN** the cell MUST expect a GlassBreak threshold alarm and MUST still record the repeated blocker key and current subject

### Requirement: Downstream Consumers Are Proved
The system SHALL prove that every applicable Cartesian cell is consumed by a
registered downstream evidence owner and test command.

#### Scenario: Evidence owner registration
- **WHEN** the runner groups applicable cells by required evidence owner
- **THEN** every generated owner MUST be registered in the TestMesh child-suite summary

#### Scenario: Model-Test Alignment registration
- **WHEN** Model-Test Alignment is evaluated
- **THEN** it MUST include model, runner, and replay evidence for the Cartesian exhaustion matrix

#### Scenario: Synthetic coverage registration
- **WHEN** synthetic-agent coverage rows are generated
- **THEN** they MUST include Cartesian obligations for runtime, reviewer, PM, FlowGuard, TestMesh, ModelMesh, and GlassBreak threshold consumers

### Requirement: Historical And Contract Exhaustion Inputs Are Consumed
The system SHALL consume existing contract-exhaustion and historical material
families as inputs to the Cartesian layer rather than replacing them.

#### Scenario: Contract exhaustion bridge
- **WHEN** the Cartesian model builds its boundary inventory
- **THEN** it MUST include bridge cells proving that existing contract-exhaustion required cells are owned by a Cartesian consumer path

#### Scenario: Historical failure bridge
- **WHEN** historical failure rows describe missing body, missing path, stale evidence, no-delta retry, or GlassBreak miss classes
- **THEN** the Cartesian matrix MUST include matching mutation families or fail with a missing-family finding
