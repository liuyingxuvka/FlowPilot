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
10. create or restore a persistent six-agent crew for formal routes, with a
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
  contradictions, unread or deferred sources, reviewer sufficiency, PM
  source-claim matrix, open questions, complexity, and discovery/cleanup route
  consequences.
- Formal startup then has a PM-owned product-function architecture gate before
  contract freeze. It captures user tasks, product capabilities, feature
  necessity, display rationale, missing high-value features, negative scope,
  and a functional acceptance matrix.
- UI projects conditionally route through `concept-led-ui-redesign` and
  `frontend-design`, followed by rendered screenshot QA and divergence review.
- Formal FlowPilot routes now use a persistent six-agent crew: project
  manager, human-like reviewer, process FlowGuard officer, product FlowGuard
  officer, worker A, and worker B. The project manager owns route,
  heartbeat-resume completion runways, PM stop signals, repair, and completion
  decisions; workers remain bounded sidecars, not route or node owners.
- Every meaningful FlowPilot scope now has two FlowGuard model gates: a
  development-process model and a product-function model.
- Human-like inspection is now a route mechanism. Blocking inspection findings
  must be grilled into specific repairable issues, mutate the route into
  repair nodes, and close only after repair evidence and same-inspector recheck.
- Every non-leaf parent/module/group now requires composite backward
  human-like review before closure. If child-local passes do not compose into
  the parent goal, FlowPilot structurally mutates the route to rework an
  existing child, insert an adjacent sibling child, rebuild the child subtree,
  or bubble impact upward before rerunning the parent review.
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
  evidence and must not require heartbeat/watchdog/global-supervisor automation.
  Any controlled nonterminal stop records and displays a resume notice; terminal
  completion records a completion notice instead of a resume prompt.
- Human-like inspection now begins with a neutral observation pass before
  judgement. The inspector first records what the artifact, screenshot, output,
  or exercised feature actually appears to be, then compares that observation
  with the frozen contract, product model, and evidence.
- Blocking review failures now force structural route mutation. The failed
  child remains as failed/superseded history, affected evidence becomes stale,
  the route version and execution frontier change, and FlowPilot either resets
  the existing child, inserts an adjacent repair/regeneration sibling, splits
  the finding into multiple focused children, or rebuilds/bubbles the subtree.
- Pause, restart, and terminal cleanup now require unified lifecycle
  reconciliation across Codex automations, global supervisor records, Windows
  scheduled tasks, local state, execution frontier, and watchdog evidence.
  Disabled Windows FlowPilot tasks are still residual objects until
  unregistered or explicitly waived.
- Heartbeat recovery now restores or replaces the six-agent crew before asking
  the project manager for a completion-oriented runway from the current
  position to project completion. The main executor no longer decides route
  advancement directly from the frontier, and it must replace the visible plan
  projection from each PM runway instead of working from a one-step gate.
- The six-agent crew is persistent as roles, and six live background subagents
  are the default formal startup target where the host/tool policy permits
  them. FlowPilot writes compact per-role memory packets under
  `.flowpilot/crew_memory/`; heartbeat and manual resume load those packets,
  try to resume stored agent ids when possible, and replace unavailable roles
  from memory only after explicit user fallback approval. The project manager
  is asked for a runway only after crew memory rehydration and the
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
  main executor may draft, run tools, integrate, and report but may not
  self-approve these gates.
- Terminal completion now requires a PM-owned dynamic route-wide gate ledger
  rebuilt from the current route, not the initial route. The ledger resolves
  effective and superseded nodes, child-skill gates, human-review gates,
  product/process model gates, generated-resource lineage, stale evidence,
  waivers, blockers, and unresolved items. Completion is blocked until
  unresolved count is zero, every generated resource is consumed, included in
  final output, used as evidence, superseded, quarantined, or discarded with
  reason, the human-like reviewer replays the final product backward through
  that ledger, and the PM records ledger-specific completion approval.
- Watchdog decisions now trust only local `state.json`, latest heartbeat
  evidence, and `.flowpilot/busy_lease.json`. Frontier, lifecycle, automation,
  and global records are drift diagnostics; live subagent busy state is not a
  supported watchdog source.
- The project manager may proactively use FlowGuard as a modeling laboratory
  for uncertain route, repair, feature, product-object, file-format, protocol,
  or validation decisions. The PM writes a structured modeling request, assigns
  the process FlowGuard officer, product FlowGuard officer, or both, receives
  a modelability-aware report, and then records the route decision.
- FlowPilot now has one user-facing flow diagram for both chat and Cockpit UI:
  a 6-8 stage FlowPilot process view with the current stage highlighted. Raw
  FlowGuard Mermaid graphs are diagnostic exports only and are disabled by
  default. Route or key-node changes make the previous user flow diagram stale
  until it is refreshed from the rechecked route and execution frontier.
- Crew records now separate `role_key`, `display_name`, and diagnostic-only
  `agent_id` so UI and authority checks do not drift when host agent names or
  handles change.
- Formal startup now has a startup activation hard gate. Before any child
  skill, imagegen, implementation, route chunk, or completion work, state,
  execution frontier, active route, six-role crew ledger, role memory packets,
  and continuation evidence must agree on the same active nonterminal route.
  `scripts/flowpilot_startup_guard.py --record-pass` writes
  `.flowpilot/startup_guard/latest.json`; route-local artifacts without that
  canonical match are shadow routes to quarantine or supersede.
- Long operations now have an explicit busy-lease wrapper helper:
  `scripts/flowpilot_run_with_busy_lease.py`.

## Model-Backed Rules Found During Preflight

FlowGuard caught and fixed these design issues:

1. High-risk gates must not overlap active formal chunks.
2. `sidecar report returned` is not enough for completion; the main agent must
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
7. Child-local passes cannot substitute for composite backward review at every
   non-leaf parent/module/group closure.
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
    intake when source materials are non-trivial. The main executor must
    inventory and summarize materials, the reviewer must approve sufficiency,
    and the PM must record material understanding and complexity before product
    architecture or route decisions.
18. Local node checks and the initial route checklist cannot substitute for a
    PM-built final route-wide gate ledger. After route mutation or repair,
    terminal completion must rescan the current route, collect all effective
    child-skill and review gates, check stale evidence, explain superseded
    nodes, and rerun human-like backward replay before PM completion approval.
19. Generated-resource existence is not useful output by itself. Concept
    images, visual assets, screenshots, route diagrams, model reports, and
    similar generated artifacts must be consumed by implementation/QA/final
    output or explicitly superseded, quarantined, or discarded with reason in
    the final ledger before completion can claim zero unresolved work.

## Current Implementation State

- The main skill lives at `skills/flowpilot/SKILL.md`.
- Reusable project-control templates live at `templates/flowpilot/`.
- FlowGuard regression models live at `simulations/`.
- Self-check and smoke scripts live at `scripts/`.
- `scripts/flowpilot_lifecycle.py` scans lifecycle authorities before pause,
  restart, or terminal cleanup and writes `.flowpilot/lifecycle/` evidence when
  requested.
- Current project progress is tracked in `.flowpilot/`.

## Remaining Work

Before public release:

1. Review the README and docs for final GitHub presentation.
2. Fill in final public FlowGuard source URLs if needed.
3. Run privacy and public-boundary review before publishing.

## Validation Commands

Run:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

If any fail, fix the model, protocol, templates, or checks before continuing.
