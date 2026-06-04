# staged-gated-effects Specification

## Purpose

FlowPilot stages small current-contract side effects on existing result or gate
surfaces when the side effect must be reviewed before runtime can safely commit
it.

## ADDED Requirements

### Requirement: Runtime stages gated side effects without parallel candidate ledgers

FlowPilot SHALL represent review-before-commit side effects with a lightweight
staged effect attached to an existing result or PM decision gate instead of
creating per-scenario candidate ledgers.

#### Scenario: Node plan result is staged before accepted binding

- **WHEN** PM submits a mechanically valid node acceptance plan result
- **THEN** runtime SHALL attach a staged effect with kind
  `commit_node_acceptance_plan` to the result
- **AND** runtime SHALL NOT bind accepted node plan or node context ids until the
  result's FlowGuard, Reviewer, and system closure gates pass.

#### Scenario: Route mutation is staged before active route change

- **WHEN** PM records a high-risk `mutate_route` decision
- **THEN** runtime SHALL attach a staged effect with kind
  `commit_route_mutation` to the PM decision gate
- **AND** runtime SHALL NOT change the active route version until the PM
  decision gate is closed and the staged effect is committed.

#### Scenario: Staged effect stays small

- **WHEN** runtime records a staged effect
- **THEN** the staged effect SHALL record only the effect kind, source
  packet/result identity, necessary target identity, status, and timestamps
- **AND** it SHALL NOT copy sealed result bodies, route payloads, node context
  payloads, or review report contents.

### Requirement: Runtime owns mechanical result validation

FlowPilot SHALL reject malformed current-result submissions at runtime/router
submission time instead of relying on FlowGuard or Reviewer to discover schema
or identity errors.

#### Scenario: Route plan compatibility shape is rejected early

- **WHEN** PM submits a planning result with an old wrapper, missing
  `flowpilot.route_plan.v1`, or a `route_nodes` alias
- **THEN** runtime SHALL block the result mechanically
- **AND** runtime SHALL keep repair on the same PM planning packet family.

#### Scenario: Semantic reviewers do not inspect field lists as router work

- **WHEN** FlowGuard or Reviewer receives a packet for a mechanically accepted
  result
- **THEN** that role SHALL review the real artifact, evidence, route effect,
  process risk, and quality sufficiency
- **AND** it SHALL NOT be responsible for replacing runtime's schema, path,
  hash, packet-kind, route-scope, or current-run validation.

### Requirement: Reissue preserves current packet family

FlowPilot SHALL preserve the original packet kind and route scope when PM asks
for `sender_reissue` or `collect_more_evidence`.

#### Scenario: PM repair decision reissue remains PM repair decision

- **WHEN** a blocker targets a `pm_repair_decision` packet
- **AND** PM selects `sender_reissue` or `collect_more_evidence`
- **THEN** runtime SHALL issue a fresh `pm_repair_decision` packet
- **AND** the new PM result SHALL update `pm_repair_decisions` and any
  applicable PM decision gate records through the normal PM repair parser.

### Requirement: Stopped semantic blockers require explicit recovery

FlowPilot SHALL keep stopped semantic blockers stopped until a current-runtime
stopped-blocker command records the recovery or terminal decision.

#### Scenario: Resume does not clear stopped semantic blocker

- **WHEN** PM selected `stop_for_user`
- **AND** Controller records a plain lifecycle resume
- **THEN** runtime SHALL keep the semantic blocker stopped
- **AND** runtime SHALL expose or require a stopped-blocker recovery command
  before dependent route work can continue.

### Requirement: Real FlowGuard toolchain failure is not fallback evidence

FlowPilot SHALL not turn FlowGuard API or model execution failures into manual
fallback pass/block evaluations.

#### Scenario: FlowGuard API unavailable

- **WHEN** the real FlowGuard API, import, or model runner fails for a formal
  FlowGuard work packet
- **THEN** runtime or the operator result SHALL record a FlowGuard toolchain
  blocker
- **AND** no `api_fallback_manual_block_eval` or equivalent fallback evaluation
  SHALL be counted as FlowGuard evidence.
