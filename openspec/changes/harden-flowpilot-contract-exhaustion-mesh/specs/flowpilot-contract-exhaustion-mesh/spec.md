## ADDED Requirements

### Requirement: Contract families generate finite negative matrix cells
FlowPilot SHALL derive a finite contract-exhaustion matrix from current packet,
result, FlowGuard evidence, reviewer, blocker, repair, and loop contract
families rather than relying only on manually selected scenarios.

#### Scenario: Current contract family has generated cells
- **WHEN** the contract-exhaustion matrix is generated
- **THEN** each registered current control-plane contract family MUST have a
  minimal valid baseline cell and generated negative cells for applicable
  missing-body, missing-field, wrong-type, wrong-target, missing-authorized-read,
  missing-evidence, evidence-path-mismatch, empty-required-manifest,
  reissue-inheritance, and repeated-no-delta variants

#### Scenario: Missing fixture builder blocks the matrix
- **WHEN** a current control-plane contract family is registered but cannot
  produce a minimal valid baseline
- **THEN** the matrix MUST fail and identify that family as missing a fixture
  builder instead of silently excluding it

### Requirement: Generated cells have runtime oracle outcomes
Each generated contract-exhaustion cell SHALL declare the expected runtime
oracle outcome for the current contract path.

#### Scenario: Invalid packet has concrete feedback
- **WHEN** a generated cell removes or corrupts a required packet, result,
  evidence, reviewer, blocker, or repair field
- **THEN** the oracle MUST expect a block or reissue that names the missing or
  invalid field, the current owner, and the repair target

#### Scenario: Downstream review is stopped for missing matching evidence
- **WHEN** a generated cell requires matching FlowGuard evidence but the
  matching evidence result, authorized read, manifest entry, or current
  packet-owned evidence artifact is missing
- **THEN** the oracle MUST expect downstream reviewer issuance to be stopped
  before the reviewer can produce a pass result

### Requirement: Historical failure families are matrix inputs
FlowPilot SHALL derive current same-class contract-exhaustion cells from
historical failure families that have already appeared in FlowPilot control
work, including missing bodies, missing mail/body handoff, wrong addresses,
stale route context, vanished evidence, install split-brain, invalid repair
targets, and repeated same-blocker storms.

#### Scenario: Historical family lacks normal repair route
- **WHEN** a history-derived failure family is added to the matrix
- **THEN** the family MUST name the normal repair route that should resolve it
  before GlassBreak and MUST NOT classify GlassBreak as an accepted outcome

#### Scenario: Historical owner is not consumed downstream
- **WHEN** history-derived cells emit a required evidence owner
- **THEN** TestMesh MUST register that owner as a current child suite and fail
  if the suite is missing, stale, or owns zero generated cells

### Requirement: Reissue preserves current packet-owned obligations
FlowPilot SHALL preserve or regenerate current packet-owned obligations when a
mechanical reissue replaces a current packet.

#### Scenario: FlowGuard reissue keeps evidence output policy
- **WHEN** a formal FlowGuard packet is mechanically reissued
- **THEN** the reissued packet MUST preserve or regenerate the current
  `evidence_output_policy` needed to create packet-owned evidence artifacts

#### Scenario: Reissue loss is a generated failure
- **WHEN** a generated matrix cell removes a required inherited obligation from
  a reissued packet
- **THEN** the runtime oracle MUST reject or block the reissue before downstream
  review treats the result as usable FlowGuard proof

### Requirement: No-delta repeats are finite
FlowPilot SHALL treat repeated rejected or blocked control-plane packets with no
new repair information as finite loop evidence.

#### Scenario: Same invalid packet repeats without repair delta
- **WHEN** a generated or replayed control-plane path returns the same invalid
  packet, missing evidence chain, or repair instruction gap without new
  actionable information
- **THEN** the runtime MUST record a no-delta loop signal instead of allowing
  indefinite reissue

#### Scenario: No-delta loop reaches GlassBreak alarm threshold
- **WHEN** normal PM, control-blocker, packet, Router, or ledger repair lanes
  cannot produce a legal next action for the same root cause
- **THEN** the matrix MUST project Controller GlassBreak eligibility as an
  alarm with the recorded failed normal-lane checks

#### Scenario: Formal rehearsal reaches GlassBreak
- **WHEN** a formal rehearsal reaches GlassBreak instead of repairing before
  the repeat threshold
- **THEN** the matrix MUST fail that rehearsal and require the normal repair
  route to be fixed

### Requirement: Matrix output owners become TestMesh child suites
FlowPilot SHALL treat each `required_evidence_owner` emitted by the
contract-exhaustion matrix as a required TestMesh child-suite owner.

#### Scenario: Matrix owner has no child suite
- **WHEN** a generated cell names a `required_evidence_owner`
- **THEN** the TestMesh report MUST include a matching child suite with current
  passing evidence and a positive owned-cell count

#### Scenario: Registered child suites omit a generated owner
- **WHEN** any generated owner is absent from the TestMesh child-suite map
- **THEN** the contract-exhaustion check MUST fail before synthetic coverage,
  Model-Test Alignment, or layered proof can consume the matrix

### Requirement: Live-run findings block final coverage
FlowPilot SHALL treat current live-runtime or current-state findings as
unfinished control-plane work, not as acceptable permanent baselines.

#### Scenario: Current lifecycle guard is stuck
- **WHEN** the current run ledger reports `lifecycle_guard.decision` as
  `control_plane_stuck`
- **THEN** process liveness and ModelMesh MUST report the run as not
  continuable and MUST include a concrete repair/blocker reason

#### Scenario: Final inventory contains live-runtime findings
- **WHEN** full-model coverage inventory contains a
  `live_runtime_or_state_findings` gap class
- **THEN** the full coverage claim MUST fail until the run is repaired or
  explicitly disposed through the current FlowPilot runtime path
