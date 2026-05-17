## MODIFIED Requirements

### Requirement: Parent partitions have explicit ownership

The system SHALL define a parent partition map for heavyweight FlowPilot
parents, assigning each parent-space item to a child model, the parent, a
read-only dependency, or a shared kernel. Large script/module split evidence
SHALL also expose StructureMesh ownership when source structure, public
entrypoints, state, side effects, or config ownership are moved.

#### Scenario: Coverage gap blocks hierarchy green

- **WHEN** a parent-space item has no owner and no explicit out-of-scope reason
- **THEN** the hierarchy check MUST reject a green hierarchy decision

#### Scenario: Unsafe sibling overlap blocks hierarchy green

- **WHEN** two sibling child models both own the same state write, side effect,
  or core functional area without a shared-kernel boundary
- **THEN** the hierarchy check MUST reject a green hierarchy decision

#### Scenario: StructureMesh ownership is required for source splits

- **WHEN** a heavyweight parent or router-related source module is split into
  new child modules
- **THEN** hierarchy or companion maintenance evidence MUST identify the
  StructureMesh result that proves child ownership and public-entrypoint
  compatibility for that split.

### Requirement: Validation surfaces include hierarchy evidence

The system SHALL include the model hierarchy runner and relevant
StructureMesh/TestMesh maintenance evidence in local validation surfaces
without forcing foreground rebuild of the two heavyweight parent graphs.

#### Scenario: Install check validates hierarchy artifacts

- **WHEN** `scripts/check_install.py` validates repository readiness
- **THEN** it MUST verify the hierarchy model, runner, result artifact, and
  documentation or OpenSpec artifacts exist

#### Scenario: Smoke check uses fast hierarchy foreground evidence

- **WHEN** smoke validation runs with fast mode
- **THEN** it MUST run the lightweight hierarchy check in foreground and use
  proof reuse for slow parent checks when valid

#### Scenario: Maintenance evidence is present

- **WHEN** a maintenance pass changes StructureMesh, TestMesh, or split model
  boundaries
- **THEN** local validation surfaces MUST verify the matching model/check
  scripts and result artifacts exist before install readiness is claimed.

#### Scenario: Parent confidence references alignment evidence

- **WHEN** a parent Meta or Capability check is used as release-level evidence
- **THEN** its supporting evidence MUST include either current Model-Test
  Alignment evidence for ordinary tests or an explicit statement that the
  parent result is abstract/model-hierarchy evidence rather than ordinary test
  coverage.
