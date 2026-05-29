# maintenance-registry-consolidation Specification

## Purpose
TBD - created by archiving change consolidate-flowpilot-maintenance-registries. Update Purpose after archive.
## Requirements
### Requirement: Maintenance surfaces are declared once

FlowPilot SHALL provide a canonical maintenance surface registry for files and public surfaces that participate in install checks, diagnostics, model-test alignment, or maintenance maps.

#### Scenario: Registry records a runtime owner surface

- **GIVEN** a runtime owner module participates in FlowPilot maintenance diagnostics
- **WHEN** the maintenance surface registry is read
- **THEN** the registry includes the module path, kind, owner identity, compatibility role, and expected evidence family.

#### Scenario: Derived inventories preserve current coverage

- **GIVEN** existing diagnostic inventories and install-required file lists
- **WHEN** derived inventories are generated from the maintenance surface registry
- **THEN** they include every previously required surface
- **AND** they do not silently drop deferred structure split findings.

### Requirement: Compatibility views are generated from canonical registries

FlowPilot SHALL keep existing public protocol tables available while deriving them from canonical registries where duplication has been removed.

#### Scenario: Gate outcome exports keep current values

- **GIVEN** gate outcome facts are represented in a canonical gate registry
- **WHEN** legacy gate outcome tables are imported
- **THEN** `GATE_OUTCOME_BLOCK_EVENT_SPECS`, `GATE_OUTCOME_BLOCK_EVENTS`, `GATE_OUTCOME_PASS_CLEAR_FLAGS`, reset flag tuples, and `GATE_OUTCOME_PASS_CLEARS_EVENTS` expose the same values as before the registry conversion.

#### Scenario: External event exports keep current values

- **GIVEN** external event facts are represented in a canonical event registry
- **WHEN** legacy external event shard modules and `EXTERNAL_EVENTS` are imported
- **THEN** startup, material, route, terminal, and merged event mappings expose the same event names, flags, legacy markers, and descriptions as before the registry conversion.

### Requirement: Contract identity has one primary source

FlowPilot SHALL treat the runtime kit contract index as the primary source for output contract identity and task-family selection where those facts are already present in the contract index.

#### Scenario: Process binding derives contract identity

- **GIVEN** a process binding refers to an output contract listed in `runtime_kit/contracts/contract_index.json`
- **WHEN** the process binding table is loaded
- **THEN** contract identity and task-family facts are derived from the contract index where possible
- **AND** Python-only policy fields remain explicit.

### Requirement: Manifest-driven tests avoid repeated path lists

FlowPilot tests SHALL read runtime kit manifests for class-wide card and prompt coverage checks instead of maintaining duplicate path lists.

#### Scenario: Card class coverage follows manifest entries

- **GIVEN** a test validates a rule for all cards of a manifest kind or audience
- **WHEN** a new matching card is added to the runtime kit manifest
- **THEN** the test includes that card without requiring a second hand-written path list.

### Requirement: Hard control-plane boundaries remain unchanged

Registry consolidation SHALL NOT weaken runtime safety boundaries.

#### Scenario: Controller patrol remains mandatory

- **WHEN** registry consolidation changes protocol tables or maintenance inventories
- **THEN** Controller foreground standby, patrol timer, and final-answer preflight behavior remain enforced.

#### Scenario: Role information isolation remains mandatory

- **WHEN** contract or event registries are consolidated
- **THEN** workers, reviewers, PM, and Controller retain their existing body visibility, packet envelope, and allowed-event boundaries.

#### Scenario: Break-glass remains independent

- **WHEN** shared IO helpers are introduced or adjusted
- **THEN** break-glass evidence writing remains independent from the ordinary router repair loop.
