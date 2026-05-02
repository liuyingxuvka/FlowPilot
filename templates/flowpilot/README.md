# `.flowpilot/` Template

This directory is the reusable project-control template copied into target
projects when FlowPilot starts.

Canonical state is JSON or executable Python. Markdown is an English summary
for review.

## Use

1. Copy this directory into the target project as `.flowpilot/`.
2. Replace template placeholders such as `<project-name>` and `<task-summary>`.
3. Emit `startup_banner.template.md` in chat as the first visible launch marker.
4. Offer run-mode selection and record the selected mode or fallback reason.
5. Run Grill-me style self-interrogation.
6. Create or restore the fixed six-agent crew, write `crew_ledger.json`, and
   write a compact role memory packet for every required crew role. The
   default startup target is six live background subagents where the host and
   current tool policy permit them. If authorization is missing or startup
   fails, pause and ask. Continue with memory-seeded single-agent six-role
   continuity only after an explicit user fallback decision.
7. Main executor writes `material_intake_packet.json`, then the human-like
   reviewer approves material sufficiency before PM planning uses it.
8. Project manager writes `pm_material_understanding.json`, classifies material
   complexity, and records whether messy/raw materials require discovery,
   cleanup, modeling, research, validation, or reconciliation nodes.
9. Ask the project manager to synthesize `product_function_architecture.json`
   before contract freeze, including user tasks, capabilities, feature
   decisions, visible-display rationale, missing-feature review, negative
   scope, and the functional acceptance matrix.
10. Product FlowGuard officer approves modelability and the human-like reviewer
   challenges usefulness and missing or unnecessary product behavior.
11. Freeze the acceptance contract from the approved product-function
   architecture before route execution.
12. Ask the project manager for the initial route-design decision.
13. Project manager extracts the child-skill gate manifest from likely invoked
   child skills, assigns required approvers, and gets reviewer/officer/PM
   approval before route modeling.
14. Generate a candidate route tree and freeze it only after root FlowGuard
   checks pass.
15. Review each parent subtree with FlowGuard before entering child work.
16. Refine the child-skill gate manifest for the current node before executing
   an invoked child skill, and require assigned-role approval before the
   parent node resumes.
17. Run child-skill conformance checks when a node invokes another skill.
18. Probe host continuation capability. If real wakeups are supported, create
   the all-or-none automated bundle: a one-minute route heartbeat
   (`FREQ=MINUTELY;INTERVAL=1`), paired watchdog, and singleton global
   supervisor at the fixed 30-minute cadence. Each heartbeat refreshes the
   project registration lease. If unsupported, record `manual-resume` and do
   not create any of those automations.
19. Write `.flowpilot/execution_frontier.json` from the checked route before
   syncing the visible Codex plan or advancing work. Each PM resume decision
   records a completion-oriented runway and the main executor replaces the
   current visible plan projection from that runway. If the host exposes a
   native plan/task-list tool such as Codex `update_plan`, call it with that
   runway before work starts; if not, record the fallback projection method and
   show the runway in chat.
20. Before any child-skill execution, image generation, implementation, or
   bounded route chunk, set `startup_activation` in state/frontier from the
   current route, crew, role memory, live-subagent startup decision,
   continuation, and visible-plan evidence. The human-like reviewer then
   personally checks the real route, state, frontier, crew, role memory,
   heartbeat, watchdog, global supervisor, Windows scheduled task, automation,
   and cleanup evidence, then writes `.flowpilot/startup_review/latest.json`.

   The reviewer reports facts and blockers only. PM reads the report, returns
   blockers to workers when needed, and opens `pm_start_gate` only from the
   current clean report by writing `.flowpilot/startup_pm_gate/latest.json` and
   setting `work_beyond_startup_allowed: true` in state and frontier.

   Work beyond startup is blocked until the PM-owned gate is open and the
   PM records `work_beyond_startup_allowed: true`. A route-local file without
   matching canonical state/frontier/crew/continuation evidence, a startup
   record with neither live agents nor explicit fallback authorization, or
   missing requested old-route cleanup is blocked and must be repaired before
   continuing.
21. Before terminal completion, have the project manager rebuild
   `final_route_wide_gate_ledger.json` from the current route and frontier,
   collect all effective node gates and child-skill gates, resolve generated
   resource lineage, check stale evidence and superseded-node explanations, get
   human-like backward review, and allow PM completion approval only when
   unresolved count is zero.
22. Update heartbeats, role memory packets, node reports, and checkpoints
   after verified progress.
23. On any controlled nonterminal stop, write the controlled-stop notice into
   state/frontier or heartbeat evidence and show the user whether to wait for
   heartbeat or type `continue FlowPilot`. On terminal completion, write the
   completion notice instead of a resume prompt.

## Files

- `state.template.json`: current pointer, host continuation mode, startup
  activation hard-gate state, and controlled-stop/completion notice state.
- `execution_frontier.template.json`: current route version, active node, next
  jump, current mainline, host continuation decision, PM completion runway,
  PM-owned child-skill gate manifest, checks before advance,
  native/fallback visible plan sync method, visible plan projection depth, and
  the single user-facing flow diagram settings plus startup PM gate and resume
  notice metadata.
- `mode.template.json`: run mode and hard-gate policy.
- `crew_ledger.template.json`: persistent six-agent crew roles, ids, status,
  authority boundaries, memory paths, recovery rules, and terminal archive
  state.
- `crew_memory/role_memory.template.json`: compact per-role recovery memory
  packet used to resume or replace unavailable subagents after heartbeat or
  manual resume.
- `material_intake_packet.template.json`: main-executor material inventory and
  source-quality packet reviewed before PM planning.
- `pm_material_understanding.template.json`: PM interpretation, source-claim
  matrix, open questions, material complexity, and discovery decision.
- `product_function_architecture.template.json`: PM-owned pre-contract product
  function architecture package.
- `flowguard_modeling_request.template.json`: PM-authored request for proactive
  process/product/object modeling when a decision is uncertain.
- `flowguard_modeling_report.template.json`: FlowGuard officer report that
  returns modelability, blindspots, failure paths, recommendation, and route
  mutation candidate for PM decision.
- `final_route_wide_gate_ledger.template.json`: PM-owned terminal ledger
  rebuilt from the current route before final completion approval.
- `contract.template.md`: acceptance contract shell.
- `capabilities.template.json`: required and conditional capability gates.
- `startup_banner.template.md`: first visible chat banner for formal startup.
- `routes/route-001/flow.template.json`: initial route.
- `routes/route-001/flow.template.md`: route summary shell.
- `routes/route-001/nodes/node-001-start/node.template.json`: first node.
- `heartbeats/hb.template.json`: heartbeat/manual-resume evidence shell,
  including continuation readiness and controlled-stop notice fields.
- `watchdog/watchdog.template.json`: external stale-heartbeat check shell.
- `diagrams/user-flow-diagram.template.mmd`: Mermaid-style user flow source for
  both chat fallback and UI display.
- `diagrams/user-flow-diagram.template.md`: Markdown preview wrapper for the
  same user flow diagram.
- `checkpoints/checkpoint.template.json`: verified milestone shell.
- `capabilities/capability-evidence.template.json`: capability evidence shell.
- `experiments/experiment-001/experiment.template.json`: bounded experiment
  shell.
- `task-models/README.md`: where task-local FlowGuard models live.
