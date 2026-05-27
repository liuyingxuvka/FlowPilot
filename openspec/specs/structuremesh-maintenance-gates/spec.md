# structuremesh-maintenance-gates Specification

## Purpose
TBD - created by archiving change structuremesh-router-model-cleanup. Update Purpose after archive.
## Requirements
### Requirement: StructureMesh gates large script splits

Large FlowPilot maintenance splits SHALL create executable FlowGuard
StructureMesh evidence before claiming routine or release-level structural
confidence.

#### Scenario: Planned split has clear ownership

- **WHEN** a large script or module split is planned
- **THEN** the StructureMesh SHALL inventory parent partitions, child modules,
  public entrypoints, state ownership, side effects, config ownership,
  dependency edges, facade retention, and parity evidence.

#### Scenario: Duplicate ownership blocks confidence

- **WHEN** two child modules own the same state, side effect, config item, or
  parent partition without an explicit shared-kernel allowance
- **THEN** the StructureMesh SHALL reject a green routine or release decision.

#### Scenario: Release scope requires current parity

- **WHEN** the maintenance pass claims completion for a moved release-required
  module or public entrypoint
- **THEN** the StructureMesh SHALL require current parity evidence at the
  configured evidence tier.

### Requirement: Router facade preserves public compatibility

Router structural maintenance SHALL keep public compatibility through the
existing router facade unless a separate explicit behavior change is approved.

#### Scenario: Public router entrypoint remains available

- **WHEN** router implementation bodies are moved into child modules
- **THEN** existing public imports, CLI commands, command names, event names,
  persisted JSON shapes, and result keys SHALL remain available through the
  facade.

#### Scenario: Root state remains coordinated by facade

- **WHEN** child modules own focused router record families
- **THEN** the router facade SHALL remain the owner of root run-state
  coordination and final persistence boundaries.

### Requirement: TestMesh gates slow validation evidence

Large router runtime validation SHALL use FlowGuard TestMesh evidence so child
suite ownership, stale evidence, timeouts, skipped tests, and background
artifacts remain visible.

#### Scenario: Background suite has final artifacts

- **WHEN** a long router suite is reported as passed
- **THEN** its TestMesh evidence SHALL include final result status, exit code,
  duration, command, log root, and final artifact presence.

#### Scenario: Progress output is insufficient

- **WHEN** a background suite has progress output but no final exit/result
  artifact
- **THEN** the TestMesh SHALL treat that suite as incomplete rather than
  passed.

#### Scenario: Parent router tier is composition only

- **WHEN** the router tier is used for validation
- **THEN** it SHALL be composed from registered child suites with explicit
  ownership
- **AND** it SHALL NOT hide one large aggregate command behind the parent gate.

### Requirement: Model-Test Alignment gates coverage claims

FlowPilot validation SHALL use FlowGuard Model-Test Alignment evidence before
claiming that model coverage and ordinary tests agree.

#### Scenario: Model obligation has required test evidence

- **WHEN** a required FlowGuard model obligation is used in a validation claim
- **THEN** the alignment review SHALL bind it to current passing ordinary test
  evidence for each required test kind or report a missing evidence finding.

#### Scenario: Ordinary test overclaims model confidence

- **WHEN** a test report claims broader model confidence than its declared
  obligation bindings prove
- **THEN** the alignment review SHALL flag the overclaim before completion.
