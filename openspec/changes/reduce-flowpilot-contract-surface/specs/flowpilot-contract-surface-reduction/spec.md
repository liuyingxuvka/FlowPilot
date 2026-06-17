## ADDED Requirements

### Requirement: Contract Field Disposition

FlowPilot SHALL classify every field touched by this change as exactly one of
`keep`, `move`, or `delete`. A field with `keep` SHALL appear in exactly one
packet family contract. A field with `move` SHALL name its target family. A
field with `delete` SHALL be rejected when submitted in a current-contract
result unless another active OpenSpec change explicitly owns a named migration.

#### Scenario: Field is moved out of early packet
- **WHEN** a `task.high_standard_contract` result includes
  `acceptance_item_registry.items[].owner_node_ids`
- **THEN** Runtime SHALL reject it as a field that moved to
  `task.planning.nodes[].acceptance_item_ids`

#### Scenario: Deleted field is submitted
- **WHEN** a current result includes a field listed in the matrix row's
  `deleted_fields`
- **THEN** Runtime SHALL reject the result without translating the field into a
  supported shape

### Requirement: Packet Family Minimal Contracts

FlowPilot SHALL define a minimal current contract for every packet family in
the mainline lifecycle: `task.high_standard_contract`, `task.discovery`,
`task.skill_standard`, `task.planning`, `task.node_acceptance_plan`,
`task.node`, `flowguard_check.post_result`, `review.any_current_subject`,
`pm_repair_decision.pm_repair_decision`, `pm_disposition.node_pm_disposition`,
`task.parent_backward_replay`, and `review.terminal_backward_replay`.

#### Scenario: All mainline families have matrix rows
- **WHEN** tests enumerate the mainline packet families
- **THEN** each family SHALL have a matrix row with current required fields,
  moved fields, deleted fields, allowed blocker classes, fixed blocker actions,
  and required evidence owner

#### Scenario: Unknown packet family is encountered
- **WHEN** Runtime or validation requests a stage matrix row for an unknown
  current packet family
- **THEN** the lookup SHALL fail instead of returning a generic fallback row

### Requirement: High Standard Contract Is Definition Only

The `task.high_standard_contract` result SHALL keep only `requirements` and
`acceptance_item_registry` as top-level required fields. Requirement rows SHALL
use `requirement_id`, `classification`, `summary`, `source_user_intent`, and
`closure_rule`. Acceptance item rows SHALL use `acceptance_item_id`,
`source_type`, `source_requirement_ids`, `summary`, `quality_floor`,
`future_evidence_rule`, and `status`.

#### Scenario: Valid high-standard definition passes
- **WHEN** PM submits requirements and acceptance items with the required
  definition fields
- **THEN** Runtime SHALL accept the result as mechanically valid without
  requiring route-node owners, worker evidence, target proof, or final replay
  evidence

#### Scenario: Future-stage fields appear in first packet
- **WHEN** PM submits `owner_node_ids`, `review_gate_ids`, or
  `final_replay_required` inside the high-standard acceptance registry
- **THEN** Runtime SHALL reject those fields as moved or deleted current
  contract fields

### Requirement: Discovery And Skill Standard Stay Preplanning

`task.discovery` SHALL prove material and candidate-skill readiness to continue
planning. `task.skill_standard` SHALL define skill obligations. Neither family
SHALL require worker artifacts, final evidence, or executed-skill proof.

#### Scenario: Discovery proceeds without worker artifacts
- **WHEN** a discovery result supplies material sources, material sufficiency,
  and candidate skill inventory
- **THEN** Runtime SHALL accept the result without worker or final evidence

#### Scenario: Skill standard defines obligations
- **WHEN** a skill standard result supplies obligations with
  `obligation_id`, `skill`, `role_use`, `use_context`, and `evidence_rule`
- **THEN** Runtime SHALL accept the result without requiring executed skill
  artifacts

### Requirement: Planning Owns Parent Child Structure

`task.planning` SHALL own route nodes, parent/child relationships, and
acceptance item assignment. It SHALL NOT require worker results, post-result
FlowGuard reports, target proof, or terminal replay evidence.

#### Scenario: Planning assigns active acceptance items
- **WHEN** a route plan contains nodes with parent/child structure and
  `acceptance_item_ids`
- **THEN** Runtime SHALL validate that active acceptance items are assigned to
  route nodes

#### Scenario: Planning omits worker result evidence
- **WHEN** a route plan is structurally valid but has no worker result artifact
- **THEN** Runtime SHALL not block for missing worker result evidence

### Requirement: Node Acceptance Plan Uses Five Groups

`task.node_acceptance_plan` SHALL use `decision` and `node_context_package`.
The `node_context_package` SHALL contain exactly the behavior-bearing groups:
`node_id`, `node_goal`, `acceptance_projection`, `evidence_projection`,
`risk_projection`, and `handoff_notes`.

#### Scenario: Node plan supplies five groups
- **WHEN** PM submits a node acceptance plan with the five node context groups
- **THEN** Runtime SHALL accept the plan without requiring worker results or
  terminal replay evidence

#### Scenario: Old node context scatter fields are submitted
- **WHEN** a node acceptance plan submits old scatter fields such as
  `test_obligation_matrix.pre_worker`, `work_packet_projection`,
  `final_user_intent_checks`, or `structure_hygiene_expectation`
- **THEN** Runtime SHALL reject them as deleted current-contract fields

### Requirement: Node Results Own Current Evidence

`task.node` SHALL own current node execution evidence. A node result SHALL use
`decision`, `pm_visible_summary`, and `current_evidence_refs`.

#### Scenario: Node result has current evidence
- **WHEN** Worker submits a node result with current evidence references bound
  to the current node
- **THEN** Runtime and later review SHALL allow the node result to continue to
  FlowGuard and Reviewer gates

#### Scenario: Node result is progress-only
- **WHEN** Worker submits a node result with no current evidence references or
  only progress text
- **THEN** the node result SHALL be blocked by the node/current evidence gate

### Requirement: FlowGuard Result Body Is PM Facing

`flowguard_check.post_result` SHALL require only
`pm_visible_summary`, `reviewed_by_role`, `passed`, `modeled_boundary`,
`blockers`, `pm_suggestion_items`, and `contract_self_check`. FlowGuard model
details SHALL be stored in the packet-owned run-local
`flowguard_evidence.json`.

#### Scenario: FlowGuard report uses compact body
- **WHEN** FlowGuard submits the compact result body and the packet-owned
  evidence file is current
- **THEN** Runtime SHALL accept the result without requiring model-detail
  fields in the result body

#### Scenario: Model detail fields are submitted in result body
- **WHEN** FlowGuard submits result-body fields such as `commands_run`,
  `model_obligations`, `ordinary_test_evidence`, `missing_test_kinds`, or
  `evidence_consistency`
- **THEN** Runtime SHALL reject them as deleted from the result body contract

### Requirement: Reviewer Keeps Blocking Authority

`review.any_current_subject` SHALL require only `pm_visible_summary`,
`reviewed_by_role`, `passed`, `findings`, `blockers`,
`pm_suggestion_items`, and `contract_self_check`. Reviewer SHALL be able to
block current-stage quality, evidence, or completion failures by selecting a
fixed blocker class allowed by the subject family.

#### Scenario: Reviewer blocks current-stage quality issue
- **WHEN** Reviewer identifies a quality failure that belongs to the current
  subject stage
- **THEN** Reviewer SHALL submit a fixed blocker class and fixed handling route
  for PM repair-decision intake

#### Scenario: Reviewer attempts future-stage blocker
- **WHEN** Reviewer blocks an early package for future-stage evidence such as
  worker output or terminal replay
- **THEN** Runtime SHALL reject the blocker shape if its class is not allowed
  for the subject family

### Requirement: PM Repair Uses One Fixed Decision Packet

`pm_repair_decision.pm_repair_decision` SHALL use `decision`, `reason`,
`target_blocker_id`, and `next_action` for ordinary repairs. Branch-specific
payloads SHALL only be valid for the matching decision branch.

#### Scenario: Ordinary repair has no route payload
- **WHEN** PM chooses a same-stage repair
- **THEN** Runtime SHALL accept the minimal repair fields and SHALL NOT require
  route, parent, or terminal repair payloads

#### Scenario: Route redesign branch requires planning payload
- **WHEN** PM chooses `redesign_route`
- **THEN** Runtime SHALL require the next packet to be a planning package with
  the current route-plan contract

### Requirement: PM Disposition Uses One Acceptance Item Table

`pm_disposition.node_pm_disposition` SHALL use
`acceptance_item_disposition[]` instead of separate accepted, blocked, waived,
and superseded id arrays.

#### Scenario: Node-owned item has one disposition row
- **WHEN** PM dispositions a node result
- **THEN** every node-owned acceptance item SHALL have one row with
  `acceptance_item_id`, `decision`, `reason`, and `evidence_refs`

#### Scenario: Old disposition arrays are submitted
- **WHEN** PM submits `accepted_acceptance_item_ids`,
  `blocked_acceptance_item_ids`, `waived_acceptance_item_ids`, or
  `superseded_acceptance_item_ids`
- **THEN** Runtime SHALL reject the old array fields

### Requirement: Parent And Terminal Replay Stay Separate

Parent replay SHALL check child composition for a parent node. Terminal replay
SHALL check final artifact evidence, all active acceptance item closure, route
segment replay, waiver records, and final blockers.

#### Scenario: Parent replay does not close terminal route
- **WHEN** parent replay passes child composition
- **THEN** FlowPilot SHALL NOT treat that pass as terminal final closure

#### Scenario: Terminal replay requires final closure
- **WHEN** terminal replay lacks final artifact evidence, active acceptance
  item closure, legal waivers, or current route replay evidence
- **THEN** terminal replay SHALL block final completion

### Requirement: Fixed Blocker Class Mapping

FlowPilot SHALL require every blocker submitted by Runtime, FlowGuard,
Reviewer, PM, parent replay, or terminal replay to use a fixed
`blocker_class` and the fixed `next_action` declared in the stage matrix row.
Runtime SHALL validate enum membership and next-action mapping only. For
substantive PM-owned blockers, that `next_action` SHALL route to the current
PM repair-decision packet and SHALL NOT preselect PM's
`repair_current_scope`, `repair_parent_scope`, or `redesign_route` branch.

#### Scenario: Blocker class maps to fixed action
- **WHEN** a role submits a blocker
- **THEN** Runtime SHALL verify that `next_action` equals the matrix mapping
  for the submitted `blocker_class`

#### Scenario: Unknown blocker class is submitted
- **WHEN** a role submits an unknown blocker class
- **THEN** Runtime SHALL reject the result as a blocker shape error without
  interpreting the blocker prose

### Requirement: Blocker Repair Packet Contracts

FlowPilot SHALL define one repair packet contract for every supported
`blocker_class`. The repair contract SHALL name the repair packet family,
required current source packet/result/node ids, required opened-body receipts
or evidence refs, required repair payload fields, owner role, and return gate.

#### Scenario: Reviewer quality blocker opens PM repair decision
- **WHEN** Reviewer submits `review_quality_block`
- **THEN** Runtime SHALL open a PM repair-decision packet that carries the
  blocked subject id, Reviewer result id, opened-body receipt for the Reviewer
  report, recommended repair context, and the current repair contract; PM SHALL
  then choose the repair branch

#### Scenario: Route structure blocker opens PM repair decision
- **WHEN** FlowGuard or Reviewer submits `route_structure_block`
- **THEN** Runtime SHALL open a PM repair-decision packet that carries the
  blocked route version, subject packet/result ids, opened-body receipts for
  the blocking reports, and recommended structural context; PM SHALL choose
  whether the fix is current-scope repair, parent-scope repair, route redesign,
  stop, or authorized waiver

#### Scenario: Missing current evidence opens PM repair decision
- **WHEN** a node or review gate submits `missing_current_evidence`
- **THEN** Runtime SHALL open a PM repair-decision packet with the current node
  id, missing evidence ids or evidence kinds, blocking report receipt, required
  current evidence refs, and repair obligations for PM branch selection

#### Scenario: Terminal closure blocker opens PM repair decision
- **WHEN** terminal replay submits `terminal_closure_block`
- **THEN** Runtime SHALL open a PM repair-decision packet with final replay
  segment ids, unclosed acceptance item ids, waiver records if any, blocking
  terminal report receipt, required final evidence refs, and terminal
  supplemental repair contract requirements when PM continues repair

#### Scenario: Parent composition blocker opens PM repair decision
- **WHEN** parent replay submits `parent_composition_block`
- **THEN** Runtime SHALL open a PM repair-decision packet with parent node id,
  child node ids, child evidence refs, and the composition blocker receipt; PM
  SHALL choose the repair branch, and `repair_parent_scope` requires the
  parent repair scope contract

### Requirement: Repeated Repair Carries Lineage Materials

FlowPilot SHALL require every repeated repair attempt for the same repair
lineage to carry the materials from the prior repair attempt plus the current
blocking report. The repeated repair packet SHALL include the original
blocker id, prior repair packet id, prior repair evidence refs, prior blocking
report id, reason the prior repair did not close, current blocking report id,
new evidence or decision, and the return gate produced by PM's selected
structured branch.

#### Scenario: Second repair attempt keeps first repair context
- **WHEN** a repair packet fails recheck and PM opens a second repair attempt
- **THEN** the second repair packet SHALL carry the original blocker, the first
  repair packet id, the first repair evidence refs, the failed recheck result,
  and the new repair payload

#### Scenario: Repeated repair omits prior materials
- **WHEN** a repeated repair packet omits the previous repair packet id or
  failed recheck result
- **THEN** Runtime SHALL reject the repair packet as mechanically incomplete

### Requirement: Fallback Surfaces Are Removed

Current FlowPilot SHALL reject legacy aliases, shape guessing, legacy wrappers,
manual fallback blocker evaluation, newest-run fallback, repo-root fallback,
historical run evidence fallback, old packet promotion, old results as current
evidence, and target-project dependence on FlowPilot development scripts.

#### Scenario: Historical result is submitted as current evidence
- **WHEN** a role cites a historical run result as current evidence
- **THEN** Runtime or the owning current-evidence gate SHALL reject it

#### Scenario: Target project lacks development script
- **WHEN** an arbitrary target project does not contain FlowPilot development
  repository scripts
- **THEN** FlowPilot SHALL rely on installed runtime self-check receipts and
  run-local evidence, not a dev-repo script fallback
