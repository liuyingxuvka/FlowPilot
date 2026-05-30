# flowguard-model-hierarchy Specification

## Purpose
TBD - created by archiving change split-heavy-flowguard-model-hierarchy. Update Purpose after archive.
## Requirements
### Requirement: Heavy parent models are explicitly classified
The system SHALL classify FlowPilot FlowGuard models by role, observed size, evidence tier, and whether they require parent/child split review.

#### Scenario: Oversized parent detected
- **WHEN** a model result reports a state count above the configured heavyweight threshold
- **THEN** the hierarchy check MUST classify the model as a heavyweight parent that requires split review or current full-regression evidence

#### Scenario: Focused child retained
- **WHEN** a focused model is below the heavyweight threshold and owns a narrow risk boundary
- **THEN** the hierarchy check MUST classify it as child evidence rather than requiring further split for size alone

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
  unsupported historical for that split.

### Requirement: Child evidence freshness is visible
The system SHALL expose each child model's result path, freshness rule, evidence tier, skipped checks, and stale-result status before using child evidence for parent confidence.

#### Scenario: Stale child evidence is used
- **WHEN** a child model result is missing, stale, foreign to the current model source, or hides skipped required checks
- **THEN** the hierarchy check MUST report the child as insufficient evidence and avoid claiming parent coverage

#### Scenario: Current child evidence is usable
- **WHEN** a child model has current abstract, hazard, live, or conformance evidence matching its declared tier
- **THEN** the hierarchy check MAY count that child toward its assigned parent partition coverage

### Requirement: Heavy regressions remain distinct from hierarchy checks
The system SHALL distinguish lightweight hierarchy checks from full heavyweight `meta` and `capability` regressions.

#### Scenario: Hierarchy check passes but parent regression is not current
- **WHEN** the hierarchy check passes and a heavyweight parent does not have a current full-regression result or valid proof
- **THEN** the system MUST report that full heavyweight regression remains required for release-level confidence

#### Scenario: Background heavyweight run is incomplete
- **WHEN** a background meta or capability run has progress output but no final exit artifact and valid result/proof
- **THEN** the system MUST report the run as incomplete rather than passed

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

### Requirement: Hierarchy reports thin parent result type
The system SHALL expose whether each Meta and Capability parent result came
from thin evidence aggregation, full graph exploration, proof reuse, or
an incomplete background run.

#### Scenario: Thin parent result is current
- **WHEN** hierarchy inventory reads a current thin parent result
- **THEN** it MUST report the parent result type as thin and MUST NOT classify
  that result as a full regression

#### Scenario: Full parent result is current
- **WHEN** hierarchy inventory reads a current full parent result or
  valid full proof
- **THEN** it MUST report the full evidence path separately from the thin parent
  result

### Requirement: Hierarchy preserves full-regression obligations
The system SHALL preserve heavyweight parent full-regression obligations when
thin evidence is current but full Meta or Capability regression evidence is not
current.

#### Scenario: Thin evidence passes without full proof
- **WHEN** thin hierarchy evidence passes and full Meta or Capability proof is
  stale, missing, or incomplete
- **THEN** hierarchy inventory MUST report the parent as routine-current and
  release-confidence-incomplete

#### Scenario: Background run is still active
- **WHEN** a background Meta or Capability run has progress output but no final
  exit artifact and valid result or proof
- **THEN** hierarchy inventory MUST treat the background run as incomplete
  rather than release-current

### Requirement: Foreground validation uses hierarchy and thin parents
The system SHALL route fast install, smoke, and coverage-sweep validation
through hierarchy and thin parent checks while keeping full parent regressions
available as background or forced validation.

#### Scenario: Fast smoke validation runs
- **WHEN** smoke validation runs in fast mode
- **THEN** it MUST run thin parent and hierarchy checks in foreground and MUST
  only reuse or defer full parent regressions with visible proof or background
  obligations

#### Scenario: Install readiness is checked
- **WHEN** install readiness validation runs
- **THEN** it MUST verify thin parent artifacts, hierarchy artifacts, and any
  full-regression obligations without requiring foreground full Meta or
  Capability graph exploration

### Requirement: Full model confidence covers visible user branches

FlowGuard full-model confidence SHALL include every visible or
user-triggerable branch in the modeled branch inventory. This includes
buttons, displayed actions, status-return modes, wait-target duties, liveness
and recovery actions, and terminal/stop branches. A visible branch that is not
implemented and covered by current model evidence SHALL be hidden, disabled, or
explicitly marked out of scope; it MUST NOT appear as an enabled no-op.

#### Scenario: Visible branch is implemented and modeled

- **WHEN** FlowPilot exposes a visible control, status action, recovery action,
  or terminal/stop branch to the user or foreground Controller
- **THEN** the model hierarchy records the branch in the visible/user-triggered
  inventory
- **AND** current parent or child FlowGuard evidence covers the branch.

#### Scenario: Visible branch is not implemented

- **WHEN** a visible control or branch is not implemented or not covered by
  current model evidence
- **THEN** the branch is hidden, disabled, or explicitly unavailable with a
  recovery path
- **AND** full-model confidence is blocked until the implementation and model
  evidence exist.

#### Scenario: Visible branch evidence is stale

- **WHEN** the implementation, prompt surface, or runtime status branch changes
  after the last visible-branch model evidence was produced
- **THEN** full-model confidence is blocked until the relevant child or parent
  model is refreshed.

### Requirement: Persistent daemon parent evidence must be thin-child mesh evidence

The FlowPilot parent hierarchy SHALL NOT consume the full
`flowpilot_persistent_router_daemon` result as direct thin-child evidence.

#### Scenario: Router daemon resume partition consumes split children

- **GIVEN** the `router_daemon_resume` parent partition is evaluated
- **WHEN** the parent reads child evidence ids from the responsibility ledger
- **THEN** it consumes focused daemon child evidence for startup/lock,
  Controller actions, wait/liveness, and terminal/projection contracts
- **AND** each focused child result is below the thin-child state threshold
- **AND** the unsupported historical persistent daemon model may still run outside the
  parent thin-child evidence set.
