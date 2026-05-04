# `.flowpilot/` Template

This directory is the reusable project-control template copied into target
projects when FlowPilot starts.

Canonical state is JSON or executable Python. Markdown is an English summary
for review.

## Use

1. Ensure the target project has `.flowpilot/`.
2. Create a new run directory under `.flowpilot/runs/<run-id>/` for every new
   formal FlowPilot invocation. The top level keeps only thin catalog files:
   `current.json` points at the active run, and `index.json` lists all runs for
   Cockpit tabs and audit lookup. Resolve the active run from
   `current.json -> runs/<run-id>`; old top-level state files are legacy
   evidence only and must not override the active run.
3. Copy run-scoped templates into the new run directory and replace template
   placeholders such as `<project-name>`, `<task-summary>`, `<run-id>`, and
   `<continues-from-run-id>`.
4. If the user asks to continue previous work, still create a fresh run. Record
   `continues_from_run_id` and write a prior-work import packet that treats old
   runs and project files as input materials. Do not reuse old control state,
   old live-agent IDs, old screenshots, or old route gates as current evidence.
5. Ask the four startup questions: run mode, background-agent permission,
   scheduled-continuation permission, and whether to open Cockpit UI. Stop immediately after asking and wait
   for a later user reply. Do not emit the banner, create route state, load
   child skills, spawn subagents, probe heartbeat, run image generation, or
   start implementation in the question-asking response.
6. Record all four later user answers explicitly. Do not infer a run mode,
   background-agent authorization, scheduled-continuation authorization,
   display surface, or fallback execution from invocation text, `.flowpilot/`
   state, host limits, or previous routes. If the user chose Cockpit, open the
   Cockpit UI as soon as startup state is ready; if the user chose chat, show
   the route sign in chat as before.
7. Emit `startup_banner.template.md` in chat only after the complete explicit
   answer set has been recorded.
8. Run Grill-me style self-interrogation.
9. Create a fresh fixed six-agent crew for the new formal FlowPilot task, write
   `crew_ledger.json`, and write a compact role memory packet for every
   required crew role. The default startup target is six live background
   subagents freshly spawned after the startup answers and current route
   allocation where the host and current tool policy permit them. Prior-route
   `agent_id` values are audit history only. If authorization is missing or
   startup fails, pause and ask. Continue with memory-seeded single-agent
   six-role continuity only after an explicit user fallback decision.
10. Main executor writes `material_intake_packet.json`, including local skill
   and host capability inventory as candidate-only resources, then the
   human-like reviewer approves material sufficiency before PM planning uses it.
11. Project manager writes `pm_material_understanding.json`, classifies material
   complexity, and records whether messy/raw materials require discovery,
   cleanup, modeling, research, validation, or reconciliation nodes.
12. Ask the project manager to synthesize `product_function_architecture.json`
   before contract freeze, including user tasks, capabilities, feature
   decisions, visible-display rationale, missing-feature review, negative
   scope, and the functional acceptance matrix.
13. Product FlowGuard officer approves modelability and the human-like reviewer
   challenges usefulness and missing or unnecessary product behavior.
14. Project manager writes `root_acceptance_contract.json` for the PM-owned
   hard requirements and selects `standard_scenario_pack.json` as the baseline
   replay pack for final review.
15. Freeze the acceptance contract from the approved product-function
   architecture before route execution.
16. Ask the project manager for the initial route-design decision.
17. Project manager writes `pm_child_skill_selection.json` from the product
   architecture, capability map, frozen contract, and local skill inventory.
18. Project manager extracts the child-skill gate manifest only from
   PM-selected child skills, assigns required approvers, and gets
   reviewer/officer/PM approval before route modeling.
19. Generate a candidate route tree and freeze it only after root FlowGuard
    checks pass.
20. Enumerate every effective route node with children as a parent backward
   replay target. This is structural, not a high-risk/integration heuristic.
21. Review each parent subtree with FlowGuard before entering child work.
22. Refine the child-skill gate manifest for the current node before executing
   an invoked child skill, and require assigned-role approval before the
   parent node resumes.
23. Run child-skill conformance checks when a node invokes another skill.
24. Before each implementation-bearing node or formal route chunk, refresh and
   visibly display the current-node FlowPilot Route Sign, then write that
   node's `node_acceptance_plan.json` with root mappings, risk hypotheses,
   concrete experiments, evidence paths, route-sign display proof, and
   terminal replay obligations.
   PM owns reviewer timing: write a review hold before worker/main-executor
   work, then after worker output, verification, and anti-rough-finish evidence
   are ready, write a review release naming gate, evidence paths, scope, and
   required inspections. Early reviewer work is precheck only and cannot open
   or block the gate.
25. Before any parent/composite node closes, write
   `parent_backward_replay.json`, have the reviewer start from the
   parent-level delivered result and replay the child rollup, then record the
   PM segment decision. Repair reruns the same parent replay.
26. Probe host continuation capability only after the scheduled-continuation
   startup answer is recorded. If real wakeups are authorized and supported,
   create a stable one-minute route heartbeat (`FREQ=MINUTELY;INTERVAL=1`). If
   the user selected manual resume, record `manual-resume` and do not create
   heartbeat automation. If automated continuation was authorized but setup is
   unsupported or fails, stop for a new user decision instead of silently
   switching to manual resume. Continuation evidence records host kind
   (`codex_heartbeat_automation`, `windows_scheduled_task`, `manual_resume`, or
   `blocked_unsupported`) and the exact host evidence source.
27. Write `.flowpilot/runs/<run-id>/execution_frontier.json` from the checked route before
   syncing the visible Codex plan or advancing work. Each PM resume decision
   records a completion-oriented runway and the main executor replaces the
   current visible plan projection from that runway. If the host exposes a
   native plan/task-list tool such as Codex `update_plan`, call it with that
   runway before work starts; if not, record the fallback projection method and
   show the runway in chat.
28. Before any child-skill execution, image generation, implementation, or
   bounded route chunk, set `startup_activation` in state/frontier from the
   current route, crew, role memory, live-subagent startup decision,
   continuation, and visible-plan evidence. The human-like reviewer then
   personally checks the real route, state, frontier, crew, role memory,
   heartbeat or manual-resume evidence, automation records, and cleanup
   evidence, then writes
   `.flowpilot/runs/<run-id>/startup_review/latest.json`.

   The reviewer reports facts and blockers only. PM reads the report, returns
   blockers to workers when needed, and opens `pm_start_gate` only from the
   current clean report by writing
   `.flowpilot/runs/<run-id>/startup_pm_gate/latest.json` and
   setting `work_beyond_startup_allowed: true` in state and frontier.

   Work beyond startup is blocked until the PM-owned gate is open and the
   PM records `work_beyond_startup_allowed: true`. A route-local file without
   matching canonical state/frontier/crew/continuation evidence, a startup
   record with neither live agents nor explicit fallback authorization, or
   missing requested old-route cleanup is blocked and must be repaired before
   continuing.
   Before PM runway work on heartbeat or manual resume, restore all six role
   identities and work memories from `crew_ledger.json` and `crew_memory/`,
   then write a crew rehydration report. Do not lazily rehydrate roles only
   when first needed.
29. Before terminal completion, have the project manager rebuild
   `final_route_wide_gate_ledger.json` from the current route and frontier,
   collect all effective node gates and child-skill gates, resolve every
   generated resource with terminal disposition `consumed_by_implementation`,
   `included_in_final_output`, `qa_evidence`, `flowguard_evidence`,
   `user_flow_diagram`, `superseded`, `quarantined`, or
   `discarded_with_reason`, replay the standard scenario pack plus node-risk
   scenarios, triage every risk or blindspot, check stale evidence and
   superseded-node explanations, build `terminal_human_backward_replay_map.json`,
   require the reviewer to start from the delivered product and manually replay
   root, parent, and leaf-node obligations, record PM decisions after every
   replay segment, and allow PM completion approval only when unresolved count
   and unresolved residual risk count are both zero.
29. Run `terminal_closure_suite.json` so state/frontier/ledger/checkpoints,
   lifecycle evidence, role memory, and final report readiness are refreshed
   before the terminal completion notice.
30. Update heartbeats, role memory packets, node reports, checkpoints, and the
   append-only activity stream after verified progress. Cockpit and chat
   progress read from activity events plus current route/frontier state.
31. At each node or meaningful review boundary, append any FlowPilot skill
   issue or improvement observation to
   `flowpilot_skill_improvement_observations.jsonl`. Observations are about
   FlowPilot itself: unclear protocol, weak templates, missing checks, hard to
   find code paths, or tooling friction. They do not block the current project.
32. Before the terminal completion notice, have the project manager write
   `flowpilot_skill_improvement_report.json` summarizing observations for
   future manual FlowPilot root-repo maintenance. The report must exist even
   when it says no obvious skill improvement was observed, but its contents do
   not require root-repo fixes before completing the current project.
33. On any controlled nonterminal stop, write the controlled-stop notice into
   state/frontier or heartbeat evidence and show the user whether to wait for
   heartbeat or type `continue FlowPilot`. On terminal completion, write the
   completion notice instead of a resume prompt.

## Files

- `state.template.json`: current pointer, host continuation mode, startup
  activation hard-gate state, and controlled-stop/completion notice state.
- `execution_frontier.template.json`: current route version, active node, next
  jump, current mainline, host continuation decision, PM completion runway,
  PM-owned child-skill gate manifest, checks before advance,
  native/fallback visible plan sync method, visible plan projection depth, the
  realtime FlowPilot Route Sign chat/UI display gate, and startup PM gate and
  resume notice metadata.
- `mode.template.json`: run mode and hard-gate policy.
- `crew_ledger.template.json`: persistent six-agent crew roles, ids, status,
  authority boundaries, memory paths, recovery rules, and terminal archive
  state.
- `crew_memory/role_memory.template.json`: compact per-role recovery memory
  packet used to resume or replace unavailable subagents after heartbeat or
  manual resume.
- `crew_memory/crew_rehydration_report.template.json`: resume-time all-role recovery report
  proving project manager, reviewer, both FlowGuard officers, and both workers
  were restored from ledger and role memory before PM runway work.
- `material_intake_packet.template.json`: main-executor material inventory,
  local skill and host capability inventory, and source-quality packet
  reviewed before PM planning.
- `local_skill_inventory.template.json`: optional standalone local skill and
  host capability inventory consumed by the material packet and PM selection.
- `pm_material_understanding.template.json`: PM interpretation, source-claim
  matrix, open questions, material complexity, and discovery decision.
- `product_function_architecture.template.json`: PM-owned pre-contract product
  function architecture package.
- `pm_child_skill_selection.template.json`: PM-owned selection of required,
  conditional, deferred, and rejected child skills after product architecture.
- `root_acceptance_contract.template.json`: PM-owned early hard-requirement
  threshold and proof-obligation package.
- `standard_scenario_pack.template.json`: baseline scenario replay pack for
  happy paths, edge/failure paths, regressions, lifecycle, and PM-risk cases.
- `flowguard_modeling_request.template.json`: PM-authored request for proactive
  process/product/object modeling when a decision is uncertain. It records the
  officer-owned async dispatch mode, officer output root, and what
  non-dependent preparation the main executor may do while reports are pending.
- `flowguard_modeling_report.template.json`: FlowGuard officer report that
  returns modelability, execution ownership provenance, blindspots, failure
  paths, PM risk tiers, model-derived review agenda, toolchain/model
  improvement suggestions, human walkthrough recommendations, recommendation,
  confidence boundary, and route mutation candidate for PM decision. Report
  templates distinguish officer-run commands from main-executor outputs used as
  pointers and avoid absolute no-risk claims.
- `role_approval.template.json`: PM, reviewer, or FlowGuard officer
  independent adversarial approval evidence. It records direct sources checked,
  state fields, probes, adversarial hypotheses, concrete evidence references,
  risk-or-blindspot triage, unresolved residual risk count, and rejects
  completion-report-only approval.
- `human_review.template.json`: reviewer-owned node, visual, interaction,
  parent, or final inspection report. For UI and interaction gates it records
  the reviewer's personal walkthrough, reachability checks, text
  overlap/clipping, whitespace/density, crowded or underfilled regions,
  aesthetic verdict, and concrete design recommendations. Worker screenshots
  and smoke logs are pointers only.
- `defects/defect_ledger.template.json`: PM-owned run-level defect ledger. Any
  role can register a product, FlowPilot skill, process, evidence, or
  tool/environment defect; PM triages and closes only after required recheck
  evidence.
- `defects/defect_event.template.json`: append-only defect event shape used for
  creation, triage, repair, recheck, closure, deferral, and reopening.
- `evidence/evidence_ledger.template.json`: run-level evidence credibility
  ledger that separates valid live-project evidence from invalid, stale,
  superseded, fixture, synthetic, historical, and generated-concept evidence.
- `evidence/evidence_event.template.json`: append-only evidence event shape
  used when evidence is registered, invalidated, marked stale, superseded, or
  linked to a defect.
- `generated_resource_ledger.template.json`: immediate registry for
  every generated concept, image, icon, screenshot, diagram, model output, or
  similar resource. `pending` is nonterminal; closure requires one of
  `consumed_by_implementation`, `included_in_final_output`, `qa_evidence`,
  `flowguard_evidence`, `user_flow_diagram`, `superseded`, `quarantined`, or
  `discarded_with_reason`.
- `activity_stream.template.json`: append-only progress stream for PM,
  reviewer, officer, worker, route, checkpoint, heartbeat/manual-resume, and
  terminal events consumed by Cockpit/chat progress.
- `pause_snapshot.template.json`: controlled-pause snapshot with current
  route/node, blockers, pending rechecks, evidence caveats, heartbeat/agent
  lifecycle, and cleanup boundary for fresh restarts.
- `parent_backward_replay.template.json`: local parent/composite replay
  evidence required for every effective route node with children before that
  parent closes.
- `final_route_wide_gate_ledger.template.json`: PM-owned terminal ledger
  rebuilt from the current route before final completion approval.
- `terminal_human_backward_replay_map.template.json`: PM-owned terminal review
  map that orders reviewer replay from delivered product to root, parent, and
  leaf-node obligations, with PM segment decisions and repair restart policy.
- `terminal_closure_suite.template.json`: terminal state, lifecycle, evidence,
  role-memory, and final-report readiness suite run before completion notice.
- `flowpilot_skill_improvement_observation.template.json`: node/review-level
  FlowPilot skill issue observation appended to the run's JSONL log without
  blocking current project completion.
- `flowpilot_skill_improvement_report.template.json`: PM-owned terminal
  and live-updated summary of FlowPilot skill improvement observations for
  later manual root-repo maintenance. The report is updated during the run and
  rebuilt at terminal closure; it is not a requirement to fix the root repo
  inside the current run.
- `contract.template.md`: acceptance contract shell.
- `capabilities.template.json`: required and conditional capability gates.
- `startup_banner.template.md`: post-answer visible chat banner for formal startup.
- `routes/route-001/flow.template.json`: initial route.
- `routes/route-001/flow.template.md`: route summary shell.
- `routes/route-001/nodes/node-001-start/node.template.json`: first node.
- `node_acceptance_plan.template.json`: per-node experiment and risk-replay
  plan copied into implementation-bearing route nodes.
- `parent_backward_targets.template.json`: PM-owned structural list of every
  effective route node with children that must receive local backward replay.
- `parent_backward_replay.template.json`: local parent/composite replay report
  copied into every structurally required parent node before closure.
- `heartbeats/hb.template.json`: heartbeat/manual-resume evidence shell,
  including continuation readiness, host kind, exact host evidence source,
  controlled-stop notice fields, and the latest route-sign display gate state.
- `diagrams/user-flow-diagram.template.mmd`: simplified English Mermaid
  FlowPilot Route Sign source for both chat fallback and UI display.
- `diagrams/user-flow-diagram.template.md`: Markdown preview wrapper for the
  same route sign, including the closed-Cockpit chat display requirement for
  startup, major route-node entry, PM current-node work brief, repair returns,
  completion review, and explicit user requests.
- `checkpoints/checkpoint.template.json`: verified milestone shell.
- `capabilities/capability-evidence.template.json`: capability evidence shell.
- `experiments/experiment-001/experiment.template.json`: bounded experiment
  shell.
- `task-models/README.md`: where task-local FlowGuard models live.
