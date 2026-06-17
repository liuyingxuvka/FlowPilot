## ADDED Requirements

### Requirement: Parent closure checks FlowGuard evidence consistency
FlowPilot layered boundary coverage SHALL include parent closure cells that
bind FlowGuard result acceptance, packet outcome, work-order decision,
packet-owned evidence artifact, reviewer authorized reads, reviewer manifest,
and system validation to the same current proof chain.

#### Scenario: Result accepted but work order failed
- **WHEN** a FlowGuard result is accepted or a packet outcome passes while the
  matching FlowGuard work order is failed, missing, stale, or points at a
  missing current packet-owned evidence artifact
- **THEN** the parent closure proof MUST fail and prevent the result from
  supporting downstream review or system validation

#### Scenario: Required reviewer evidence manifest is empty
- **WHEN** a reviewer packet requires matching FlowGuard evidence but its
  evidence manifest entries are empty or do not authorize the matching
  FlowGuard result read
- **THEN** the parent closure proof MUST fail before reviewer pass evidence can
  support system validation

### Requirement: Parent consumes current child evidence ids
FlowPilot parent mesh confidence SHALL consume current child evidence ids and
runtime path evidence for repaired child models.

#### Scenario: Parent consumes stale child evidence
- **WHEN** a child model, matrix, or runtime path evidence changes after a
  model miss repair
- **THEN** the parent mesh MUST block broad confidence until it consumes the
  current child evidence id and confirms stable inputs, outputs, state,
  side-effects, outgoing guarantees, and runtime path evidence

#### Scenario: Contract-exhaustion child output is not reattached
- **WHEN** the contract-exhaustion child model emits generated cells,
  required child-suite owners, or history-derived replay rows
- **THEN** the layered boundary proof MUST reattach those outputs to the parent
  proof and include them in the leaf matrix before claiming coverage-accounting
  confidence

### Requirement: Full-leaf coverage rejects live blockers
FlowPilot layered boundary coverage SHALL keep the stricter full-leaf claim
false while any current live runtime or current-state blocker remains.

#### Scenario: Live runtime finding exists
- **WHEN** coverage inventory reports `live_runtime_or_state_findings`
- **THEN** `full_leaf_cartesian_ok` MUST be false and the requirement matrix
  MUST identify that gap class as a blocker

#### Scenario: Live runtime findings are repaired or disposed
- **WHEN** coverage inventory has zero live-runtime findings, no hard runner
  gaps, no stale child evidence, and Model-Test Alignment reports full coverage
- **THEN** the full-leaf requirement MAY become green through the normal
  layered boundary proof
