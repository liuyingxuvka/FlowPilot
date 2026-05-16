# Handoff

## Purpose

Build and maintain a Codex skill named `flowpilot`.

FlowPilot lets an AI agent manage a substantial software project as a
model-backed autopilot:

1. interrogate its understanding before freezing a contract;
2. create persistent project-control state under `.flowpilot/`;
3. require material intake and PM material understanding before product design;
4. require a PM-owned product-function architecture before contract freeze;
5. model the project-control route with FlowGuard;
6. route to specialized capabilities at explicit nodes;
7. execute bounded chunks;
8. verify each chunk before moving on;
9. update the model and route when new facts invalidate the current route;
10. create a fresh six-agent crew for each new formal FlowPilot task, with a
  project manager as route-decision and completion-runway authority and worker
  agents limited to bounded sidecar tasks;
11. finish only after evidence proves the frozen contract is met.

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
- `grill-me` style self-interrogation is a required early gate.
- Formal startup now has a material intake and PM material understanding gate
  after full self-interrogation and six-agent crew recovery, but before PM
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
  non-waived standard into route nodes, work packets, reviewer/officer gates,
  and expected artifacts.
- Node acceptance plans and work packets now inherit the Skill Standard
  Contract projection. Worker/officer results must return a Skill Standard
  Result Matrix for inherited standard ids, and reviewers block missing rows,
  manifest-only evidence, or unapproved waivers.
- UI projects now default to the experimental
  `autonomous-concept-ui-redesign` child skill, which now owns the concept-led
  product/design front half internally and composes `frontend-design`,
  `design-iterator`, `design-implementation-reviewer`, image generation when
  needed, and geometry/screenshot QA. The older `concept-led-ui-redesign` skill
  is no longer a FlowPilot dependency.
- Formal FlowPilot routes now use a persistent six-agent crew: project
  manager, human-like reviewer, process FlowGuard officer, product FlowGuard
  officer, worker A, and worker B. The project manager owns route,
  heartbeat-resume completion runways, PM stop signals, repair, and completion
  decisions; workers remain bounded sidecars, not route or node owners.
- Every meaningful FlowPilot scope now has two FlowGuard model gates: a
  development-process model and a product-function model.
- Human-like inspection is now a route mechanism. Blocking inspection findings
  must be grilled into specific repairable issues. Local defects go through a
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
- Heartbeat resume is an execution gate, not a status note. When an unfinished
  node exists, the heartbeat must load the persisted frontier, execute the
  current subnode/gate or record a concrete blocker, and cannot stop after only
  writing "continue to the next gate."
- Heartbeat is optional host capability. Unsupported hosts run in
  `manual-resume` mode from the same `.flowpilot/` state/frontier/crew-memory
  evidence and must not require heartbeat automation.
  Any controlled nonterminal stop records and displays a resume notice; terminal
  completion records a completion notice instead of a resume prompt.
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
  reconciliation across Codex heartbeat automations, local state, execution
  frontier, and heartbeat/manual-resume evidence.
- Heartbeat recovery now restores or replaces the six-agent crew before asking
  the project manager for a completion-oriented runway from the current
  position to project completion. The controller no longer decides route
  advancement directly from the frontier, and it must replace the visible plan
  projection from each PM runway instead of working from a one-step gate.
- The six-agent crew is persistent as roles, but each new formal FlowPilot task
  must receive a fresh live background-agent cohort when the user authorizes
  background agents. FlowPilot writes compact per-role memory packets under
  `.flowpilot/runs/<run-id>/crew_memory/`; heartbeat and manual resume may load
  and resume stored agent ids only when they belong to the same active
  task-born cohort.
  Prior-route or earlier-task `agent_id` values are audit history only, not
  startup evidence. Replacement from memory is allowed only inside same-task
  continuation or after explicit user fallback approval. The project manager is
  asked for a runway only after crew memory rehydration and the
  live-subagent/fallback startup decision are recorded.
- Public invocation text should explicitly say: use FlowPilot full protocol,
  including permission to start the standard six background subagents where the
  host and current tool policy permit them, heartbeat/manual-resume
  continuation, and the startup hard gate. If live subagents are unavailable or
  not yet authorized, FlowPilot pauses and asks. It continues with
  single-agent six-role continuity only after explicit fallback approval; it
  blocks when neither live agents nor user-authorized fallback are recorded,
  when a required role cannot be recovered, or when a hard gate cannot be
  satisfied.
- Role authority is now an explicit protocol gate. Startup self-interrogation,
  product-function architecture synthesis, route advancement, heartbeat
  resume, repair strategy, route mutation, and completion require
  project-manager decisions; process models require the process FlowGuard
  officer; product-function architecture modelability and product-function
  models require the product FlowGuard officer; product usefulness challenge,
  human-like observations, judgement, and rechecks require the reviewer. The
  controller may relay, record status, request decisions, and enforce hard stops but may not
  self-approve these gates.
- Every PM, reviewer, and FlowGuard officer approval now has a universal
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
- Heartbeat/manual-resume lifecycle state now trusts current-run `state.json`,
  latest heartbeat evidence, execution frontier, and crew memory. There is no
  extra reset path or registry layer.
- Heartbeat/manual-resume now re-enters the packet-gated controller loop. The
  stable launcher loads the active run and packet ledger, restores roles, asks
  PM for `PM_DECISION` with `controller_reminder`, runs router direct-dispatch
  preflight before worker execution, routes existing worker results to PM for
  package-result disposition, and blocks ambiguous worker state for PM recovery
  rather than letting Controller infer or finish work.
- Material scan, research, and current-node execution now use physical
  packet/result envelopes. Controller may relay envelope metadata only; workers
  open packet bodies, worker results return to PM, PM records a package-result
  disposition, and reviewers inspect PM-built formal gate packages rather than
  raw worker result bodies. PM may complete a node only after the formal
  reviewer node-completion gate passes plus any required parent backward replay
  and PM segment decision. Generalized async FlowGuard officer request/report
  packets remain the next packet-loop expansion.
- The project manager may proactively use FlowGuard as a modeling laboratory
  for uncertain route, repair, feature, product-object, file-format, protocol,
  or validation decisions. The PM writes a structured modeling request, assigns
  the process FlowGuard officer, product FlowGuard officer, or both, receives
  a modelability-aware report, and then records the route decision.
- FlowGuard modeling requests are now officer-owned async gates when live
  background roles are available. The PM records the request and officer output
  root, the matching officer authors/runs/interprets the model and writes
  execution provenance, and the controller may only do non-dependent
  preparation while the model gate is pending.
- FlowGuard officer reports are PM decision-support packets, not absolute
  no-risk certificates. The officers must extract model-derived risk tiers,
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
- Crew records now separate `role_key`, `display_name`, and diagnostic-only
  `agent_id` so UI and authority checks do not drift when host agent names or
  handles change.
- Formal startup now has a PM-owned startup activation gate. Before any child
  skill, imagegen, implementation, route chunk, or completion work, the
  human-like reviewer must personally check real state/frontier/route,
  six-role crew ledger, role memory packets, live-agent freshness for the
  current task, continuation, heartbeat/manual-resume lifecycle, and
  cleanup evidence, current run pointer/index evidence, and prior-work import
  boundary when continuing, then write
  `.flowpilot/runs/<run-id>/startup_review/latest.json` as a factual report.
  The PM is the only role that may open
  `.flowpilot/runs/<run-id>/startup_pm_gate/latest.json` and set
  `work_beyond_startup_allowed: true`; there is no third startup opener or
  runtime startup-check script. Route-local artifacts without that canonical match
  are shadow routes to quarantine or supersede.
- Formal startup now begins with a three-question pre-banner gate. On
  `Use FlowPilot` / `使用开始`, the assistant asks for background-agent
  permission, scheduled-continuation permission, and whether to open Cockpit UI
  or use chat route signs, then the assistant response must stop immediately and
  wait for the user's reply. The startup banner, route writes, Cockpit launch,
  child skills, subagents, heartbeat probes, imagegen, and implementation are
  blocked until a later user reply explicitly answers all three questions and
  `startup_activation.startup_questions` records both the stop-and-wait
  evidence and banner-after-answers evidence.
- Long operations no longer carry a FlowPilot stale-heartbeat wrapper; use
  ordinary checkpoints, logs, and host tool status for bounded-operation
  evidence.
- FlowPilot now records PM-owned skill-improvement observations separately from
  current project acceptance. Roles may note protocol/template/tooling issues
  during node or review work, PM writes a final
  `flowpilot_skill_improvement_report.json`, and those observations never block
  current project completion or require root-repo fixes inside the active run.

## Model-Backed Rules Found During Preflight

FlowGuard caught and fixed these design issues:

1. High-risk gates must not overlap active formal chunks.
2. `sidecar report returned` is not enough for completion; the controller must
   merge and verify the result.
3. Subagent opportunity checks belong at child-node entry. Parent/module review
   may identify likely helper work but must not spawn subagents or transfer node
   ownership.
4. Sidecar scope checking must be separate from reuse-or-spawn assignment, and a
   suitable idle subagent must be reused before spawning a new one.
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
15. Live subagent continuity is not reliable enough to be a source of truth
    after heartbeat sleep or manual resume. Role continuity must be persisted
    through structured role memory packets; replacement roles must be seeded
    from those packets before they can approve gates.
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
    as the current six live background agents. The reviewer must check that the
    six live role-bearing subagents, when authorized, were freshly spawned
    after the current startup answers and current route allocation. Counting
    six role records is insufficient if any ID was resumed from a prior route
    or older task.
21. A new formal FlowPilot invocation must create a new target-project run
    directory under `.flowpilot/runs/<run-id>/`. Top-level `.flowpilot`
    control files are forbidden except `current.json` and `index.json`.
    Continuing prior work imports old evidence into the new run; it never
    resumes old control state as current state.

## Current Implementation State

- The main skill launcher lives at `skills/flowpilot/SKILL.md`. It is now
  intentionally small and delegates formal startup to
  `skills/flowpilot/assets/flowpilot_router.py`.
- Prompt-isolated runtime cards live under
  `skills/flowpilot/assets/runtime_kit/` and are listed in
  `skills/flowpilot/assets/runtime_kit/manifest.json`.
- Resume re-entry now has explicit Controller and PM system cards:
  `controller.resume_reentry` and `pm.resume_decision`. The Controller loads
  current-run state, frontier, packet ledger, and crew memory into
  `continuation/resume_reentry.json` without reading sealed bodies or inferring
  progress from chat history; ambiguous resume state blocks for PM recovery.
- `flowpilot_router.py` now drives the current-node packet loop through the
  physical `packet_runtime` envelope/body system. It requires route activation,
  current-node packet registration, router direct-dispatch preflight, packet
  ledger checks, Controller envelope-only relay, worker result relay to PM,
  PM package-result disposition, and a reviewer formal node-completion audit
  before PM node completion.
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
- `docs/flowpilot_clean_rebuild_plan.md` and
  `docs/legacy_to_router_equivalence.json` are the current rebuild plan and
  old-protocol equivalence checklist. `scripts/check_install.py` verifies both
  documents, the runtime card manifest, packet schema alignment, resume model
  results, and router-loop model results.
- FlowGuard coverage now includes prompt isolation, heartbeat/manual resume,
  and current-node/router-loop models:
  `simulations/prompt_isolation_model.py`,
  `simulations/flowpilot_resume_model.py`, and
  `simulations/flowpilot_router_loop_model.py`.
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
  route mutation, and legacy reconcile commits.
- The second legacy FlowPilot backup lives under
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
- Runtime closure hardening now writes explicit officer request lifecycle,
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

## Remaining Work

Before public release:

1. Extend repair/mutation traversal beyond the current active subtree into full
   branch/sibling replacement policy validation. Basic recursive parent/module
   entry and terminal closure reconciliation are now runtime-backed.
2. Build a production replay adapter for the abstract resume and router-loop
   FlowGuard models if they are promoted from design models to conformance
   checks.
3. Review the README and docs for final GitHub presentation.
4. Fill in final public FlowGuard source URLs if needed.
5. Run privacy and public-boundary review before publishing.

## Validation Commands

Run:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
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
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

If any fail, fix the model, protocol, templates, or checks before continuing.
