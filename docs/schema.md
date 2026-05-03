# `.flowpilot/` Schema Notes

## Canonical Files

Machine-readable files are the source of truth. Each formal FlowPilot
invocation creates a current run under `.flowpilot/runs/<run-id>/`. Top-level
`.flowpilot/current.json` and `.flowpilot/index.json` are pointer/catalog files
only; the following files live inside the current run unless explicitly marked
user-level:

- `.flowpilot/current.json`
- `.flowpilot/index.json`
- `runs/<run-id>/run.json`
- `runs/<run-id>/state.json`
- `runs/<run-id>/execution_frontier.json`
- `mode.json`
- `crew_ledger.json`
- `crew_memory/*.json`
- `product_function_architecture.json`
- `root_acceptance_contract.json`
- `standard_scenario_pack.json`
- `final_route_wide_gate_ledger.json`
- `terminal_closure_suite.json`
- `contract.md`
- `capabilities.json`
- `routes/*/flow.json`
- `routes/*/parent_backward_targets.json`
- `routes/*/nodes/*/node.json`
- `routes/*/nodes/*/node_acceptance_plan.json`
- `routes/*/nodes/*/parent_backward_replay.json`
- `heartbeats/*.json`
- `lifecycle/latest.json`
- `lifecycle/events.jsonl`
- `startup_review/latest.json`
- `startup_pm_gate/latest.json`
- `human_reviews/*.json`
- `role_approvals/*.json`
- `checkpoints/*.json`
- `experiments/*/experiment.json`
- `flowpilot_skill_improvement_observations.jsonl`
- `flowpilot_skill_improvement_report.json`

Markdown files are English summaries for review.

## State

`runs/<run-id>/state.json` records the current run pointer:

- active route;
- active node;
- active route version;
- execution frontier path and version;
- visible Codex plan projection version;
- run mode;
- product-function architecture path;
- root acceptance contract path;
- standard scenario pack path;
- terminal closure suite path;
- final route-wide gate ledger path;
- status;
- last heartbeat;
- last checkpoint;
- next node;
- next action;
- startup activation hard-gate status.

It should not store the whole history.

`startup_activation` is the route-start transaction record. A formal route
cannot enter child-skill execution, image generation, implementation, or route
chunks until this block and the matching frontier block show:

- `hard_gate_required: true`;
- `startup_questions` records explicit user answers for run mode,
  background-agent permission, and scheduled-continuation permission;
- `startup_questions.dialog_stopped_for_user_answers: true`;
- `startup_questions.banner_emitted_after_answers: true`;
- `.flowpilot/current.json` points at the same run and `.flowpilot/index.json`
  catalogs it;
- canonical route files, current-run `state.json`, and
  `execution_frontier.json` are
  written for the same active nonterminal route;
- legacy top-level control state is absent, legacy-only, or quarantined and is
  not used as the current run state;
- continuing prior work has a current-run prior-work import packet;
- `crew_ledger_current: true`;
- `role_memory_packets_current` is at least 6;
- `live_subagent_startup` records either six live background agents
  started/resumed after a user decision or explicit user authorization for
  single-agent six-role continuity;
- `continuation_ready: true`, either as automated heartbeat evidence or
  explicit `manual-resume` no-automation evidence;
- `startup_preflight_review` records the human-like reviewer's factual startup
  audit, including user authorization versus actual state, route/state/frontier
  consistency, old-route or old-asset cleanup when requested, real Codex
  heartbeat automation or manual-resume evidence, background-agent role
  evidence, and shadow or residual route state;
- `pm_start_gate` records the project manager's decision from the current
  reviewer report. The reviewer cannot open this gate. If the report has
  blockers, PM sends remediation back to workers and requires a recheck;
- `work_beyond_startup_allowed: true`;
- `shadow_route_detected: false`.

`startup_activation.startup_questions` is the pre-banner gate:

- `required: true`;
- `status`: `pending`, `answered`, or `blocked`;
- `asked_before_banner: true`;
- `dialog_stopped_for_user_answers: true` records that the assistant response
  ended immediately after asking the three questions and no startup work ran
  until the user's later reply;
- `explicit_user_answer_recorded: true` before the PM can open startup;
- `answer_source`: `user_reply` or `user_reply_after_prompt`; values such as
  `agent_inferred`, `default`, `prior_route`, or `single_message_invocation`
  are invalid;
- `answers.run_mode.answer`: `full-auto`, `autonomous`, `guided`, or
  `strict-gated`;
- `answers.background_agents.answer`: `allow` for six live background agents
  or `single-agent` for single-agent six-role continuity;
- `answers.scheduled_continuation.answer`: `allow` for heartbeat/automation or
  `manual` for manual resume;
- `answer_evidence_path`, `answered_at`, and
  `banner_emitted_after_answers: true`.

If any answer is absent, ambiguous, or `pause`, startup remains
`startup_pending_user_answers` and no banner, route work, child skill,
imagegen, implementation, fallback execution, subagent startup, heartbeat probe,
heartbeat job, or manual-resume claim may proceed. If the questions were asked
but the assistant did not stop and wait for the user's reply, the answer
evidence is invalid and the PM must not open startup.

`startup_activation.startup_preflight_review` is written by the human-like
reviewer after direct factual checks. It is not an approval object and no
runtime startup-check script writes it. It must include:

- `required: true`;
- `reviewer_role: human_like_reviewer`;
- `reviewer_decision_authority: report_only_no_start_approval`;
- `report_path`;
- `report_status`: `pending`, `ready_for_pm`, or
  `requires_worker_remediation`;
- `blocking_findings`;
- scope flags for user authorization, route consistency, cleanup boundary,
  continuation evidence, real Codex heartbeat automation or manual-resume
  evidence, background-agent roles, user background-agent decision versus
  actual subagent state, live subagent count or explicit single-agent
  authorization, and shadow/residual state;
- required facts for route heartbeat interval 1 minute and route heartbeat
  RRULE `FREQ=MINUTELY;INTERVAL=1` when automated continuation is selected;
- if `answers.background_agents.answer` is `allow`, six live role-bearing
  subagents must be active or resumed after the user decision;
- if `answers.background_agents.answer` is `single-agent`, explicit
  single-agent role-continuity authorization must exist and the route must not
  claim six live subagents.

`startup_activation.pm_start_gate` is written by the project manager after
reading the reviewer report. It must include:

- `required: true`;
- `decision_owner: project_manager`;
- `decision`: `pending`, `open`, `return_to_worker`, or `blocked`;
- `based_on_review_report_path`;
- `decision_path`;
- `worker_remediation_required`;
- `opened_at` only when the current clean reviewer report supports opening.

`work_beyond_startup_allowed` can become true only after a clean reviewer
report and a PM-owned open decision. Worker remediation invalidates the prior
review report and must be rechecked before PM opens the gate.

A route-local file, generated concept, screenshot, or implementation artifact
without matching canonical state/frontier/crew/continuation evidence is a
shadow route. Shadow routes are invalid startup evidence and must be
quarantined or superseded before work continues.

`startup_activation.live_subagent_startup` records this decision:

- `required_by_default: true`;
- `decision`: `live_agents_started`, `live_agents_resumed`,
  `single_agent_role_continuity_authorized`, or `blocked`;
- `user_decision_recorded: true` before the PM can open startup;
- `user_authorized_live_start: true`, `live_start_attempted: true`, and
  `live_agents_active >= 6` for the live-agent path;
- `single_agent_role_continuity_authorized: true` for the fallback path;
- `blocker` and `evidence_path` for the prompt, failed attempt, or fallback
  decision evidence.

## Crew Ledger

`crew_ledger.json` records the persistent six-agent crew for a formal
FlowPilot route:

- project manager;
- human-like reviewer;
- process FlowGuard officer;
- product FlowGuard officer;
- worker A;
- worker B.

For each role, the ledger records the role name, agent id when available,
status, authority boundary, latest report path, role memory path, memory
freshness, recovery or replacement rule, and terminal archive state. It is
loaded before formal route work and before heartbeat recovery.

Role memory packets under `crew_memory/*.json` are the durable continuity
state for the crew. Each packet records:

- role and nickname;
- agent id when available;
- authority boundary and forbidden approvals;
- compact role charter summary;
- frozen contract and current route position;
- latest report path;
- latest decisions, open obligations, open questions, blockers, and
  do-not-redo notes;
- relevant evidence paths;
- latest rehydration result;
- update timestamp.

Live subagent context is not the source of truth, but six live background
agents are the default startup target. Heartbeat or manual resume may try to
resume a stored agent id. If live agents are unavailable, FlowPilot records the
block and asks for a user decision before falling back to replacement from the
latest role memory packet. Raw transcripts are optional evidence only; a
compact structured memory packet is required before a replacement role can
approve gates. Heartbeat recovery loads the ledger and memory packets, records
which roles were resumed, replaced, or blocked, and only then asks the project
manager for a completion-oriented runway from the current route position to
project completion.

Valid current role statuses may represent live or memory-seeded continuity,
including `active`, `idle`, `ready`, `running`, `restored`, `recovered`,
`replaced_from_memory`, `memory_recovered`, `memory_seeded`, or
`live_unavailable_memory_seeded`. `archived`, `paused`, `blocked`, and other
terminal statuses cannot satisfy startup activation. FlowPilot must distinguish
between "the role is recovered and authorized" and "a live subagent process is
currently running"; when the latter is unavailable, the fallback is valid only
after explicit user authorization for single-agent role continuity.

## Material Intake Packet

`material_intake_packet.json` is the main-executor material inventory and
source-quality packet. It also records a local skill and host capability
inventory as candidate-only route material. The reviewer sufficiency block
must show direct source inspection, not report-only acceptance:

- `reviewer_fact_check_required: true`;
- `direct_material_sources_checked` and `direct_material_samples_checked`;
- `packet_matches_checked_sources`: `yes`, `no`, or `partial`;
- `worker_report_only: false`.

Reviewer approval is invalid when the packet only summarizes worker claims
without direct material-source checks.

The local skill inventory portion records skill names, `SKILL.md` paths,
description summaries, candidate fit, possible product capabilities, hard gates
or safety notes, read depth, deferred/private skills, and host capability
providers. It must mark every entry as candidate-only until PM selection.

## PM Child-Skill Selection

`pm_child_skill_selection.json` is the PM-owned bridge from product capability
mapping to child-skill gate extraction. It is written after
`product_function_architecture.json`, the frozen contract, and
`capabilities.json`, and before child-skill route-design discovery.

It records:

- product-function architecture, capabilities manifest, frozen contract, and
  local skill inventory source paths;
- a selection rule stating that product capability needs choose skills, not
  local availability;
- skill decisions marked `required`, `conditional`, `deferred`, or `rejected`;
- supported product capabilities and trigger conditions for each selected
  skill;
- hard gates or user approvals needed before use;
- `SKILL.md` files and references to load now, plus deferred references with
  reasons;
- negative selection reasons for available but unused skills;
- proof that raw inventory was not used as route authority.

## Product Function Architecture

`product_function_architecture.json` is the PM-owned pre-contract product
design package. It is written after startup self-interrogation and six-agent
crew recovery, and before acceptance contract freeze, route generation,
capability routing, or implementation.

It records:

- source inputs from startup self-interrogation and known product context;
- user-task map;
- product capability map;
- feature decisions marked `must`, `should`, `optional`, or `reject`;
- display rationale for every visible label, control, status, card, alert,
  empty state, and persistent text;
- missing high-value feature review;
- negative scope and rejected displays;
- functional acceptance matrix with inputs, outputs, states, permissions,
  failure cases, checks, and evidence paths;
- project-manager synthesis evidence;
- product FlowGuard officer modelability approval or block;
- human-like reviewer usefulness challenge result, including direct checks
  against the user request, inspected material sources, and expected workflow
  reality. `human_like_reviewer_worker_report_only` must be false.

The acceptance contract freezes from this artifact. Later product-function
models check and refine coverage, but they do not substitute for the
pre-contract PM architecture gate.

## Root Acceptance Contract

`root_acceptance_contract.json` is the PM-owned early hard-requirement package
written before contract freeze. It converts the most important user/PM
requirements into route-wide proof obligations without trying to pre-design
every node test.

It records:

- source requirement ids and user-facing rationale;
- acceptance threshold for each root obligation;
- minimum experiment, inspection, replay, or evidence type;
- owner role and required approver;
- terminal replay expectation;
- proof matrix status;
- whether unresolved residual risks are allowed. For completed routes this must
  be false.

## Standard Scenario Pack

`standard_scenario_pack.json` is the compensating scenario baseline used by
terminal review. It is selected or written before contract freeze and replayed
again near completion.

It records scenario families such as:

- core happy path;
- edge and failure handling;
- regression of repaired or previously risky behavior;
- lifecycle/state recovery;
- localization, accessibility, and interaction coverage when relevant;
- PM-risk scenarios inherited from the root contract or node acceptance plans.

Each scenario records the target requirement, operation or experiment design,
expected evidence, required approver, status, and final replay result.

## Node Acceptance Plan

`routes/*/nodes/*/node_acceptance_plan.json` is written before a formal route
chunk or implementation-bearing node starts. It maps only the current node,
not every future node.

It records:

- root acceptance requirements touched by the node;
- child-skill gates and approvers used by the node;
- current-node acceptance criteria;
- concrete experiments, manual walkthroughs, commands, screenshots, or probes;
- known risk hypotheses and how each will be checked;
- risk scenarios that must be replayed in final review if not closed earlier;
- evidence paths and approval owner;
- node structure: whether this is a leaf, parent, or composite node, whether
  it has children, and the local parent backward replay path when applicable;
- unresolved residual risk count, which must be zero before the node can close
  unless the required role records an explicit exception that does not lower the
  frozen contract.

## Parent Backward Replay

`routes/*/parent_backward_targets.json` is PM-owned structural planning
evidence built from the current route. It enumerates every effective `flow.json`
node that has children and points each one at its required
`parent_backward_replay.json`. The file becomes stale whenever the route
version changes and must be rebuilt from the new route before affected parent
closure or terminal ledger approval.

`routes/*/nodes/*/parent_backward_replay.json` is required for every effective
route node with children. The trigger is structural: if the current `flow.json`
node has child nodes, the parent replay is required. No semantic classification
such as high risk, integration, feature, or downstream dependency is needed to
turn this gate on, and those labels cannot turn it off.

It records:

- the parent node id, route version, and source route/frontier paths;
- the structural trigger evidence showing the parent has children;
- the parent goal and parent-level delivered result;
- child node ids, child acceptance plan paths, child evidence paths, and
  product/model evidence used as pointers;
- replay segments starting from the parent-level delivered result, then parent
  goal, child rollup, child node segments, structure fit, PM segment decision,
  and repair/restart policy;
- reviewer evidence showing a neutral observation, independent probe, direct
  current-artifact or behavior checks, and whether children compose into the
  parent goal;
- the PM segment decision: continue, repair existing child, add sibling child,
  rebuild child subtree, bubble to parent, or PM stop;
- stale-evidence and same-parent-rerun status after repair.

Parent closure is invalid until the reviewer pass and PM segment decision are
recorded for that parent, unresolved blocking findings are zero, and any latest
repair has rerun the same parent replay.

## Execution Frontier

`execution_frontier.json` is the source of truth for the next jump and current
mainline plan projection. Heartbeat automations load it instead of embedding
route-specific next steps in the automation prompt.

The frontier records:

- schema version;
- active route and route version;
- frontier version, which must match the active route version before work;
- active node;
- current subnode or current gate when the active node is unfinished;
- current mainline node list;
- next node and fallback node;
- current chunk and next chunk;
- user flow diagram metadata: enabled display mode, render policy, highlighted
  current stage, source route/frontier paths, generated Mermaid path, rendered
  route/frontier versions, and staleness after route mutation;
- debug FlowGuard Mermaid metadata, which defaults to disabled and on-request
  only;
- host continuation decision: automated, manual-resume, blocked, or unknown;
- latest PM completion runway, including current gate, downstream steps,
  hard-stop conditions, checkpoint cadence, plan replacement status, and any
  PM stop signal;
- PM-owned child-skill selection status: local skill inventory path, selection
  manifest path, required/conditional/deferred/rejected decisions, and proof
  that raw local availability did not create route work;
- PM-owned child-skill gate manifest status: route-design discovery from
  PM-selected skills, loaded child-skill files, initial manifest path,
  current-node refined manifest path, required approver assignments,
  reviewer/officer/PM approval evidence, and whether all current child-skill
  gates have assigned-role approval;
- PM-owned final route-wide gate ledger status: ledger path, built route
  version, current-route scan, effective-node resolution, child-skill gate
  collection, human-review gate collection, product/process model gate
  collection, standard scenario replay, residual risk triage, stale-evidence
  check, superseded-node explanation, unresolved count, unresolved residual
  risk count, terminal human backward replay map path, reviewer delivered-product
  replay status, PM segment-decision status, repair/restart policy status, PM
  ledger approval path, and whether completion is allowed;
- root acceptance contract and standard scenario pack paths;
- current node acceptance plan path, status, required experiments, and terminal
  replay obligations;
- parent backward replay trigger rule, structurally enumerated parent targets,
  current parent replay path/status, PM segment decision status, and unresolved
  parent replay blocker count;
- terminal closure suite path and latest state/evidence/lifecycle refresh
  status;
- whether the current node is unfinished;
- the concrete `current_subnode` or `next_gate` that the next continuation turn must
  execute while the node is unfinished;
- current-node completion status, required evidence, evidence paths, and
  `advance_allowed`;
- checks required before the next jump;
- visible Codex plan projection for the current mainline;
- crew ledger path, role memory root, rehydration status, restored/replaced
  role lists, and latest project-manager decision, including the PM repair
  strategy interrogation evidence path when a review failure mutates the route;
- route mutation status;
- stable heartbeat launcher metadata when automated continuation is supported;
- heartbeat lifecycle metadata when automated continuation is supported, or
  manual-resume no-automation evidence when unsupported;
- controlled-stop and completion notice metadata: whether the current route is
  complete, whether a resume notice must be shown on controlled nonterminal
  stop, whether heartbeat wakeup can be waited for, and the exact manual resume
  prompt;
- startup activation guard metadata matching `state.json`;
- update timestamp.

If the route structure changes, FlowPilot writes a new route version, reruns
FlowGuard checks, rewrites the execution frontier, and syncs the visible Codex
plan from the latest PM completion runway. When the host has a native visible
plan/task-list tool, such as Codex `update_plan`, the sync must call that tool
and record the method, timestamp, route version, PM runway id, item count, and
completion-tail coverage. It does not rewrite the heartbeat automation prompt
unless the host continuation itself needs repair.

`next_node` is not executable while `unfinished_current_node` is true or
`current_node_completion.advance_allowed` is false. In that state, the next
continuation turn, whether automated heartbeat or manual resume, resumes
`active_node`, obtains a PM completion runway, replaces the visible plan
projection from that runway, selects the persisted `current_subnode` or
`next_gate`, and must execute at least that gate when it is executable before
continuing along the runway. A continuation record that only says "continue to
next gate" without an executed gate or blocker is invalid no-progress evidence.

On any controlled stop before terminal completion, the frontier or heartbeat
record stores a `controlled_stop_notice` packet. Automated mode may set
`can_wait_for_heartbeat` true and include both heartbeat and manual resume
instructions. `manual-resume` mode sets `can_wait_for_heartbeat` false and
instructs the user to type `continue FlowPilot`. Terminal completion stores a
completion notice instead of a resume prompt.

The execution frontier stores the native plan sync status separately from the
PM runway evidence. `synced_to_visible_plan` requires either native plan tool
evidence when available or an explicit no-native-tool fallback. It also records
whether the projection includes downstream runway depth; a current-gate-only
projection is invalid for formal continuation.

Child-skill gate manifests live in the frontier because they determine the
next legal gate. The initial manifest is PM-owned route-design evidence; the
current-node manifest is a contextual refinement. Each gate record names its
source skill, source step, gate type, evidence required, `draft_owner`,
`execution_owner`, `required_approver`, `forbidden_approvers`,
`approval_status`, `approval_evidence_path`,
`independent_validation_required: true`,
`completion_report_only_allowed: false`, and
`independent_validation_evidence_path`. Parent resume is invalid until every
current child-skill gate is approved by its assigned role with independent
validation evidence, or blocked/waived with evidence from the responsible role.

Before any child-skill, imagegen, implementation, or formal route chunk starts,
the human-like reviewer personally checks `.flowpilot/current.json`,
`.flowpilot/index.json`, current-run `state.json`, `execution_frontier.json`,
`routes/<active-route>/flow.json`, `crew_ledger.json`, all role memory packets,
continuation evidence, Codex heartbeat automation or manual-resume evidence,
requested cleanup evidence, and prior-work import boundary when continuing.
The reviewer then writes
`startup_review/latest.json` inside the current run as a factual report.

The PM reads the current factual report. If it has blockers, PM returns the
work to workers and requires a new review after remediation. If it is clean,
PM writes `startup_pm_gate/latest.json` inside the current run and updates state plus frontier so
downstream work can check `work_beyond_startup_allowed`.

## Adversarial Approval Evidence

`role_approvals/*.json` is the canonical evidence family for any PM,
human-like reviewer, process FlowGuard officer, or product FlowGuard officer
approval that is not already embedded in a richer role-owned report. Every
approval gate may reference one of these files through
`independent_validation_evidence_path`.

Each approval evidence object includes:

- `approval_id`, `run_id`, `route_id`, `node_id`, and `gate_id`;
- `approver_role`: `project_manager`, `human_like_reviewer`,
  `process_flowguard_officer`, or `product_flowguard_officer`;
- `approval_scope`: route, material, product architecture, child-skill gate,
  process model, product model, human review, parent backward review,
  startup PM gate, repair, final ledger, lifecycle, or completion;
- `completion_report_only: false`;
- `report_inputs_used_as_pointers`: completion reports, worker reports,
  screenshots, smoke logs, PM summaries, or model snippets consulted only as
  navigation aids;
- `direct_sources_checked`: exact files, materials, screenshots, route/frontier
  files, ledger entries, model files, logs, runtime outputs, or delivered
  artifacts opened by the approver;
- `state_fields_checked`: `.flowpilot` paths and fields, model state fields,
  runtime fields, counters, or ledger entry ids compared;
- `commands_or_probes_run`: manual operations, local commands, browser/UI
  probes, replay commands, FlowGuard checks, sample reads, or other active
  probes run by the approver;
- `adversarial_hypotheses_tested`: concrete failure theories such as stale
  evidence, missing child gate, wrong approver, report-only pass, bad model
  boundary, unreachable interaction, incorrect waiver, or unresolved blocker;
- `concrete_evidence_references`: file paths, screenshot paths, command output
  summaries, model labels, state/edge counts, counterexample ids, ledger entry
  ids, and checked state fields supporting the decision;
- `role_specific_checks`: PM audit, reviewer direct inspection, or FlowGuard
  officer model-boundary/counterexample checks as applicable;
- `risk_or_blindspot_triage`;
- `unresolved_residual_risk_count`;
- `decision`: `approved`, `blocked`, `request_more_evidence`, `mutate_route`,
  or `pm_stop`.

An approval is invalid when `completion_report_only` is true, when direct
sources and probes are empty, or when the evidence cites only worker/completion
reports without the approving role's own checks. PM completion approval must
include a decision-surface audit of the current route/frontier/ledger, stale
evidence, superseded entries, waiver authority, unresolved counts, reviewer
backward replay, standard scenario replay, node acceptance plan coverage, and
risk-or-blindspot triage with zero unresolved residual risks. FlowGuard officer approval must cite
model files, commands or valid unchanged reuse, state/edge counts, invariant
results, missing labels, counterexamples inspected, PM risk tiers,
model-derived review agenda, toolchain/model improvement suggestions,
confidence boundary, and blindspots. Officer model reports are decision
support for the PM: they must classify hard blockers, PM review-required
items, later-gate or terminal-replay items, and non-risk scope notes instead
of making absolute "no risk" claims.

## Final Route-Wide Gate Ledger

`final_route_wide_gate_ledger.json` is the PM-owned terminal closeout ledger.
It is rebuilt from current `.flowpilot/` state before final completion, after
route mutations, repairs, standard raises, and child-skill loop closures have
settled. It is not a static checklist copied from the initial route.

The ledger records:

- active route id and route version;
- source paths used to build the ledger;
- current-route scan and effective-node resolution status;
- child-skill, human-review, product-model, process-model, verification,
  lifecycle, and completion gate entries;
- root acceptance obligations and current proof status;
- standard scenario pack replay status;
- node acceptance plan coverage and PM-risk scenario replay status;
- generated-resource lineage for concept images, visual assets, screenshots,
  route diagrams, model reports, and other generated artifacts;
- required approver, approval status, evidence paths, waiver reasons, blocked
  reasons, superseded-by links, and unresolved reasons for each entry;
- stale evidence count, generated-resource count, unresolved-resource count,
  unresolved count, and unresolved residual risk count;
- residual risk triage: every risk or blindspot classified as fixed, routed to
  repair, current-gate blocker, terminal replay scenario, non-risk note, or
  explicit role-approved exception;
- terminal human backward replay map path and status;
- human-like reviewer backward-check evidence path, including delivered-product
  start, root acceptance segment, parent/module node segments, leaf-node
  segments, node acceptance plan comparisons, and current product checks;
- local parent backward replay paths for parent/module segments, used as
  evidence pointers rather than substitutes for terminal human replay;
- PM segment-decision evidence for every replay segment;
- repair/restart policy evidence showing that any terminal replay repair
  invalidates affected evidence and restarts final review from the delivered
  product unless a narrower impacted-ancestor restart has a PM reason;
- PM ledger approval evidence path;
- `completion_allowed`.

Terminal completion requires `unresolved_count` to be zero, reviewer backward
check to pass through the terminal human backward replay map, PM segment
decisions and repair/restart policy to be recorded, PM ledger approval to be
recorded, the standard scenario pack to be replayed, and
`unresolved_residual_risk_count` to be zero. If route mutation or terminal
replay repair occurs after the ledger is built, the ledger and replay map are
stale and must be rebuilt.

`terminal_human_backward_replay_map.json` is PM-owned terminal review planning
evidence. It is built from the current final ledger and orders the reviewer
walkthrough from the delivered product to root acceptance, parent/module nodes,
and leaf nodes. Every effective node must either appear in a replay segment or
be explained as superseded, waived by the correct role, or out of the current
route. Reviewer reports for these segments must inspect current product
behavior, not only evidence files. PM decisions for each segment are one of
continue, repair, route mutation, correct-role exception, or PM stop. Repair
findings invalidate affected evidence; the default rerun starts final review
from the delivered product, with narrower impacted-ancestor reruns allowed only
when PM records why earlier segments cannot be affected.

## Terminal Closure Suite

`terminal_closure_suite.json` is run after final route-wide ledger approval and
before the terminal completion notice. It prevents a clean review from ending
with stale state or stale automation.

It records:

- latest state, execution frontier, route, ledger, checkpoint, and lifecycle
  paths checked;
- standard scenario and residual-risk replay status;
- terminal human backward replay pass status and repair/restart freshness;
- heartbeat stop or manual-resume no-automation evidence;
- role memory and crew archive status;
- FlowPilot skill improvement report path and written status;
- controlled-stop/completion notice status;
- final report readiness and user-visible summary evidence.

Terminal completion is invalid when this suite is missing, stale, or records an
unresolved blocker.

## FlowPilot Skill Improvement Report

`flowpilot_skill_improvement_observations.jsonl` is an append-only run-level
log for issues with FlowPilot itself. Any role may add an observation at a
node, review, repair, child-skill closure, parent replay, or terminal boundary.
Observations are about the skill, not the target product: unclear protocol
text, weak templates, missing report fields, hard-to-find code paths, model or
tooling friction, automation friction, Cockpit display gaps, or similar future
maintenance notes.

Each observation records the node or gate, reporting role, kind, summary,
observed behavior, temporary compensation used in the current run, candidate
FlowPilot root-repo files, evidence paths, PM triage status, and
`does_not_block_current_project: true`.

`flowpilot_skill_improvement_report.json` is PM-owned and written before the
terminal completion notice. It summarizes the observation log for later manual
FlowPilot root-repo maintenance. The report must also exist when no obvious
skill improvement was observed. Its contents do not require fixing the
FlowPilot root repository before the current project completes. If a FlowPilot
weakness affects the active project, the route may compensate locally and still
finish; true project blockers remain ordinary route blockers.

## Inspection Evidence

Human-like inspection evidence includes a neutral observation before the
pass/fail decision. The observation records what the artifact, screenshot,
output, or exercised feature actually appears to be, including visible content,
window or desktop artifacts, responses to operations, and any required behavior
that was not observable.

Reviewer-owned reports live under `human_reviews/` or the current node's
review-evidence directory. For UI, browser, desktop, visual, localization, or
interactive gates, the report must show direct review, not report-only
acceptance:

- `reviewer_role: human_like_reviewer`;
- `worker_report_only: false`;
- `reviewer_personal_walkthrough_done: true`;
- `opened_surfaces`, `viewport_or_window_sizes`, and `screenshots_viewed`;
- `interaction_paths_exercised` and `unreachable_or_untested_controls`;
- `text_overlap_or_clipping_findings`;
- `layout_density_whitespace_findings`;
- `crowding_or_underfilled_region_findings`;
- `hierarchy_readability_findings`;
- `aesthetic_verdict`: `pass`, `weak`, or `fail` when visual quality matters;
- `design_recommendations`, including concrete repair ideas or an explicit
  statement that no current-gate design repair is needed;
- `obligation_classification`: `current_gate_required`,
  `future_gate_required`, or `nonblocking_note` for each finding.

An approval is invalid when the report only cites worker screenshots, automated
screenshot QA, or interaction smoke logs without the reviewer's personal
walkthrough and visual/layout findings. If the reviewer cannot operate the
surface, the gate blocks or requests more evidence; it does not pass from the
worker report alone.

For generated UI concept targets, the observation also records whether the
candidate appears to be an independent concept, an existing screenshot, an
existing-image variant, a desktop/window capture, old route UI evidence, or
prior failed evidence with cosmetic changes. The later authenticity decision
must cite this observation.

## Lifecycle

`lifecycle/latest.json` is the unified inventory snapshot for pause, restart,
and terminal cleanup. It records the status seen across:

- Codex app automation records for FlowPilot heartbeat automations;
- `.flowpilot/current.json`;
- `.flowpilot/runs/<run-id>/state.json`;
- `.flowpilot/runs/<run-id>/execution_frontier.json`;
- latest heartbeat or manual-resume evidence.

Lifecycle closure is valid only when the snapshot records either no required
actions or explicit waived actions with reasons.

The lifecycle helper does not call Codex automation APIs. It records required
actions so the controller can use the official Codex app automation interface.

## Route

`flow.json` records:

- route id;
- status;
- superseded route if any;
- nodes;
- allowed transitions;
- required gates;
- rollback targets;
- invariants.

## Capability Evidence

Capability evidence should name:

- capability id;
- source skill;
- reason it was invoked;
- inputs;
- outputs;
- verification status;
- dependent route nodes.
