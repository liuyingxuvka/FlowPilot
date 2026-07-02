## ADDED Requirements

### Requirement: Runtime owns active repair dossiers
FlowPilot SHALL maintain one runtime-owned active repair dossier for each
current repair lineage that is repairing a substantive blocker.

#### Scenario: Dossier is created from first substantive blocker
- **WHEN** a substantive blocker opens a repair path
- **THEN** Runtime MUST create a repair dossier that records the blocker id,
  blocked packet id, blocked result id, base node id, parent node id, repair
  depth, unresolved obligations, and normal-recovery status.

#### Scenario: Dossier is updated across repair packets
- **WHEN** Runtime issues PM repair decisions, repair packets, FlowGuard
  checks, reviewer rechecks, or route mutations for the same repair lineage
- **THEN** Runtime MUST update the same repair dossier instead of creating
  packet-family-local repair history.

#### Scenario: Dossier keeps superseded blockers visible
- **WHEN** a blocker is marked `superseded_by_route_mutation` while its repair
  lineage has not recovered to a normal business node
- **THEN** the blocker MUST remain in the active repair dossier blocker chain.

### Requirement: Repair packets receive role-scoped dossier context
FlowPilot SHALL authorize sealed result-body reads for repair packets from the
active repair dossier according to packet role and packet family.

#### Scenario: PM sees blocker lineage and repair depth
- **WHEN** Runtime issues a PM repair decision or PM repair planning packet
  inside a repair dossier
- **THEN** the packet MUST include authorized reads for the current blocker,
  blocked target result, prior same-dossier blocker reports, prior PM repair
  decisions, prior reviewer blocker reports, and the current repair depth.

#### Scenario: Worker sees blocker reason and required repair materials
- **WHEN** Runtime issues a worker repair packet inside a repair dossier
- **THEN** the packet MUST include authorized reads for the blocker report, PM
  repair decision, blocked target packet and result context, prior failed repair
  reports, and required material refs needed to produce fresh current evidence.

#### Scenario: Reviewer sees current subject and repair history
- **WHEN** Runtime issues a reviewer packet for a repaired subject inside a
  repair dossier
- **THEN** the packet MUST include authorized reads for the current subject
  result, required current evidence refs, matching FlowGuard result when
  required, prior reviewer blocker reports, and the repair dossier lineage.

#### Scenario: Normal packets remain minimally authorized
- **WHEN** Runtime issues a normal non-repair packet
- **THEN** Runtime MUST NOT authorize unrelated parent-scope sealed bodies
  merely because they share a parent node.

### Requirement: Historical repair bodies are context-only by default
FlowPilot SHALL classify inherited prior repair-chain bodies as context-only
unless they are explicitly the current packet's new evidence.

#### Scenario: PM plan cannot satisfy worker evidence
- **WHEN** a reviewer or FlowGuard check evaluates a repaired worker/result-stage
  subject, or a PM plan that claims already-produced worker evidence or repair
  closure evidence, but the only available body is a PM node-context plan
- **THEN** the check MUST reject the subject as missing current repair evidence.

#### Scenario: Dossier does not override PM plan stage
- **WHEN** a PM node-context plan is reviewed inside a repair dossier
- **AND** the review window says the subject lifecycle stage is
  `node_plan_definition`
- **AND** the PM result does not claim already-produced worker evidence or
  repair closure evidence
- **THEN** the repair dossier MUST remain historical context only
- **AND** Reviewer MUST apply the PM plan-stage requirements rather than worker
  result-stage evidence requirements.

#### Scenario: Old blocked result cannot close current obligation
- **WHEN** a role cites an old blocked result body as the repaired result
- **THEN** Runtime or Reviewer MUST reject that citation as context-only.

#### Scenario: Current evidence remains usable
- **WHEN** a worker submits a new current repair result and it is recorded as
  current evidence for the dossier obligation
- **THEN** Reviewer and FlowGuard MAY use that result as the current subject.
