# Requirement And Scenario Audit

## Scope And Claim Boundary

This audit covers every requirement and all 88 scenarios in the 18 delta-spec
files for `upgrade-flowpilot-complete-workstream-orchestration`. It maps each
scenario group to the existing single FlowPilot runtime path, its primary
implementation owners, FlowGuard models, ordinary tests, and verification
contract checks. It does not treat a model result, generated JSON, prompt text,
or `openspec verify --no-run` report as current execution proof.

Evidence status terms used below:

- `mapped`: implementation/model/test/check ownership is explicit.
- `narrow-current`: a directly affected test was executed after the latest
  edit and passed.
- `stale`: an older pass exists but its covered source fingerprint no longer
  matches the current worktree.
- `blocked-precheck`: a check could not reach its assertion because the
  external FlowGuard engine and this project's governed artifacts are between
  compatible frozen versions.
- `final-current`: the `final18` parent receipts and terminal consumer match
  frozen source fingerprint
  `10f38ac754a614ed5508ad30bc16b270a6942087db79b156094f65184c7b4389`.

## User-Agreed Outcome Audit

| User-agreed outcome | Existing single-path owner | Contract evidence | Current status |
|---|---|---|---|
| FlowPilot is only for complex, long-running, high-standard projects | PM role card, high-standard startup/planning route, route decomposition criteria | `req.workstream.pm`, `check.workstream.prompts`, `check.review.flow` | final-current |
| Every substantive AI understands, writes a numbered plan, executes/delegates, integrates, verifies, repairs, and reports step status | shared role handoff plus existing `contract_self_check.workstream_plan_and_completion` | `req.workstream.lifecycle`, `req.workstream.report`, `req.role.plan_status` | final-current |
| Controller remains mechanical | foreground action ledger and current runtime command surface | `req.workstream.controller_boundary`, `check.controller.boundary` | final-current |
| PM owns whole-project ambition, architecture, integration, low-score disposition, and closure | existing PM cards, route/node/repair/final-ledger owners | `req.workstream.pm`, `req.flowguard.pm_test_disposition` | final-current |
| Role-local FlowGuard may help, but independent formal FlowGuard and Reviewer remain mandatory at named boundaries | existing FlowGuard work-order/report and review-window paths | `req.workstream.flowguard`, `req.flowguard.boundaries` | final-current |
| Local skill inventory remains mandatory and shallow until PM selection | Runtime discovery packet plus PM skill selection | `req.discovery.skill_inventory`, `req.role.inventory_depth` | final-current |
| Material reading/research is ordinary role work; no special material phase or sufficiency gate remains | existing research/PM role-work packet/result/disposition path | `req.discovery.ordinary_material_work`, `req.removed.material_phase`, `req.removed.material_sufficiency` | final-current |
| Material map is optional navigation only | existing optional map facade and terminal link projection | `req.discovery.optional_map`, `req.material.map_linkage` | final-current |
| Fake-AI and Cartesian evidence is executable, count-reconciled, and bounded | canonical opened-packet responder, formal execution closure, ContractExhaustionMesh/TestMesh | `req.fake.canonical`, `req.coverage.*`, `req.synthetic.*` | final-current |
| Validation uses affected checks after edits and exactly one stable final full run | TestMesh tier ownership, frozen fingerprint, acyclic final consumer | `req.tiers.participation`, `req.tiers.freshness`, `req.tiers.acyclic` | final-current; duplicate owner removed |
| Source, installed skill, repository prompts, and local Git converge before closure | install audit/parity, public boundary, scoped Git and OpenSpec archive gates | `req.release.local_sync` | source/install final-current; scoped local Git close pending |

## Complete Scenario Inventory

### `complete-ai-workstream-orchestration` — 10 scenarios

- Scenarios: `Worker receives a bounded route leaf`; `Reviewer or FlowGuard Operator receives formal work`; `Complete workstream report`; `Missing or contradictory plan evidence`; `Controller relays a role packet`; `Leaf contains several local execution steps`; `Leaf leaks PM authority`; `Local results pass but the project is incoherent`; `Reviewer score is below target`; `Worker uses role-local FlowGuard`.
- Implementation: `flowpilot_core_runtime/role_handoff.py`, `packet_result_contracts.py`, `review_window_contracts.py`, route decomposition criteria, and existing PM/Worker/Reviewer/FlowGuard/Controller cards.
- Model/tests/checks: `flowpilot_complete_workstream_orchestration_model.py`; `test_flowpilot_complete_workstream_orchestration.py`; `test_flowpilot_complete_workstream_fake_ai.py`; `check.workstream.model`, `check.workstream.prompts`, `check.workstream.fake_ai`, `check.controller.boundary`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `daemon-projection-reconciliation` — 3 scenarios

- Scenarios: `Ordinary research result event exists only in role output ledger`; `Generic direct role event is replayed`; `Invalid or unauthorized direct role event exists`.
- Implementation: existing daemon/event dispatcher and role-output reconciliation modules; no material-specific replay path.
- Model/tests/checks: `flowpilot_daemon_reconciliation_model.py`; role-output reconciliation and startup-daemon tests; `check.daemon.projection`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `dispatch-recipient-gate` — 8 scenarios

- Scenarios: `Formal work packet checks target role before exposure`; `System-card bundle remains grouped`; `System card can guide the current active obligation`; `User intake blocks independent PM dispatch until first output`; `User intake first output frees PM for later dispatch`; `System-card work wait blocks follow-up dispatch`; `ACK-only card is prompt context, not a work package`; `Output-bearing event card is work context`.
- Implementation: `flowpilot_router_dispatch_gate.py`, current dispatch policy, system-card grouping, and first-output state.
- Model/tests/checks: `flowpilot_dispatch_recipient_gate_model.py`; `tests/router_runtime/dispatch_gate.py` through the public wrapper; `check.dispatch.model`, `check.dispatch.runtime`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `executable-repair-transactions` — 12 scenarios

- Scenarios: `Operation replay names a replayable operation`; `Controller repair work packet is bounded`; `Await existing event names a producer`; `Role reissue and route mutation name current PM producers`; `Terminal stop is explicit`; `Retired replacement-packet repair is rejected`; `Role reissue without producer is rejected`; `Ordinary role rework uses the existing package path`; `PM repair decision enables a current follow-up wait`; `Half-committed repair state is detected`; `Replayed operation has fresh identity`; `Replayed operation uses current packet and route identity`.
- Implementation: existing repair transaction, outcome, finalization, Controller repair, replay scheduling, and control-blocker modules; retired packet-reissue names remain negative-only.
- Model/tests/checks: `flowpilot_repair_transaction_model.py`; `tests/router_runtime/control_blockers.py` and route-mutation tests; `check.repair.model`, `check.repair.runtime`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `finite-ai-contract-exhaustion` — 5 scenarios

- Scenarios: `Semantic fake profile executes`; `Generated case was not executed`; `Child proof is stale`; `Pairwise public-path coverage is selected`; `All declared cases pass`.
- Implementation: canonical `ContractDrivenFakeAIResponder.from_open_packet_result`, formal AI execution closure, current Cartesian matrix, evidence-truth accounting, and ContractExhaustionMesh.
- Model/tests/checks: complete-workstream fake-AI runner, formal AI tests, contract exhaustion and Cartesian tests; `check.workstream.fake_ai`, `check.contract.exhaustion`, `check.cartesian`, `check.acceptance.testmesh`.
- Evidence: final-current; older `final16` and `final17` proof remains diagnostic-only.

### `flowguard-boundary-test-alignment` — 3 scenarios

- Scenarios: `Plan-report obligation lacks ordinary evidence`; `Removed material field remains positive`; `Historical material label remains`.
- Implementation: existing Model-Test Alignment family/source contracts and deleted-material source classifier.
- Model/tests/checks: `flowpilot_model_test_alignment_family_plans.py`, MTA source-audit modules, `test_flowpilot_model_test_alignment.py`, retired-material authority tests; `check.model_test_alignment`, `check.deleted.material`.
- Evidence: final-current. The atomic `error_paths` tuple defect and singular
  behavior-ledger migration are repaired; strict final MTA consumed the
  current `final18` manifest.

### `flowguard-full-coverage-findings` — removed requirement, 0 scenarios

- Removed surface: `Material Scan Phase Writes Stay Synchronized`.
- Disposition: dedicated material phase/event/packet/frontier authority is deleted or negative/historical-only; ordinary role-work owns real reading/research.
- Tests/checks: removed-material source audit and runtime rejection; `check.deleted.material`, `check.resource.runtime`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `flowguard-test-obligation-ownership` — 4 scenarios

- Scenarios: `Node entry chooses the smallest sufficient evidence route`; `FlowGuard reports become PM disposition inputs`; `Worker results refresh post-result obligations`; `Role-local model exists`.
- Implementation: existing PM and FlowGuard Operator cards, FlowGuard work order/report, post-result obligation refresh, MTA/TestMesh selection.
- Model/tests/checks: `flowpilot_test_obligation_ownership_model.py`, `flowpilot_skillguard_contract_model.py`, the focused SkillGuard contract runner, card-instruction and high-standard tests; `check.skillguard.model`, `check.flowguard.obligation`, `check.prework.flowguard`, `check.review.flow`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `flowpilot-packet-review-flow` — 4 scenarios

- Scenarios: `Substantive role result returns to PM for disposition`; `Raw role result cannot satisfy dependent gate`; `Plan is specific and fully evidenced`; `Plan is ceremonial or incomplete`.
- Implementation: current packet result return, PM package disposition, review-window challenge, and repair/recheck path.
- Model/tests/checks: synthetic agent trace replay, high-standard flow, AI contract projection, complete-workstream fake AI; `check.packet.review`, `check.review.flow`, `check.workstream.fake_ai`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `material-artifact-map` — 4 scenarios

- Scenarios: `Material map entry policy is internally split without changing output`; `Optional map is absent`; `Route memory references existing map`; `Final ledger has no map`.
- Implementation: existing public map facade and child entry-policy modules, route-memory projection, and final-ledger optional link.
- Model/tests/checks: `flowpilot_material_artifact_map_model.py`, material-access mesh and terminal tests; `check.material.map`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `ordinary-resource-discovery` — 7 scenarios

- Scenarios: `Runtime issues discovery`; `Only selected skills are deeply loaded`; `Current discovery omits old material fields`; `Old material-shaped discovery is submitted`; `PM needs deeper source analysis`; `Existing material is already sufficient`; `No material map exists`.
- Implementation: Runtime shallow inventory, narrowed `task.discovery` result, PM selection, ordinary research/PM role work, and optional map.
- Model/tests/checks: `flowpilot_ordinary_resource_discovery_model.py`, `test_flowpilot_ordinary_resource_discovery.py`; `check.resource.model`, `check.resource.runtime`, `check.child_skill`, `check.deleted.material`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `packet-open-authority-exits` — 7 scenarios

- Scenarios: `PM needs startup repair`; `PM reaches no legal startup repair path`; `PM receives Router control blocker`; `Result author matches current role binding`; `Role-name agent id is repaired through the current result path`; `Reviewer release waits for formal PM disposition`; `Packet evidence cannot bypass PM disposition contract`.
- Implementation: current packet-open/lease/result authority, startup and control-blocker exits, PM disposition, and reviewer release gate.
- Model/tests/checks: `flowpilot_packet_open_authority_model.py`, packet runtime/control-plane/high-standard tests; `check.packet.authority`, `check.packet.review`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `role-child-skill-use` — 3 scenarios

- Scenarios: `Local planning skill is candidate-only but considered`; `Process-support skill is not needed`; `Many local skills are available`.
- Implementation: Runtime shallow inventory and PM candidate selection/skip guidance; no Runtime semantic skill choice.
- Model/tests/checks: ordinary-resource and capability models; contract-surface/high-standard tests; `check.child_skill`, `check.resource.runtime`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `role-scoped-quality-repair-prompts` — 5 scenarios

- Scenarios: `Worker completes and repairs a packet-scoped workstream`; `Worker escalates out-of-scope defect`; `Ordinary evidence packet reports target defect`; `FlowGuard Operator corrects model evidence`; `Generic PM role-work targets any substantive role`.
- Implementation: shared role handoff, Worker/evidence/FlowGuard cards, PM role-work packet, and existing blocker/suggestion return paths.
- Model/tests/checks: complete-workstream model, card-instruction tests, complete-workstream prompt tests; `check.role.prompts`, `check.workstream.prompts`, `check.prework.flowguard`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `router-external-wait-reconciliation` — 3 scenarios

- Scenarios: `Follow-up wait records producer evidence`; `Empty follow-up wait becomes PM correction`; `Producer evidence is current-packet scoped`.
- Implementation: repair transaction producer bindings, blocker outcome/index projection, and daemon-visible current wait state.
- Model/tests/checks: repair transaction model and control-blocker tests; `check.repair.model`, `check.repair.runtime`.
- Evidence: final-current. The removed material-generation close path is negative-only through `req.removed.material_wait`.

### `shared-skill-maintenance-log` — 4 scenarios

- Scenarios: `Existing shared log is used`; `Missing shared log is created in shared format`; `PM planning reports the maintenance row`; `Bookkeeping does not block project acceptance`.
- Implementation: the existing PM card now requires the full row identity and cites path/entry id through the existing PM planning or workstream self-check surface, with no new field, packet, node, or gate.
- Model/tests/checks: `flowpilot_shared_maintenance_log_model.py`; the exact new PM-card test; `check.shared.maintenance`, `check.workstream.prompts`.
- Evidence: final-current; the PM-card projection and model receipt are both included.

### `synthetic-agent-coverage-matrix` — 3 scenarios

- Scenarios: `Profile bypasses canonical responder`; `Parent receipt overstates proof`; `Shallow role result reaches review`.
- Implementation: canonical opened-packet responder, synthetic coverage matrix, finite execution receipts, PM disposition/reviewer repair path.
- Model/tests/checks: `flowpilot_synthetic_agent_coverage_matrix.py`, synthetic matrix and complete-workstream fake-AI tests; `check.synthetic.matrix`, `check.workstream.fake_ai`, `check.contract.exhaustion`.
- Evidence: final-current through the `final18` parents and terminal consumer.

### `tiered-flowpilot-test-validation` — 3 scenarios

- Scenarios: `Focused test passes but parent is stale`; `Source changes during background run`; `Final confidence is placed inside release evidence`.
- Implementation: test-tier definitions, covered-source fingerprint, background artifact contract, TestMesh compilation, and terminal final-confidence consumer.
- Model/tests/checks: tiering/slow-test models and `test_flowpilot_test_tiers.py`; `check.tier.structure`, the three background parent checks, TestMesh compile, and final background check.
- Evidence: final-current. The parent-participation test passed, the duplicate
  all-tier owner is absent, and the acyclic final consumer passed with one
  execution owner.

## Current Open Gates

1. Frozen source fingerprint
   `10f38ac754a614ed5508ad30bc16b270a6942087db79b156094f65184c7b4389`
   is shared by all `final18` parent receipts and the terminal consumer.
   `all` passed 167/167, adversarial passed 6/6, release passed 6/6, and the
   terminal final-confidence consumer passed 1/1. Older `final16` and `final17`
   evidence is diagnostic-only and must not be resumed.
2. Meta and Capability full parents each ran once through their release-tier
   owner and wrote current stable receipts under `tmp/flowguard_background`.
   Later consumers are read-only and cannot relaunch those owners.
3. The final acceptance manifest accounts for 179 selected, executed, and
   passed child commands. Contract exhaustion, Cartesian coverage,
   Model-Test Alignment, Acceptance TestMesh, and ModelMesh all consumed the
   manifest successfully with zero missing or failed coverage obligations.
4. FlowPilot source/install parity, installed runtime checks, current V2
   SkillGuard projection, topology, privacy/URL/package boundary, and public
   release checks are current. The optional UI companion remains an explicit
   warning only and is not required by the FlowPilot runtime contract.
5. Remaining closure is limited to one strict local OpenSpec verification,
   scoped local Git integration, change archive, and predictive-KB postflight.
