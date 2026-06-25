# Handoff

## Purpose

Build and maintain a Codex skill named `flowpilot`.

FlowPilot lets an AI agent manage a substantial software project as a
model-backed project-control runtime:

1. interrogate its understanding before freezing a contract;
2. create persistent project-control state under `.flowpilot/`;
3. require material intake and PM material understanding before product design;
4. require a PM-owned product-function architecture before contract freeze;
5. model the project-control route with FlowGuard;
6. route to specialized capabilities at explicit nodes;
7. execute bounded chunks;
8. verify each chunk before moving on;
9. update the model and route when new facts invalidate the current route;
10. open, reuse, or replace only the currently requested packet responsibility
  for each new formal FlowPilot task, with a project manager as route-decision
  authority and worker roles limited to bounded Helper tasks;
11. finish only after evidence proves the frozen contract is met.

## Current Maintenance Gate

The current new-only maintenance rule is no compatibility or fallback surfaces
by default. FlowPilot runtime, prompt, OpenSpec, and test changes should keep a
single structured current path for each behavior. Legacy aliases, old pointer
fields, prose parsers, missing-field defaults, nested shape normalization,
old-router active execution fallback, and automatic historical artifact
promotion are unsupported unless a future OpenSpec change explicitly approves a
named migration. Runtime recovery is still allowed when it is current-run,
owner-scoped, packet/node-scoped, and blocks or reissues instead of translating
old input into valid current evidence.

Current-contract bug repairs must also follow
`docs/flowpilot_current_contract_repair_discipline.md`. Future agents should
use that guide before adding fields or prompt requirements: first check the
stage matrix, role boundary, fixed blocker action, repair packet contract, and
repeated-repair lineage rule; then shrink, move, or delete the mismatched
requirement instead of stacking another compatibility surface.

The current structure-maintenance baseline uses a FlowGuard StructureMesh /
TestMesh gate before broad router or model-script refactors. The gate lives in
`simulations/flowpilot_structure_maintenance_model.py` and is checked by
`simulations/run_flowpilot_structure_maintenance_checks.py`.

The same maintenance baseline now includes a FlowGuard Model-Test Alignment
gate. It lives in `simulations/run_flowpilot_model_test_alignment_checks.py`
and maps major model obligations to ordinary tests before a coverage claim is
trusted.

The maintenance baseline also includes a FlowGuard model maturation closure
gate. It lives in `simulations/run_flowpilot_model_maturation_checks.py` and
consumes FlowGuard 0.27 `review_model_maturation_loop()` signals before broad
maintenance or local install confidence is promoted. This gate turns ACK-only
closure risk, route replacement disposition gaps, prompt-contract drift, stale
result artifacts, oversized parent-model masking, and progress-only background
evidence into explicit model actions or scoped-confidence decisions.

The maintenance baseline also includes a focused singleton identity authority
gate. It lives in `simulations/run_flowpilot_singleton_identity_checks.py` and
records `simulations/flowpilot_singleton_identity_results.json`. It separates
intended plurality such as parallel runs and background Flow blocks from
illegal duplicate authority inside one scope, including daemon writers, active
packet holders, PM package dispositions, route replacement, material progress
generation, ACK/output waits, and final closure evidence.

The maintenance baseline also includes a FlowGuard similarity-convergence gate.
It lives in `simulations/flowpilot_similarity_convergence_model.py`, is checked
by `simulations/run_flowpilot_similarity_convergence_checks.py`, and records
`simulations/flowpilot_similarity_convergence_results.json`. It uses FlowGuard
0.39 model-similarity and plan-detail APIs to group similar packet-result,
ACK-return, route-mutation, and reconciliation branches; derive sibling impact
when one member changes; keep false friends such as route display versus route
mutation separate; and classify branch-fold candidates before Architecture
Reduction, Model-Test Alignment, ModelMesh, StructureMesh, or replay work.

The maintenance baseline also includes a focused blocker repair information-flow
gate. It lives in
`simulations/flowpilot_blocker_repair_information_flow_model.py`, is checked by
`simulations/run_flowpilot_blocker_repair_information_flow_checks.py`, and
records `simulations/flowpilot_blocker_repair_information_flow_results.json`.
It validates that current blocker details, reviewer required-repair guidance,
PM repair decisions, fresh repair package content, worker semantic deltas,
success evidence contracts, reviewer recheck bindings, and same-blocker loop
escapes remain connected end to end.

The information-flow baseline also includes a broader project-control parent
gate. It lives in
`simulations/flowpilot_project_control_information_flow_model.py`, is checked
by `simulations/run_flowpilot_project_control_information_flow_checks.py`, and
records `simulations/flowpilot_project_control_information_flow_results.json`.
It keeps interruption/manual lifecycle resume, reopened continuation runs,
Controller break-glass repair, route mutation, on-demand role assignment,
follow-up blockers, terminal stop, and closure paths under the same rule:
nonterminal work needs current run state plus new information, or it must
block, mutate, or stop instead of repeating stale work.

The information-flow baseline is now also bound to concrete code contracts,
test evidence, and prompt/card source markers through
`simulations/run_flowpilot_information_flow_alignment_checks.py`, which records
`simulations/flowpilot_information_flow_alignment_results.json`. That alignment
gate checks 10 information-flow obligations across blocker repair, manual
lifecycle resume, reopen, break-glass, route mutation, on-demand role
assignment, closure, and terminal stop. The current contract forbids treating
heartbeat automation, stale role reports, or fixed role-set restoration
as current formal-run authority. PM result disposition has a direct opened-body
validation test, and resume/role-dispatch evidence is bound to
`flowpilot_new.py resume` and `dispatch-current-role`.

The current startup trunk is Runtime/Router mechanical entry followed by PM
first-round work. Startup no longer has a Reviewer startup fact gate or a PM
startup activation gate. Runtime creates the current run, seals startup input,
writes startup mechanical audit, writes display/status evidence, audits current
run identity, and records any structured stop/block reason. When those
mechanical conditions pass, Router delivers the sealed `user_intake` packet to
PM for the first material/intake decision. Background or parallel roles remain
mandatory FlowPilot capability: if the user-facing acknowledgement is disabled
or the host cannot open the requested current role surface, Runtime stops or
blocks; after authorization it dispatches only the currently requested packet
responsibility through `dispatch-current-role`. Reviewer judges human quality,
evidence credibility, requirement satisfaction, and repair need only after
Runtime accepts mechanics. FlowGuard
operator judges model/process/state risks; Runtime/Router owns fields, hashes,
paths, packet/result/current-run ids, role-agent binding, output-contract shape,
and ledger absorption.

The current executable-node trunk invariant is: PM node entry self-check ->
ordinary node plan Reviewer -> Worker -> post-result FlowGuard -> independent
Reviewer. Ordinary node execution no longer has a mandatory pre-worker
FlowGuard gate. If PM discovers at node entry that the current route/node shape
is too broad, too narrow, wrongly ordered, or otherwise structurally wrong, PM
must submit a structural `redesign_route` plan instead of issuing a worker-ready
node plan. Runtime then stages the route effect, requires FlowGuard to simulate
the current route plan and its work/validation/failure/repair paths, requires
PM to absorb that FlowGuard result through `pm_flowguard_acceptance`, and only
then sends the PM absorption package to Reviewer. The focused owning model is
`simulations/flowpilot_prework_flowguard_gate_model.py`; despite the historical
filename, its current semantics are structural route-change FlowGuard and PM
absorption. The total Model-Test Alignment family is named `current-node trunk
invariant`.

As of the new-only FlowPilot contract, the active maintenance baseline is
recorded in `docs/flowpilot_maintenance_convergence_20260527.md` and the
current new-only surface-removal change. Completed OpenSpec changes were archived,
runtime retention and validation-artifact cleanup stayed read-only, and current
runtime/prompt/install surfaces must not teach old protocol inputs as usable
paths. Focused child modules own PM role-work package disposition helpers,
external event data by phase, and process-contract policy data. The latest
model-test-code alignment report is current when its generated result artifact
matches the source tree.

It covers two ownership surfaces:

- fresh-runtime ownership, where `flowpilot_new.py` owns current formal runs,
  lifecycle guard state, and requested-responsibility packet routing;
- split FlowGuard model scripts backed by focused state, transition,
  invariant, hazard, audit, and strategy helpers as applicable.

The latest singleton-authority pass keeps the model-test-code alignment report
at `867` covered surfaces with `0` gaps and `0` deferred structure splits.

The current router-facade split also has a narrower FlowGuard gate at
`simulations/flowpilot_router_facade_split_model.py`, checked by
`simulations/run_flowpilot_router_facade_split_checks.py`. It covers
PromptStore manifest/hash behavior, prompt-delivery ownership, card-delivery
ownership, Controller action-ledger helper ownership, role-output protocol
helper ownership, coarse runtime/startup/controller/work-packet/event/repair/
route/terminal ownership, upgraded StructureMesh target-structure evidence,
and public-entrypoint preservation. The coarse owner modules currently added for
this gate are:

- `flowpilot_router_runtime_state.py` for bootstrap/run state and low-level
  runtime factories;
- `flowpilot_router_protocol_catalog.py` for schema constants, action/event
  catalogs, system-card tables, gate contracts, and protocol lookup helpers;
- `flowpilot_router_startup_flow.py` for legacy Router startup, bootloader,
  resume, and role-assignment/replacement phase bodies;
- `flowpilot_router_self_interrogation.py` for early understanding checks,
  concise fallback summaries, and self-interrogation report helpers;
- `flowpilot_router_controller_scheduler.py` for Controller scheduler rows,
  receipts, foreground standby, and patrol timer behavior;
- `flowpilot_router_controller_repair.py` for Controller deliverable repair,
  mail-delivery postcondition folding, and router-owned postcondition reclaim;
- `flowpilot_router_action_factory.py` for router action construction,
  dispatch recipient gates, user-send decisions, and action envelope helpers;
- `flowpilot_router_payload_contracts.py` for payload normalization,
  interpretation contracts, startup answer payloads, and role identity helpers;
- `flowpilot_router_work_packets.py` for material, research, current-node
  packet flow, and PM role-work lifecycle;
- `flowpilot_router_events_repair.py` for control blockers, repair
  transactions, and gate-decision validation;
- `flowpilot_router_lifecycle_requests.py` for external lifecycle request
  intake and event queuing;
- `flowpilot_router_event_dispatcher.py` for the external event dispatcher
  body;
- `flowpilot_router_route_artifacts.py` for route diagram/readme/report
  artifact writers and packet-path snapshots;
- `flowpilot_router_route_frontier.py` for route/frontier projection and node
  completion;
- `flowpilot_router_system_cards.py` for system-card body construction,
  delivery contexts, and role card return actions;
- `flowpilot_router_expected_waits.py` for expected-wait records,
  acknowledgement guards, and wait-state rendering;
- `flowpilot_router_terminal_ledger.py` for final ledger, terminal replay,
  closure suite, and terminal reconciliation.

Router runtime regression now uses split background child suites. Run
`python scripts/run_test_tier.py --tier router --background --background-dir tmp/flowguard_background --json`;
the runner starts one hidden bounded supervisor (`router_background_supervisor`)
and writes per-suite artifacts for startup, foreground/controller, packet,
route, terminal, closure, resume, blocker, PM role-work, quality-gate, and
material/modeling domains.
The route domain is also split internally: `router-route` runs focused
route-mutation child suites for draft activation, model-miss triage, acceptance
repair, preconditions, repair transactions, topology, sibling replacement, and
parent backward replay. Aggregate route-mutation coverage is historical
evidence only and is not a new runtime contract.

Known-bad variants for missing owners, duplicate state ownership, missing
facades, removed entrypoints, stale parity, insufficient release evidence,
hidden skipped tests, timeout suites, and background progress without final
artifacts must fail before a maintenance pass can be called complete.
Alignment known-bad variants for missing evidence, stale evidence,
progress-only background evidence, orphan tests, duplicate same-kind evidence,
and model-confidence overclaims must also fail.

## What Has Already Been Decided

- The public project and skill name is `flowpilot`.
- FlowGuard remains the required modeling engine and technical foundation.
- The skill is new. It is not a patch to the old heartbeat skill.
- It is strongly bound to real FlowGuard and the `model-first-function-flow`
  skill.
- It absorbs heartbeat rules but does not hard-depend on the old heartbeat
  skill.
- The project-control directory is `.flowpilot/`.
- Canonical state should be machine-readable JSON/Python/results.
- Markdown files are English summaries derived from canonical state.
- Routes are versioned. Old routes are retained and may be rolled back to only
  if their checkpoints remain valid.
- `self-interrogation` style self-interrogation is a required early gate.
- Formal startup now has a material intake and PM material understanding gate
  after full self-interrogation and runtime role-binding readiness, but before PM
  product-function architecture. It inventories user-provided and
  repository-local materials, records source summaries, authority, freshness,
  contradictions, local skills and host capabilities as candidate-only
  resources, unread or deferred sources, reviewer sufficiency, PM source-claim
  matrix, open questions, complexity, and discovery/cleanup route consequences.
- PM material gaps are now first-class research packages rather than informal
  notes. If reviewed materials are insufficient for product architecture, route
  choice, node acceptance, mechanism understanding, external source confidence,
  or validation, the PM writes a bounded research/evidence package, assigns
  worker execution, requires reviewer direct-source or experiment-output
  checks, and only then absorbs the result into material understanding or
  mutates/blocks the route.
- Formal startup then has a PM-owned product-function architecture gate before
  contract freeze. It captures user tasks, product capabilities, feature
  necessity, display rationale, missing high-value features, negative scope,
  and a functional acceptance matrix.
- Child-skill routing now has a PM-owned selection gate between product
  architecture/capability mapping and child-skill gate extraction. The PM reads
  the local skill inventory and classifies candidate skills as required,
  conditional, deferred, or rejected; child-skill discovery may proceed only
  from PM-selected skills, never from raw local availability.
- PM route drafting now begins with a planning profile. The PM classifies the
  task as interactive UI/product work, software engineering, research writing,
  release delivery, debug/simple repair, or long-running multi-role work before
  drafting nodes. The route must then show profile-appropriate convergence
  loops, horizontal modules, node artifacts, and a self-check that the route is
  not too coarse for the user's stated quality level.
- Selected child skills now require a Skill Standard Contract instead of a
  manifest-only gate list. PM extracts `MUST`, `DEFAULT`, `FORBID`, `VERIFY`,
  `LOOP`, `ARTIFACT`, and `WAIVER` standards with source paths, then maps each
  non-waived standard into route nodes, work packets, reviewer/operator gates,
  and expected artifacts.
- Node acceptance plans and work packets now inherit the Skill Standard
  Contract projection. Worker/FlowGuard operator results must return a Skill Standard
  Result Matrix for inherited standard ids, and reviewers block missing rows,
  manifest-only evidence, or unapproved waivers.
- UI projects now default to the experimental
  `autonomous-concept-ui-redesign` child skill, which now owns the concept-led
  product/design front half internally and composes `frontend-design`,
  `design-iterator`, `design-implementation-reviewer`, image generation when
  needed, and geometry/screenshot QA. The older `concept-led-ui-redesign` skill
  is no longer a FlowPilot dependency.
- Formal FlowPilot routes now use runtime-requested role bindings only for
  responsibilities currently issued by the runtime. Typical requested
  responsibilities include project manager, human-like reviewer,
  FlowGuard operator, and bounded worker-class packet executors. The project
  manager owns route, resume completion runways,
  PM stop signals, repair, and completion decisions; workers remain packet
  executors, not route or node owners.
- Every meaningful FlowPilot scope now has two FlowGuard model gates: a
  development-process model and a product-function model.
- Human-like inspection is now a route mechanism. Blocking inspection findings
  must be interrogated into specific repairable issues. Local defects go through a
  local repair and same-inspector recheck; route-invalidating findings mutate
  the route into repair nodes and close only after repair evidence and
  same-inspector recheck.
- Effective route nodes with children require local parent backward human-like
  replay when composition risk is high or the PM cannot justify a low-risk
  waiver from current evidence. If child-local passes do not compose into the
  parent goal, FlowPilot structurally mutates the route to rework an existing
  child, insert an adjacent sibling child, rebuild the child subtree, or bubble
  impact upward before rerunning the same parent review and recording a PM
  segment decision.
- Generated UI concept targets require two separate gates: source and
  authenticity. Source proves the asset came from `imagegen` or an
  authoritative user reference; authenticity proves the content is an
  independent concept, not an existing screenshot, screenshot variant, desktop
  capture, old route UI, or prior failed evidence with cosmetic changes.
- Manual lifecycle resume is an execution gate, not a status note. When an
  unfinished node exists, `flowpilot_new.py resume --reason manual_resume` must
  load current-run authority and return a concrete foreground duty; Controller
  cannot stop after only writing "continue to the next gate."
- There is no current heartbeat requirement. Nonterminal waiting uses
  foreground duty and patrol refresh from the current ledger. Any controlled
  nonterminal stop records and displays a resume notice; terminal completion
  records a completion notice instead of a resume prompt.
- Human-like inspection now begins with a neutral observation pass before
  judgement. The inspector first records what the artifact, screenshot, output,
  or exercised feature actually appears to be, then compares that observation
  with the frozen contract, product model, and evidence.
- UI, browser, desktop, visual, localization, and interaction review gates now
  require reviewer-owned personal walkthrough evidence. Screenshot QA,
  interaction smoke logs, or worker reports are only pointers. The reviewer
  must personally check reachable controls, clicks/keyboard paths,
  overlap/clipping, whitespace, density, crowding, hierarchy, readability,
  responsive/window fit, aesthetics, and concrete design recommendations, or
  block/request more evidence.
- Blocking review failures now route by issue type. A local defect uses local
  repair with the same reviewer recheck and does not force route mutation. A
  route-invalidating finding forces structural route mutation: the failed child
  remains as failed/superseded history, affected evidence becomes stale, the
  route version and execution frontier change, and FlowPilot either resets the
  existing child, inserts an adjacent repair/regeneration sibling, splits the
  finding into multiple focused children, or rebuilds/bubbles the subtree.
- Pause, restart, and terminal cleanup now require unified lifecycle
  reconciliation across current-run ledger state, execution frontier,
  packet/lease state, lifecycle guard, and foreground-duty evidence.
- Manual lifecycle resume does not restore a fixed role set. It returns the
  current foreground duty; when that duty asks for role work, Controller opens,
  reuses, or replaces only the requested packet responsibility through
  `dispatch-current-role`.
- Runtime-required roles are persistent as responsibilities, but each new
  formal FlowPilot task must receive fresh current-run assignment/lease evidence
  when the user authorizes host-supported role assistance. Prior-route or
  earlier-task `agent_id` values are audit history only, not startup evidence.
  Replacement memory is allowed only for the currently requested responsibility
  and current packet/task boundary.
- Public invocation text should explicitly say: use FlowPilot full protocol,
  including permission for FlowPilot to request additional runtime role
  assistance where the host and current tool policy support it,
  manual lifecycle resume continuation, Runtime/Router startup mechanical
  audit, and PM startup intake release. If requested host role bindings are
  unavailable or not authorized, FlowPilot records a structured stop or blocker
  instead of continuing through a foreground-only route. It blocks when
  the requested current role surface cannot be opened, when the current packet
  responsibility cannot be leased, or when the current mechanical or PM release
  condition cannot be satisfied.
- Role authority is now an explicit protocol gate. Startup self-interrogation,
  product-function architecture synthesis, route advancement, manual lifecycle
  resume, repair strategy, route mutation, and completion require
  project-manager decisions; FlowGuard modelability and model execution
  require the FlowGuard operator; product usefulness challenge,
  human-like observations, judgement, and rechecks require the reviewer. The
  controller may relay, record status, request decisions, and enforce hard stops but may not
  self-approve these gates.
- Every PM, reviewer, and FlowGuard operator approval now has a universal
  adversarial approval baseline. Completion reports, worker reports,
  screenshots, logs, and prior role reports are only pointers. The approving
  role must personally probe the relevant sources or state, test failure
  hypotheses, cite concrete files/screenshots/state fields/commands/results,
  record residual blindspots, and write independent validation evidence before
  approving. Completion-report-only approval is invalid across startup gates,
  material intake, product architecture, child-skill manifests, FlowGuard model
  gates, implementation/human review, composite backward review, final product
  replay, and the final route-wide ledger.
- Human-like reviewer reports now have a concrete Reviewer Independent
  Challenge Gate. The PM review package is only the minimum checklist.
  Reviewer report bodies must include `independent_challenge` with scope
  restatement, explicit and implicit commitments, failure hypotheses,
  task-specific challenge actions, blocking and nonblocking findings,
  pass-or-block decision, reroute request, and waivers. A pass is invalid if
  this object is missing, if the actions are generic instead of task-specific,
  if direct evidence or approved waiver is absent, or if a hard requirement,
  frozen contract item, child-skill standard, quality level, exposed product
  behavior, or core commitment is downgraded into residual risk.
- Terminal completion now requires a PM-owned dynamic route-wide gate ledger
  rebuilt from the current route, not the initial route. The ledger resolves
  effective and superseded nodes, child-skill gates, human-review gates,
  product/process model gates, generated-resource lineage, stale evidence,
  waivers, blockers, and unresolved items. Completion is blocked until
  unresolved count is zero, every generated resource is consumed, included in
  final output, used as evidence, superseded, quarantined, or discarded with
  reason, the human-like reviewer replays the final product backward through
  that ledger, and the PM records ledger-specific completion approval.
- The clean rebuild implements this as a prompt-isolated router/card runtime:
  PM writes `final_route_wide_gate_ledger.json`, the router creates
  `terminal_human_backward_replay_map.json`, the human-like reviewer receives
  `reviewer.final_backward_replay`, and completion/closure remains blocked
  until `reviews/terminal_backward_replay.json` passes. The current runtime
  validates stale evidence, unresolved evidence, pending resources, unresolved
  residual risks, old UI/visual asset reuse, and completion-report-only closure.
  The remaining terminal expansion is a closure-suite lifecycle writer after
  PM closure approval.
- Each formal FlowPilot invocation now creates a fresh
  `.flowpilot/runs/<run-id>/` directory in the target project. Top-level
  `.flowpilot/current.json` and `.flowpilot/index.json` are pointer/catalog
  files only. Continuing old work creates a new run and imports old outputs as
  read-only evidence; old control state, agent IDs, screenshots, icons, or
  route files must not become current state.
- Manual lifecycle resume now trusts the current-run ledger, lifecycle guard,
  foreground duty, execution frontier, packet/lease state, and on-demand role
  assignment records. There is no heartbeat evidence requirement, extra reset
  path, or registry layer.
- Manual lifecycle resume re-enters the packet-gated controller loop through
  `flowpilot_new.py`. The stable launcher loads the active run and packet ledger,
  follows the returned foreground duty, routes existing worker results through
  the runtime, and blocks ambiguous worker state rather than letting Controller
  infer or finish work.
- Material scan, research, and current-node execution now use physical
  packet/result envelopes. Controller may relay envelope metadata only; workers
  open packet bodies, worker results return to PM, PM records a package-result
  disposition, and reviewers inspect PM-built formal gate packages rather than
  raw worker result bodies. PM may complete a node only after the formal
  reviewer node-completion gate passes plus any required parent backward replay
  and PM segment decision. Generalized async FlowGuard operator request/report
  packets remain the next packet-loop expansion.
- The project manager may proactively use FlowGuard as a modeling laboratory
  for uncertain route, repair, feature, product-object, file-format, protocol,
  or validation decisions. The PM writes a structured modeling request, assigns
  the FlowGuard operator, receives
  a modelability-aware report, and then records the route decision.
- FlowGuard modeling requests are now FlowGuard operator-owned async gates when live
  background roles are available. The PM records the request and operator output
  root, the FlowGuard operator authors/runs/interprets the model and writes
  execution provenance, and the controller may only do non-dependent
  preparation while the model gate is pending.
- FlowGuard operator reports are PM decision-support packets, not absolute
  no-risk certificates. The FlowGuard operator must extract model-derived risk tiers,
  PM review-required hotspots, human walkthrough targets, toolchain/model
  improvement suggestions, and a confidence boundary; PM decides whether to
  continue, repair, add evidence, split, mutate, or block.
- FlowPilot now has one user-facing flow diagram for both chat and Cockpit UI:
  a 6-8 stage FlowPilot process view with the current stage highlighted. Raw
  FlowGuard Mermaid graphs are diagnostic exports only and are disabled by
  default. Startup, each new major `flow.json` route-node entry, parent/module
  or leaf route-node entry, PM current-node work brief, route mutation, repair
  return, completion review, and explicit user requests require the chat
  Mermaid when Cockpit is closed. Generated files or display packets alone do
  not count as chat display.
- Role-binding records now separate `role_key`, `display_name`, and
  diagnostic-only `agent_id` so UI and authority checks do not drift when host
  agent names or handles change.
- Formal startup now has no Reviewer startup fact gate and no PM startup
  activation gate. Before any child skill, imagegen, implementation, route
  chunk, or completion work, Runtime/Router must create the current run, seal
  startup input, write startup mechanical audit, write display/status evidence,
  audit current run identity, and either stop/block with a structured reason or
  deliver the sealed `user_intake` packet to PM. The PM then owns the first
  material/intake decision, repair, stop, or route-continuation decision.
  Route-local artifacts without that canonical runtime entry are shadow routes
  to quarantine or supersede.
- Formal startup now begins with a single-option pre-banner gate. On
  `Use FlowPilot` / `使用开始`, the assistant asks for the user's work request and
  whether FlowPilot may use mandatory background or parallel collaboration,
  then the assistant response must stop immediately and wait for the user's
  reply. The startup banner, route writes, child skills, role bindings,
  imagegen, and implementation are blocked until a later user reply explicitly
  acknowledges that required background-collaboration capability and Runtime
  records both the stop-and-wait evidence and banner-after-answers evidence.
  Removed startup choices are recorded as fixed defaults: manual continuation
  and chat route signs.
- Long operations no longer carry a FlowPilot stale-heartbeat wrapper; use
  ordinary checkpoints, logs, and host tool status for bounded-operation
  evidence.
- FlowPilot now records PM-owned skill-improvement observations separately from
  current project acceptance. Roles may note protocol/template/tooling issues
  during node or review work, PM writes a final
  `flowpilot_skill_improvement_report.json`, and those observations never block
  current project completion or require root-repo fixes inside the active run.
- Controller has a development-mode break-glass repair lane only for FlowPilot
  control-plane failures where normal Router/PM/control-blocker/packet repair
  cannot produce a legal next action. The full playbook is
  `skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`.
  Repeated Controller table/monitor/patrol surfaces show a short reminder, and
  run-scoped incidents/patches live under
  `.flowpilot/runs/<run-id>/controller_break_glass/`. This lane never grants
  target-project work, sealed-body access, gate approval, route mutation,
  acceptance changes, publication, deployment, or secret handling.

## Model-Backed Rules Found During Preflight

FlowGuard caught and fixed these design issues:

1. High-risk gates must not overlap active formal chunks.
2. `helper report returned` is not enough for completion; the controller must
   merge and verify the result.
3. Helper opportunity checks belong at child-node entry. Parent/module review
   may identify likely helper work but must not open role bindings or transfer
   node ownership.
4. Helper scope checking must be separate from reuse-or-open assignment, and a
   suitable idle role binding must be reused before opening a new one.
5. Completion checks must use historical gate evidence, not only a helper that
   applies to `running` state.
6. Technical evidence such as screenshot existence, app launch, or test pass
   cannot substitute for product-function modeling and human-like inspection.
7. Child-local passes cannot substitute for local parent backward replay at
   every structurally enumerated route node with children.
8. Structural route repair must invalidate stale implementation or child
   evidence before the changed route is rechecked and work resumes.
9. Source-only concept acceptance is unsafe. A generated file can still be a
   contaminated or reused screenshot-like asset, so concept authenticity must
   be inspected independently and failures must route back to clean concept
   regeneration.
10. A continuation turn that only records a future next-step decision is a
    no-progress failure. The current unfinished gate must be executed or blocked
    in the continuation turn.
11. Review failure cannot be treated as "evidence exists but pass is soft."
    It is a route mutation that invalidates stale child evidence and redirects
    the frontier to a reset or newly inserted repair child.
12. Lifecycle state can drift across multiple authorities. Pause, restart, and
    terminal closure must scan and reconcile all of them before claiming the
    route lifecycle state is clean.
13. The current reviewer decision is not enough history. Blocking review
    findings need persistent block evidence so later repair, recheck, route
    mutation, and completion closure can still trace why the route changed.
14. Gate existence is not actor authority. A model check, review pass, route
    mutation, or completion decision must record the correct approving role,
    and route repair must invalidate stale approvals together with stale
    product evidence.
15. Live helper responsibility continuity is not reliable enough to be a source
    of truth after a wait or manual resume. Role continuity is audit context;
    replacement roles must be explicitly assigned and leased for the currently
    requested packet responsibility before they can approve gates.
16. Product-function models and final feature reviews cannot substitute for a
    pre-contract PM product-function architecture package. Without feature
    necessity, display rationale, missing-feature review, negative scope, and
    a functional acceptance matrix, FlowPilot may freeze a contract around
    unnecessary UI text or miss obvious high-value functions.
17. A PM product-function architecture package cannot substitute for material
    intake when source materials are non-trivial. The controller must
    inventory and summarize materials, the reviewer must approve sufficiency,
    and the PM must record material understanding and complexity before product
    architecture or route decisions.
18. Local node checks and the initial route checklist cannot substitute for a
    PM-built final route-wide gate ledger. After route mutation or repair,
    terminal completion must rescan the current route, collect all effective
    child-skill and review gates, check stale evidence, explain superseded
    nodes, and rerun human-like backward replay before PM completion approval.
19. The final backward replay must be a terminal human acceptance pass, not
    merely a ledger audit. The PM builds an ordered replay map; the reviewer
    starts from the delivered product, then manually checks root acceptance,
    parent/module nodes, and leaf nodes against current product behavior and
    node acceptance plans. After every segment, PM records continue/repair/stop
    decisions. A repair invalidates affected evidence and normally restarts the
    final review from the delivered product; narrower impacted-ancestor reruns
    require a PM reason.
20. Asking the three startup questions is not a soft prompt. It is a hard
    pause boundary: if FlowPilot keeps working in the same response after the
    questions, any later startup evidence is invalid and the PM must not open
    `work_beyond_startup_allowed`.
21. Generated-resource existence is not useful output by itself. Concept
    images, visual assets, screenshots, route diagrams, model reports, and
    similar generated artifacts must be consumed by implementation/QA/final
    output or explicitly superseded, quarantined, or discarded with reason in
    the final ledger before completion can claim zero unresolved work.
20. A new formal FlowPilot task cannot treat historical role `agent_id` values
    as current role-binding evidence. The reviewer must check that every
    runtime-requested role binding, when authorized, was explicitly assigned and
    leased for the current packet responsibility after the current startup
    answers and current route allocation. Counting role records is insufficient
    if any ID was resumed from a prior route or older task.
21. A new formal FlowPilot invocation must create a new target-project run
    directory under `.flowpilot/runs/<run-id>/`. Top-level `.flowpilot`
    control files are forbidden except `current.json` and `index.json`.
    Continuing prior work imports old evidence into the new run; it never
    resumes old control state as current state.

## Current Implementation State

- The main skill launcher lives at `skills/flowpilot/SKILL.md`. It is now
  intentionally small and delegates formal startup to
  `skills/flowpilot/assets/flowpilot_new.py`.
- Prompt-isolated runtime cards live under
  `skills/flowpilot/assets/runtime_kit/` and are listed in
  `skills/flowpilot/assets/runtime_kit/manifest.json`.
- Manual lifecycle resume now uses `flowpilot_new.py resume --reason
  manual_resume` and the returned lifecycle guard plus foreground duty. The
  Controller loads current-run ledger, packet/lease state, active blockers, and
  status projection without reading sealed bodies or inferring progress from
  chat history. Role work is opened only through the current
  `dispatch-current-role` path for the requested packet responsibility; fixed
  role-set restoration and heartbeat recovery are not current runtime
  mechanisms.
- `flowpilot_new.py` now drives the fresh current-run packet loop through the
  physical envelope/body system. It requires route activation, current-node
  packet registration, runtime dispatch preflight, packet ledger checks,
  Controller envelope-only relay, worker result relay to PM, PM
  package-result disposition, reviewer audit, and system-owned validation and
  closure before PM node completion.
- Route activation and review-block repair now write run-scoped route/frontier
  state. `execution_frontier.json` tracks the active node, completed nodes, and
  route-mutation repair state; mutation records are written before new repair
  work can proceed.
- Route replanning now has an explicit phase boundary. Planning/root/parent
  node-entry gaps before executable child work must be handled by route
  replanning or ordinary node expansion, not by creating a repair node. Route
  activation also rejects active nodes that are not present in the reviewed
  route draft. The policy is modeled in
  `simulations/flowpilot_route_replanning_policy_model.py`.
- `docs/flowpilot_clean_rebuild_plan.md` is retained as historical planning
  context. Current install readiness no longer depends on old-protocol
  equivalence checklists; `scripts/check_install.py` verifies the current
  runtime card manifest, packet schema alignment, model result artifacts, and
  repository-owned install surfaces.
- FlowGuard coverage now includes prompt isolation, manual lifecycle resume,
  on-demand role assignment, and current-node/router-loop models:
  `simulations/prompt_isolation_model.py`,
  `simulations/flowpilot_resume_model.py`, and
  `simulations/flowpilot_router_loop_model.py`.
- Terminal FlowGuard coverage governance now has a focused model and runtime
  gate: `simulations/flowpilot_terminal_flowguard_coverage_model.py` and
  `simulations/run_flowpilot_terminal_flowguard_coverage_checks.py`. PM final
  ledger creation requires a current PM-accepted
  `flowguard_terminal_coverage_report`, Reviewer terminal backward replay must
  include the `flowguard-coverage-governance` segment, and PM closure rechecks
  the same report instead of accepting scattered node-level FlowGuard evidence,
  stale reports, progress-only reports, unresolved blockers, or pending PM
  suggestions.
- Control-plane event-contract coverage lives in
  `simulations/flowpilot_event_contract_model.py`. It rejects any persisted
  role wait that contains an internal Router action, unknown event string,
  direct ACK/check-in event, false-prerequisite event, success-only material
  repair table, duplicate PM repair side effect, or post-write-only cleanup
  path.
- Event capability registry coverage lives in
  `simulations/flowpilot_event_capability_registry_model.py`. It verifies that
  registered external events are also currently executable for the active node
  kind, repair origin, target role, wait/rerun/outcome usage, and distinct
  success/blocker/protocol-blocker repair rows.
- Control transaction registry coverage lives in
  `simulations/flowpilot_control_transaction_registry_model.py`.
  `skills/flowpilot/assets/runtime_kit/control_transaction_registry.json`
  is the unified registry for route progression, packet dispatch, result
  absorption, reviewer gates, control-blocker repair, control-plane reissue,
  and route mutation commits.
- The preserved historical FlowPilot backup lives under
  `backups/flowpilot-20260504-second-backup-20260504-195841/` with matching
  zip archive. It is marked as a preserved backup and must not be deleted by
  cleanup.
- Reusable project-control templates live at `templates/flowpilot/`.
- FlowGuard regression models live at `simulations/`.
- Self-check and smoke scripts live at `scripts/`.
- `scripts/flowpilot_lifecycle.py` scans lifecycle authorities before pause,
  restart, or terminal cleanup and writes `.flowpilot/runs/<run-id>/lifecycle/` evidence when
  requested.
- Current project progress is tracked in `.flowpilot/current.json` plus the
  active `.flowpilot/runs/<run-id>/` directory.
- Runtime closure hardening now writes explicit FlowGuard operator request lifecycle,
  continuation quarantine, final user report, and route-display refresh
  artifacts. The focused model and checker are
  `simulations/flowpilot_runtime_closure_model.py` and
  `simulations/run_flowpilot_runtime_closure_checks.py`.
- Recursive route and terminal closure reconciliation hardening now prevents
  sibling parent/module skips and records defect-ledger, role-memory, and
  continuation-quarantine reconciliation in the final ledger and closure suite.
  The focused model and checker are
  `simulations/flowpilot_recursive_closure_reconciliation_model.py` and
  `simulations/run_flowpilot_recursive_closure_reconciliation_checks.py`.
- Route mutation repair/replacement hardening now supports explicit
  `sibling_branch_replacement` topology, affected sibling nodes, replay-scope
  declaration, stale sibling evidence handling, route-sign replacement/replay
  projection, and old current-node packet supersession before fresh route
  recheck. The focused model and checker are
  `simulations/flowpilot_route_mutation_activation_model.py` and
  `simulations/run_flowpilot_route_mutation_activation_checks.py`.
- The Python structure simplification passes keep current public entrypoints and
  protocol semantics stable while reducing several heavy active files.
  The internal router facade remains a source-level diagnostic entrypoint, while event dispatch,
  event finalization, event intake, Controller action providers, Controller
  action handlers, route activation/mutation, and legacy Router resume helpers now
  live in focused modules:
  `flowpilot_router_events.py`,
  `flowpilot_router_event_intake.py`,
  `flowpilot_router_action_providers.py`,
  `flowpilot_router_action_handlers.py`,
  `flowpilot_router_route.py`, and
  `flowpilot_router_resume.py`.
- The follow-up router-facade prompt/store pass keeps selected prompt text under
  `skills/flowpilot/assets/runtime_kit/prompts/` and loads it through
  `flowpilot_prompt_store.py`. Router prompt delivery, card delivery,
  ACK return settlement, Controller action-ledger helper, role-output protocol
  helper, event identity/idempotency, and daemon lock/status/tick runtime code
  now lives in `flowpilot_router_prompt_delivery.py`,
  `flowpilot_router_card_delivery.py`,
  `flowpilot_router_card_returns.py`,
  `flowpilot_router_controller_ledger.py`,
  `flowpilot_router_role_io_protocol.py`,
  `flowpilot_router_event_identity.py`, and
  `flowpilot_router_daemon_runtime.py`. Bootloader/startup, external event
  dispatch settlement, control-blocker repair transactions, PM role-work,
  packet dispatch, route frontier, and terminal ledger helpers remain deferred
  until their state-owner contracts are independently modeled.
- `packet_runtime.py` remains the public facade and delegates schema, path,
  contract, ledger, relay, current-packet-holder, session, and reviewer responsibilities
  to `packet_runtime_*` helper modules.
- `role_output_runtime.py` remains the public facade and delegates schema,
  contract, progress, envelope, and CLI responsibilities to
  `role_output_runtime_*` helper modules.
- `scripts/check_install.py` remains the install self-check entrypoint and delegates
  check groups to `scripts/install_checks/`.
- The Meta and Capability FlowGuard parent models now keep short `apply`
  orchestration methods and move their previous monolithic bodies into phase
  helpers. Their regression runners are layered: the default command validates
  bounded thin-parent evidence for routine confidence, `--full` validates a
  fast layered full-parent proof recorded in
  `simulations/meta_layered_full_results.json` or
  `simulations/capability_layered_full_results.json`. Long full regressions
  should use the background artifacts under
  `tmp/flowguard_background/run_meta_checks.*` and
  `tmp/flowguard_background/run_capability_checks.*`.
- Router runtime tests now have domain entry files covering all `304` aggregate
  runtime tests exactly once, including resume, cards, packets, route mutation,
  startup daemon, dispatch gate, Controller, ACK/return, terminal, closure,
  bootstrap/CLI, foreground, PM role work, material/modeling, control blockers,
  and quality gates. `tests/test_flowpilot_router_runtime.py` remains available
  as the source of the shared test case class.
- `scripts/run_test_tier.py` hides Windows subprocess windows for both
  background children and foreground child commands. Use the background
  artifact files for completion evidence instead of relying on visible console
  windows.
- Child FlowGuard models that still produced high maintenance friction now keep
  facade entrypoints while delegating state, transitions, invariants, hazards,
  and audit helpers to focused modules. This pass covered control-plane
  friction, router-loop, and daemon reconciliation. The parent hierarchy now
  consumes thin child evidence for daemon startup/locks, Controller actions,
  waits/liveness, and terminal/projection contracts.
- A v0.9.7 behavior repair discovered during simplification validates explicit
  event-envelope references against the current Router wait before startup or
  current-scope reconciliation can return a recoverable wait. The event-contract
  model includes the corresponding
  `explicit_envelope_outside_wait_returns_reconciliation_wait` hazard.

## Remaining Work

Before public release:

1. Build a production replay adapter for the abstract resume and router-loop
   FlowGuard models if they are promoted from design models to conformance
   checks.
2. Review the README and docs for final GitHub presentation after any parallel
   AI work is merged.
3. Fill in final public FlowGuard source URLs if needed.
4. Run privacy and public-boundary review before publishing.
5. Add native Cockpit consumption of `route_state_snapshot.json` when UI work
   resumes.

## Validation Commands

Run:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python simulations/run_meta_checks.py --full --fast
python simulations/run_capability_checks.py --full --fast
python simulations/run_prompt_isolation_checks.py
python simulations/run_flowpilot_resume_checks.py
python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json
python simulations/run_flowpilot_control_plane_friction_checks.py --json-out simulations/flowpilot_control_plane_friction_results.json
python simulations/run_flowpilot_event_contract_checks.py --json-out simulations/flowpilot_event_contract_results.json
python simulations/run_flowpilot_event_capability_registry_checks.py --json-out simulations/flowpilot_event_capability_registry_results.json
python simulations/run_flowpilot_control_transaction_registry_checks.py --json-out simulations/flowpilot_control_transaction_registry_results.json
python simulations/run_flowpilot_model_mesh_checks.py --json-out simulations/flowpilot_model_mesh_results.json
python simulations/run_flowpilot_planning_quality_checks.py --json-out simulations/flowpilot_planning_quality_results.json
python simulations/run_flowpilot_route_replanning_policy_checks.py --json-out simulations/flowpilot_route_replanning_policy_results.json
python simulations/run_flowpilot_runtime_closure_checks.py --json-out simulations/flowpilot_runtime_closure_results.json
python simulations/run_flowpilot_recursive_closure_reconciliation_checks.py --json-out simulations/flowpilot_recursive_closure_reconciliation_results.json
python simulations/run_flowpilot_route_mutation_activation_checks.py --json-out simulations/flowpilot_route_mutation_activation_results.json
python simulations/run_flowpilot_singleton_identity_checks.py --json-out simulations/flowpilot_singleton_identity_results.json
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
python simulations/run_flowpilot_similarity_convergence_checks.py --json-out simulations/flowpilot_similarity_convergence_results.json
python simulations/run_flowpilot_model_maturation_checks.py --json-out simulations/flowpilot_model_maturation_results.json
python simulations/run_flowpilot_blocker_repair_information_flow_checks.py --json-out simulations/flowpilot_blocker_repair_information_flow_results.json
python simulations/run_flowpilot_project_control_information_flow_checks.py --json-out simulations/flowpilot_project_control_information_flow_results.json
python simulations/run_flowpilot_information_flow_alignment_checks.py --json-out simulations/flowpilot_information_flow_alignment_results.json
python scripts/check_install.py
python scripts/smoke_flowpilot.py
```

If any fail, fix the model, protocol, templates, or checks before continuing.
