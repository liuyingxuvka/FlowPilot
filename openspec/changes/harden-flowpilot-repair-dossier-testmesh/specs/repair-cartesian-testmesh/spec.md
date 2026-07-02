## ADDED Requirements

### Requirement: Repair validation uses a Cartesian TestMesh
FlowPilot SHALL validate repair dossier behavior through a generated
Cartesian TestMesh whose parent gate consumes child-suite evidence.

#### Scenario: Required dimensions are generated
- **WHEN** the repair TestMesh generates required coverage cells
- **THEN** it MUST include role, packet family, blocker class, repair depth,
  subject family, lifecycle stage, authorization state, evidence state, subject
  completion-claim state, and recovery state dimensions.

#### Scenario: Parent gate consumes child evidence
- **WHEN** the parent repair TestMesh reports confidence
- **THEN** every required coverage cell MUST be owned by a child suite with
  current passing evidence.

#### Scenario: Hidden non-evidence cannot pass parent gate
- **WHEN** a child suite is skipped, stale, running, timed out, failed, or only
  has progress output
- **THEN** the parent repair TestMesh MUST NOT count that child as passing.

### Requirement: Observed repair-loop replay is required
FlowPilot SHALL keep an observed-run replay case for the repair loop pattern
where repair nodes continue without normal recovery.

#### Scenario: June repair-loop pattern is replayed
- **WHEN** the observed-loop replay fixture runs
- **THEN** it MUST cover repeated worker material blockers, repeated reviewer
  plan-as-evidence blockers, repeated PM `repair_current_scope` decisions, and
  superseded blockers in the same repair lineage.

#### Scenario: Replay reaches glass-break at fifth repair node
- **WHEN** the observed-loop replay enters five consecutive same-parent repair
  nodes without a normal business-node recovery
- **THEN** Runtime MUST expose Controller break-glass and MUST NOT issue the
  sixth ordinary repair node.

### Requirement: Same-class blocker and package families are covered
FlowPilot SHALL cover every supported blocker class and every repair-relevant
packet family in the repair TestMesh.

#### Scenario: Blocker classes are mapped to cells
- **WHEN** the repair TestMesh enumerates blocker coverage
- **THEN** it MUST include every supported blocker class from the stage
  evidence matrix, including missing required information, missing matching
  FlowGuard report, evidence gap, FlowGuard failure, local artifact, and route
  decomposition.

#### Scenario: Packet families are mapped to cells
- **WHEN** the repair TestMesh enumerates packet-family coverage
- **THEN** it MUST include PM repair decision, PM node acceptance plan, worker
  node task, FlowGuard post-result check, PM FlowGuard acceptance, reviewer
  current-subject review, same-packet reissue, control-plane blocker, and
  Controller break-glass surfaces.
