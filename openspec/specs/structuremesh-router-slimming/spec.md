# structuremesh-router-slimming Specification

## Purpose
TBD - created by archiving change adopt-structuremesh-target-split-and-slim-router. Update Purpose after archive.
## Requirements
### Requirement: StructureMesh uses a model-derived target structure
Large FlowPilot router split reviews SHALL include a FlowGuard-derived target code structure that names target modules, function blocks, state owners, config owners, public entrypoints, validation boundaries, and the retained facade.

#### Scenario: Target structure is present
- **WHEN** the router StructureMesh release check runs
- **THEN** it MUST include a non-empty `target_structure`
- **AND** the target structure MUST match the StructureMesh parent boundary and registered child owner modules.

#### Scenario: Target structure is missing
- **WHEN** a router StructureMesh plan omits the model-derived target structure
- **THEN** FlowGuard MUST block the split with a target-structure finding rather than accepting current ownership evidence alone.

### Requirement: TestMesh uses a target split derivation
FlowPilot parent test gates SHALL include a FlowGuard-derived target split derivation that covers all registered child suites and partition items before claiming release confidence.

#### Scenario: Parent test gate is release checked
- **WHEN** the router TestMesh release check runs
- **THEN** it MUST name every child suite in the target split derivation
- **AND** it MUST cover every parent partition item.

#### Scenario: Child-suite derivation is incomplete
- **WHEN** the target split derivation omits a registered suite or partition item
- **THEN** FlowGuard MUST block the parent test claim.

### Requirement: Router facade remains public compatibility owner
The FlowPilot router split SHALL keep `skills/flowpilot/assets/flowpilot_router.py` as the stable public import and CLI facade while moving owned implementation regions into child modules.

#### Scenario: Router import and CLI compatibility are checked
- **WHEN** release validation reviews the router split
- **THEN** the public import path and CLI command MUST remain compatibility-preserved through the facade
- **AND** behavior parity evidence MUST be current for release-required entrypoints.

### Requirement: Catalog extraction is behavior-preserving
Protocol/catalog declarations moved out of `flowpilot_router.py` SHALL retain the same values, lookup semantics, and payload-contract behavior through facade imports or wrappers.

#### Scenario: Declarative catalog owner is extracted
- **WHEN** protocol constants, schema tables, action catalogs, or payload-contract helpers are moved into a child module
- **THEN** existing router behavior tests MUST pass without callers changing public router imports.

### Requirement: Release completion includes install and background evidence
FlowPilot maintenance SHALL not be published remotely until focused checks, relevant background FlowGuard regressions, local install synchronization, and public-release checks have final pass evidence. For this change, remote publication is deferred after local readiness is established.

#### Scenario: Background regression is reported complete
- **WHEN** a Meta, Capability, router, or release background check is cited as complete
- **THEN** its final exit artifact and metadata MUST exist under the configured background log root
- **AND** the exit status MUST show success.

#### Scenario: Local install is synchronized
- **WHEN** repository maintenance source changes are complete
- **THEN** the installed local FlowPilot skill MUST be synchronized from the repository
- **AND** the freshness audit MUST pass before local release-readiness is claimed.
