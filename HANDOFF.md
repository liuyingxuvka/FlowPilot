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
- Formal startup then has a PM-owned product-function architecture gate before
  contract freeze. It captures user tasks, product capabilities, feature
  necessity, display rationale, missing high-value features, negative scope,
  and a functional acceptance matrix.
- Child-skill routing now has a PM-owned selection gate between product
  architecture/capability mapping and child-skill gate extraction. The PM reads
  the local skill inventory and classifies candidate skills as required,
  conditional, deferred, or rejected; child-skill discovery may proceed only
  from PM-selected skills, never from raw local availability.
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
  must be grilled into specific repairable issues, mutate the route into
  repair nodes, and close only after repair evidence and same-inspector recheck.
- Every effective route node with children now requires local parent backward
  human-like replay before closure. The trigger is structural, not a semantic
  guess about risk, integration, feature status, or downstream dependency. If
  child-local passes do not compose into the parent goal, FlowPilot
  structurally mutates the route to rework an existing child, insert an
  adjacent sibling child, rebuild the child subtree, or bubble impact upward
  before rerunning the same parent review and recording a PM segment decision.
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
- Blocking review failures now force structural route mutation. The failed
  child remains as failed/superseded history, affected evidence becomes stale,
  the route version and execution frontier change, and FlowPilot either resets
  the existing child, inserts an adjacent repair/regeneration sibling, splits
  the finding into multiple focused children, or rebuilds/bubbles the subtree.
- Pause, restart, and terminal cleanup now require unified lifecycle
  reconciliation across Codex heartbeat automations, local state, execution
  frontier, and heartbeat/manual-resume evidence.
- Heartbeat recovery now restores or replaces the six-agent crew before asking
  the project manager for a completion-oriented runway from the current
  position to project completion. The main executor no longer decides route
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
  main executor may draft, run tools, integrate, and report but may not
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
- Terminal completion now requires a PM-owned dynamic route-wide gate ledger
  rebuilt from the current route, not the initial route. The ledger resolves
  effective and superseded nodes, child-skill gates, human-review gates,
  product/process model gates, generated-resource lineage, stale evidence,
  waivers, blockers, and unresolved items. Completion is blocked until
  unresolved count is zero, every generated resource is consumed, included in
  final output, used as evidence, superseded, quarantined, or discarded with
  reason, the human-like reviewer replays the final product backward through
  that ledger, and the PM records ledger-specific completion approval.
- Each formal FlowPilot invocation now creates a fresh
  `.flowpilot/runs/<run-id>/` directory in the target project. Top-level
  `.flowpilot/current.json` and `.flowpilot/index.json` are pointer/catalog
  files only. Continuing old work creates a new run and imports old outputs as
  read-only evidence; old control state, agent IDs, screenshots, icons, or
  route files must not become current state.
- Heartbeat/manual-resume lifecycle state now trusts current-run `state.json`,
  latest heartbeat evidence, execution frontier, and crew memory. There is no
  extra reset path or registry layer.
- The project manager may proactively use FlowGuard as a modeling laboratory
  for uncertain route, repair, feature, product-object, file-format, protocol,
  or validation decisions. The PM writes a structured modeling request, assigns
  the process FlowGuard officer, product FlowGuard officer, or both, receives
  a modelability-aware report, and then records the route decision.
- FlowGuard modeling requests are now officer-owned async gates when live
  background roles are available. The PM records the request and officer output
  root, the matching officer authors/runs/interprets the model and writes
  execution provenance, and the main executor may only do non-dependent
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
- Formal startup now begins with a four-question pre-banner gate. On
  `Use FlowPilot` / `使用开始`, the assistant asks for run mode, background-agent
  permission, scheduled-continuation permission, and whether to open Cockpit UI
  or use chat route signs, then the assistant response must stop immediately and
  wait for the user's reply. The startup banner, route writes, Cockpit launch,
  child skills, subagents, heartbeat probes, imagegen, and implementation are
  blocked until a later user reply explicitly answers all four questions and
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
    intake when source materials are non-trivial. The main executor must
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
20. Asking the four startup questions is not a soft prompt. It is a hard
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

- The main skill lives at `skills/flowpilot/SKILL.md`.
- Reusable project-control templates live at `templates/flowpilot/`.
- FlowGuard regression models live at `simulations/`.
- Self-check and smoke scripts live at `scripts/`.
- `scripts/flowpilot_lifecycle.py` scans lifecycle authorities before pause,
  restart, or terminal cleanup and writes `.flowpilot/runs/<run-id>/lifecycle/` evidence when
  requested.
- Current project progress is tracked in `.flowpilot/current.json` plus the
  active `.flowpilot/runs/<run-id>/` directory.

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
