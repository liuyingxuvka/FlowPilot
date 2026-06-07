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
- `runs/<run-id>/packet_ledger.json`
- `runs/<run-id>/route_memory/route_history_index.json`
- `runs/<run-id>/route_memory/pm_prior_path_context.json`
- `role_binding_ledger.json`
- `role_binding_memory/*.json`
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
- `manual_resume/latest.json`
- `startup/startup_mechanical_audit.json`
- `startup/startup_mechanical_audit.json.proof.json`
- `startup/pm_startup_intake_decision.json`
- `lifecycle/latest.json`
- `lifecycle/events.jsonl`
- `research/*/research_package.json`
- `research/*/worker_report.json`
- `research/*/reviewer_report.json`
- `human_reviews/*.json`
- `role_approvals/*.json`
- `checkpoints/*.json`
- `experiments/*/experiment.json`
- `controller_break_glass/index.json`
- `controller_break_glass/incidents/*.json`
- `controller_break_glass/patches/*.json`
- `pm_suggestion_ledger.jsonl`
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
- product-function architecture path;
- root acceptance contract path;
- standard scenario pack path;
- terminal closure suite path;
- final route-wide gate ledger path;
- status;
- latest manual-resume lifecycle receipt;
- last checkpoint;
- next node;
- next action;
- startup runtime intake release hard-gate status.
- packet control-plane status: active packet id, holder, PM decision path,
  router direct-dispatch path, worker result path, review decision path, and
  next legal controller relay action.
- parallel packet batch reconciliation status: active batch id/kind, join
  policy, dependency class, returned and missing packet ids/roles, and whether
  all blocking results have returned. This status is metadata-only and must not
  include packet body text, result body text, findings, commands, or
  recommendations.

It should not store the whole history.

## Parallel Packet Batches

Router records material scan, research, current-node, and PM role-work packet
batches under `runs/<run-id>/packet_batches/`. Each active batch has a
member-status block keyed by packet id and role:

- `packet_count`, `results_returned`, `returned_packet_ids`, and
  `missing_packet_ids`;
- `returned_roles` and `missing_roles` for status summaries;
- `dependency_class`: `blocking`, `advisory`, or `prep-only`;
- `join_policy`, usually `all_results_before_pm_absorption`;
- `partial_results_returned` and `all_results_returned`.

Partial status may drive accurate waiting and display, but it cannot advance a
protected PM/reviewer gate by itself. Blocking batches require every blocking
member result before PM disposition or reviewer gate release. Advisory and
prep-only role-work requests may allow unrelated route work to continue, but
they remain unresolved until PM absorbs, cancels, supersedes, or explicitly
carries the result forward before terminal closure.

Router may reconcile already-written packet/result envelopes before emitting a
wait. Reconciliation is idempotent by batch id, packet id, request id, role, and
result envelope hash. Controller-visible summaries must remain metadata-only.

## Route Memory

`runs/<run-id>/route_memory/route_history_index.json` is a
Controller-generated index of the current route history. It records the active
frontier, route version, completed nodes, effective nodes, node history,
route mutations, superseded nodes, stale evidence ids, review markers,
research/modeling outputs, generated resource counts, unresolved evidence
counts, and source paths.

`runs/<run-id>/route_memory/pm_prior_path_context.json` is the PM-facing brief
built from that index. It records the current route position, completed nodes,
effective nodes, superseded nodes, stale evidence, prior blocks, passes,
research or experiment outputs, and future PM decision requirements.

Both files must include:

- `generated_by: "controller"`;
- `controller_decision_authority: false`;
- `sealed_packet_or_result_bodies_read: false`;
- `source_paths` pointing to current-run source-of-truth files.

Protected PM outputs such as route drafts, resume decisions, node acceptance
plans, route mutations, parent segment decisions, final ledgers, and closure
decisions must include `prior_path_context_review`. That review cites both
route-memory files and states which completed, superseded, stale, blocked, or
experimental history affected the decision.

## Material Artifact Map

`runs/<run-id>/material/material_artifact_map.json` is a router-derived,
run-scoped index for reusable material and decision-support artifacts. It
records metadata for material scan packets, result envelopes, PM formal gate
packages, PM material understanding, research packages and reports, reviewer
reports, self-interrogation indexes, generated-resource ledgers, and related
material artifacts when present.

The map is not an approval artifact. It must include:

- `generated_by: "router"`;
- `controller_decision_authority: false`;
- `controller_may_read_sealed_bodies: false`;
- `sealed_packet_or_result_bodies_read: false`;
- `body_text_excluded: true`;
- `entries` with `entry_id`, `kind`, producer and owner roles, status,
  authority level, safe summary, source refs, envelope refs, body refs, allowed
  role reads, and related entries.

Entries that refer to sealed packet or result bodies may cite body paths,
hashes, visibility, and `requires_runtime_open: true`, but they must not copy
the body text. Workers may use map entries only when the current PM-authored
packet names the entry id in `allowed_material_map_entry_ids`. Reviewers may
use map entries as navigation to concrete source paths or packet-runtime open
receipts, not as source sufficiency by themselves.

`route_history_index.json`, `pm_prior_path_context.json`, and
`final_route_wide_gate_ledger.json` cite the material artifact map when it
exists. They may summarize its counts, but Controller-generated summaries
remain indexes only and cannot replace PM/reviewer/runtime source evidence.

`startup_runtime_intake_release` is the route-start transaction record. A
formal route cannot enter child-skill execution, image generation,
implementation, or route chunks until this block and the matching frontier
block show:

- `hard_gate_required: true`;
- `startup_intake` records the explicit user answer for background-collaboration
  permission plus fixed manual-continuation and chat-display defaults;
- `startup_intake.dialog_stopped_for_user_answers: true`;
- `startup_intake.banner_emitted_after_answers: true`;
- `startup_intake.startup_intake_authority_source: startup_intake_record`;
- `startup_intake.router_must_not_use_chat_history_for_startup_intake: true`;
- `.flowpilot/current.json` points at the same run and `.flowpilot/index.json`
  catalogs it;
- canonical route files, current-run `state.json`, and
  `execution_frontier.json` are
  written for the same active nonterminal route;
- prior top-level control state is absent, unsupported-only, or quarantined and is
  not used as the current run state;
- continuing prior work has a current-run prior-work import packet;
- `role_binding_ledger_current: true`;
- `role_memory_packets_current` is at least the current runtime role count;
- role-binding startup records current-run live background or parallel-agent
  bindings for every runtime-required role after the startup authorization
  decision;
- `continuation_ready: true` with current-run manual-resume lifecycle evidence.
  Automated heartbeat continuation is not a supported current path;
- `startup_mechanical_audit` records Runtime/Router mechanical checks over the
  current sealed intake, path/hash evidence, display status, run/route/frontier
  consistency, role-binding freshness, prior-work boundary, and shadow or
  residual route state;
- `pm_startup_intake_release` records the project manager's node/work-package
  decision from the current mechanical audit. Runtime/Router cannot make the
  PM decision. If the audit has blockers, PM sends remediation back to workers
  and requires a fresh mechanical audit before release;
- `work_beyond_startup_allowed: true`;
- `shadow_route_detected: false`.

`startup_runtime_intake_release.startup_intake` is the pre-banner gate:

- `required: true`;
- `status`: `pending`, `answered`, or `blocked`;
- `asked_before_banner: true`;
- `dialog_stopped_for_user_answers: true` records that the assistant response
  ended immediately after asking for the work request and background-collaboration
  permission, and no startup work ran until the user's later reply;
- `explicit_user_answer_recorded: true` before the PM can open startup;
- `provenance`: exactly `explicit_user_reply`; values such as
  `agent_inferred`, `default`, `prior_route`, `naked`, or
  `single_message_invocation` are invalid;
- `answers.background_collaboration_authorized`: must be `true` for a confirmed
  startup. If it is false, FlowPilot records `startup_blocked` and stops instead
  of using unsupported single-agent continuity;
- `answers.display_surface.answer`: fixed `chat`; this is no longer a
  user-visible startup option;
- `answer_evidence_path`, `answered_at`, and
  `banner_emitted_after_answers: true`.

If any answer is absent, ambiguous, or `pause`, startup remains
`startup_pending_user_answers` and no banner, route work, child skill,
imagegen, implementation, unsupported-path execution, role-binding startup, or
manual-resume claim may proceed. If the questions were asked but the assistant
did not stop and wait for the user's reply, the answer evidence is invalid and
PM must not release startup intake.

`startup_runtime_intake_release.startup_mechanical_audit` is written by
Runtime/Router after current mechanical checks. It is not a PM decision object
and no human-like reviewer owns startup release. It must include:

- `required: true`;
- `check_owner: flowpilot_router`;
- `decision_authority: mechanical_only_no_pm_approval`;
- `audit_path`;
- `proof_path`;
- `audit_status`: `pending`, `ready_for_pm`, or
  `requires_worker_remediation`;
- `blocking_findings`;
- scope flags for startup intake record authority, no-chat-history intake,
  path/hash checks, display status, user authorization, route consistency,
  cleanup boundary, manual-resume lifecycle evidence, role-binding decisions,
  user background-collaboration decision versus actual role-binding state,
  current binding coverage, and shadow/residual state;
- current runtime role bindings must be active, rehydrated, or explicitly
  blocked before work proceeds.

`startup_runtime_intake_release.pm_startup_intake_release` is written by the
project manager after reading the mechanical audit. It must include:

- `required: true`;
- `decision_owner: project_manager`;
- `decision`: `pending`, `release_to_route`, `return_to_worker`, or `blocked`;
- `based_on_startup_mechanical_audit_path`;
- `decision_path`;
- `node_package_decision_recorded`;
- `startup_runtime_release_status`;
- `worker_remediation_required`;
- `released_at` only when the current clean mechanical audit supports release.

`work_beyond_startup_allowed` can become true only after a clean runtime
mechanical audit and a PM-owned startup-intake release decision. Worker
remediation invalidates the prior audit and must be rechecked before PM
releases startup intake.

A route-local file, generated concept, screenshot, or implementation artifact
without matching canonical state/frontier/role-binding/continuation evidence is
a shadow route. Shadow routes are invalid startup evidence and must be
quarantined or superseded before work continues.

`startup_runtime_intake_release.startup_runtime_role_binding` records this
decision:

- `required_by_default: true`;
- `decision`: `background_agents_bound`, `manual_resume_rehydrated`, or
  `blocked`;
- `user_decision_recorded: true` before the PM can open startup;
- `user_authorized_live_start: true`, `live_start_attempted: true`, and
  current-run live binding evidence for the runtime-required roles;
- `blocker` and `evidence_path` for the prompt or failed current binding
  attempt.

## Role-Binding Ledger

`role_binding_ledger.json` records role authority and role memory for a formal
FlowPilot route.

For each currently requested responsibility, the ledger records the role key,
agent id when available, status, authority boundary, latest report path, role
memory path, memory freshness, recovery or replacement rule, and terminal
archive state. It is loaded before formal route work and before resume
recovery.

Role memory packets under `role_binding_memory/*.json` are the durable continuity
state for requested responsibilities. Each packet records:

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

Live host context is not the source of truth. Current role authority comes from
the current-run role-binding ledger plus current host liveness evidence. Manual
resume may reuse an `agent_id` only for same-task continuation when the ledger
still requires that responsibility and `host_liveness_status` proves the role
surface is active. Prior-route or earlier-task `agent_id` values are audit
history only. If a required live binding is unavailable, FlowPilot records the
current blocker or stop; it must not translate old role memory into current
authority or continue through a foreground-only path. Raw transcripts are
optional evidence only; a compact structured memory packet may seed a fresh
current binding transaction, but that replacement cannot approve gates until
Runtime/Router records active host liveness and current packet ownership.

The canonical role ledger status is `active`, `idle`, `blocked`, or `closed`.
Operation result fields may describe the current transaction, such as
`opened_for_current_task`, `resumed_same_task_agent`, `replaced_from_memory`, or
`blocked`, but only `active` host liveness on the current run can satisfy role
readiness. FlowPilot must distinguish "current responsibility has a fresh
addressable role surface" from "memory exists for this responsibility"; memory
alone is never live-agent authority.

## Material Intake Packet

`material_intake_packet.json` is the authorized-worker material inventory and
source-quality packet. It also records a local skill and host capability
inventory as candidate-only route material. The reviewer sufficiency block
must show direct source inspection, not report-only acceptance:

- `reviewer_fact_check_required: true`;
- `direct_material_sources_checked` and `direct_material_samples_checked`;
- non-empty `checked_source_paths` or `runtime_open_receipt_refs` naming what
  the reviewer actually checked;
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
design package. It is written after startup self-interrogation and required
role-binding recovery, and before acceptance contract freeze, route generation,
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
- FlowGuard operator modelability approval or block;
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

- PM current-node high-standard recheck against `high_standard_posture`,
  `highest_achievable_product_target`, `unacceptable_result_review`, and
  `semantic_fidelity_policy`;
- PM decision to raise the current node, add a sibling or repair node, insert
  discovery or validation, ask the user, block, or proceed;
- root acceptance requirements touched by the node;
- child-skill gates and approvers used by the node;
- current-node acceptance criteria;
- concrete experiments, manual walkthroughs, commands, screenshots, or probes;
- linked research packages for material, mechanism, source, validation, or
  evidence gaps that need worker investigation and reviewer source checks;
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
- next node and any explicit repair or restart candidate node;
- current chunk and next chunk;
- user flow diagram metadata: enabled display mode, render policy, highlighted
  current stage, source route/frontier paths, generated Mermaid path, rendered
  route/frontier versions, and staleness after route mutation;
- debug FlowGuard Mermaid metadata, which defaults to disabled and on-request
  only;
- host continuation decision: manual-resume, blocked, or unknown;
- latest PM completion runway, including current gate, downstream steps,
  hard-stop conditions, checkpoint cadence, plan replacement status, and any
  PM stop signal;
- packet control-plane status, including active packet id, holder, PM
  controller reminder presence, router direct-dispatch evidence, worker
  identity, worker result, review decision, ambiguity block, and whether the
  internal packet loop can continue without stopping for the user;
- PM-owned child-skill selection status: local skill inventory path, selection
  manifest path, required/conditional/deferred/rejected decisions, and proof
  that raw local availability did not create route work;
- PM-owned child-skill gate manifest status: route-design discovery from
  PM-selected skills, loaded child-skill files, initial manifest path,
  current-node refined manifest path, required approver assignments,
  reviewer/FlowGuard operator/PM approval evidence, and whether all current child-skill
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
- current node acceptance plan path, PM high-standard recheck status, required
  experiments, and terminal replay obligations;
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
- role-binding ledger path, role memory root, rehydration status,
  current-run resumed, replaced, or blocked responsibility lists, and latest
  project-manager decision, including the PM repair
  strategy interrogation evidence path when a review failure mutates the route;
- route mutation status;
- current manual-resume launcher metadata and lifecycle evidence;
- controlled-stop and completion notice metadata: whether the current route is
  complete, whether a resume notice must be shown on controlled nonterminal
  stop, and the exact manual resume prompt;
- startup runtime intake release metadata matching `state.json`;
- update timestamp.

If the route structure changes, FlowPilot writes a new route version, reruns
FlowGuard checks, rewrites the execution frontier, and syncs the visible Codex
plan from the latest PM completion runway. When the host has a native visible
plan/task-list tool, such as Codex `update_plan`, the sync must call that tool
and record the method, timestamp, route version, PM runway id, item count, and
completion-tail coverage. It updates manual-resume or foreground patrol
metadata only through the current lifecycle command path.

`next_node` is not executable while `unfinished_current_node` is true or
`current_node_completion.advance_allowed` is false. In that state, the next
continuation turn resumes `active_node`, obtains a PM completion runway,
replaces the visible plan
projection from that runway, selects the persisted `current_subnode`,
`next_gate`, and packet recovery state, and continues the packet loop when it
is executable. A continuation record that only says "continue to next gate"
without reviewer/worker/PM packet progress or a concrete blocker is invalid
no-progress evidence.

## Packet Ledger

`packet_ledger.json` is the run-local source of truth for the packet-gated
controller loop. It records the active packet id, packet holder, PM decision
evidence, router direct-dispatch evidence, assigned worker, packet envelope/body
paths and hashes, result envelope/body paths and hashes, review decision
evidence, next legal controller relay action, and whether ambiguous worker
state blocks controller execution. It also records controller relay signatures,
recipient pre-open body checks, holder history, contaminated return-to-sender
records, replacement links, and the latest packet-chain audit.

Packet envelopes live at
`.flowpilot/runs/<run-id>/packets/<packet-id>/packet_envelope.json`. The
envelope is the only packet object the controller may read. It contains
`packet_id`, `from_role`, `to_role`, `node_id`, `is_current_node`,
`body_path`, `body_hash`, `return_to`, `next_holder`,
`controller_allowed_actions`, `controller_forbidden_actions`, and
`controller_relay`. The packet body lives at the envelope `body_path` and is
readable by the target role only after that role verifies the controller relay
signature and body hash. Reviewer/PM access is limited to review, repair, or
completion decisions.

`skills/flowpilot/assets/packet_runtime.py` is the physical writer used by the
installed skill. Its repo wrapper is `scripts/flowpilot_packets.py`. The
runtime writes the envelope and body as separate files, computes `body_hash`
from the body file, writes or updates `packet_ledger.json`, and builds
controller handoff payloads from envelope fields only. A valid review release
records that physical packet files exist and that the controller context
excluded body text. If controller records that it read or executed a sealed
body, the runtime marks the envelope contaminated and requires sender reissue;
post-hoc signing or relabeling does not repair it.

Result envelopes live at
`.flowpilot/runs/<run-id>/packets/<packet-id>/result_envelope.json`. Returning
roles put `packet_id`, `completed_by_role`, `completed_by_agent_id`,
`node_id`, `result_body_path`, `result_body_hash`, and `next_recipient` in the
result envelope, plus the controller relay signature once Controller has
relayed it. Detailed commands, file changes, screenshots, model outputs,
evidence, findings, and open issues go in `result_body.md`. The controller may
relay the result envelope but may not read, execute, summarize, or repair the
body.

`packet_chain_audit.json` is the reviewer-owned audit for a subnode or major
node. It checks packet/result relay signatures, body-open-after-relay records,
holder continuity, absence of private role-to-role mail, and replacement
coverage for contaminated, rejected, unopened, or missing mail. If the audit
finds an unopened or missing required letter, it is sent to PM for a restart
node, repair node, or sender reissue decision.

Each packet entry also contains a mandatory envelope-aware
`role_origin_audit`. The reviewer must fill it before any pass decision by
comparing the PM-authored packet envelope, router direct-dispatch evidence,
`packet_envelope.to_role`, assigned worker or authorized role,
`result_envelope.completed_by_role`, `completed_by_agent_id`, and actual
result author evidence. Packet and result body hashes must match their
envelopes, and stale bodies after route mutation block acceptance. A
controller, unknown, or mismatched result author sets
`invalid_role_origin_blocked: true`, requires a controller-boundary warning,
and sends the packet back to PM for reissue, repair by the assigned role,
quarantine, route mutation, user block, or stop. Wrong-role work cannot be
cosigned, relabelled, or accepted as "good enough." A packet cannot close while
`role_origin_audit.required_for_every_packet` is true and the audit is absent,
mismatched, hash-invalid, or stale.

Manual resume and foreground patrol load the packet ledger before asking PM for
the current decision and must audit the mail chain without opening bodies. The
controller may not mint packets, finish worker packets, or advance from
controller-origin evidence. If PM issues a packet, the ledger must show
`controller_reminder`, router direct-dispatch preflight, controller relay
signature, and recipient body-open record before worker execution. If a worker
result exists, the next action is controller-relayed reviewer review. If packet holder, relay
signature, body-open record, or worker-result state is ambiguous, the next
action is PM recovery/reissue, not controller execution.

On any controlled stop before terminal completion, the frontier stores a
`controlled_stop_notice` packet. Current manual-resume mode records whether a
foreground patrol receipt is active and instructs the user to type
`continue FlowPilot`. Terminal completion stores a completion notice instead
of a resume prompt.

Before a terminal run is finally observed as closed, stopped, cancelled, or a
protocol dead end, FlowPilot writes a run-scoped final summary receipt:

- `.flowpilot/runs/<run-id>/final_summary.md`;
- `.flowpilot/runs/<run-id>/final_summary.json`;
- `.flowpilot/index.json` fields `final_summary_path`,
  `final_summary_json_path`, `final_summary_sha256`, and
  `flowpilot_project_url`.

`final_summary.md` must start with:

```text
Generated with [FlowPilot](https://github.com/liuyingxuvka/FlowPilot) - a project-control workflow for AI coding agents.
```

The terminal summary action is the only time the Controller may read all files
under the current run root as one summary source. The read scope is
`current_run_root_all_files`. It does not allow route mutation, gate approval,
new project evidence, role opening, or writes outside the final summary files,
`.flowpilot/index.json`, `.flowpilot/current.json`, and router state.

The execution frontier stores the native plan sync status separately from the
PM runway evidence. `synced_to_visible_plan` requires native plan tool evidence
when available or an explicit no-native-tool blocker/receipt when unavailable.
It also records whether the projection includes downstream runway depth; a
current-gate-only projection is invalid for formal continuation.

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
Runtime/Router checks `.flowpilot/current.json`, `.flowpilot/index.json`,
current-run `state.json`, `execution_frontier.json`,
`routes/<active-route>/flow.json`, `role_binding_ledger.json`, all role memory
packets, startup intake path/hash evidence, display status, continuation
evidence, current manual-resume lifecycle evidence, requested cleanup evidence,
and prior-work import boundary when continuing. Runtime/Router then writes
`startup/startup_mechanical_audit.json` and its proof inside the current run.

The PM reads the current mechanical audit. If it has blockers, PM returns the
work to workers and requires a fresh audit after remediation. If it is clean,
PM writes `startup/pm_startup_intake_decision.json` inside the current run and
updates state plus frontier so downstream work can check
`work_beyond_startup_allowed`.

## Adversarial Approval Evidence

`role_approvals/*.json` is the canonical evidence family for any PM,
human-like reviewer, FlowGuard operator, or FlowGuard operator
approval that is not already embedded in a richer role-owned report. Every
approval gate may reference one of these files through
`independent_validation_evidence_path`.

Each approval evidence object includes:

- `approval_id`, `run_id`, `route_id`, `node_id`, and `gate_id`;
- `approver_role`: `project_manager`, `human_like_reviewer`,
  `flowguard_operator`, or `flowguard_operator`;
- `approval_scope`: route, material, product architecture, child-skill gate,
  process model, product model, human review, parent backward review,
  startup intake release, repair, final ledger, lifecycle, or completion;
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
  FlowGuard operator model-boundary/counterexample checks as applicable;
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
risk-or-blindspot triage with zero unresolved residual risks. FlowGuard operator approval must cite
model files, commands or valid unchanged reuse, state/edge counts, invariant
results, missing labels, counterexamples inspected, PM risk tiers,
model-derived review agenda, toolchain/model improvement suggestions,
confidence boundary, and blindspots. FlowGuard operator model reports are decision
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
with stale state, stale lifecycle evidence, or stale resume binding.

It records:

- latest state, execution frontier, route, ledger, checkpoint, and lifecycle
  paths checked;
- standard scenario and residual-risk replay status;
- terminal human backward replay pass status and repair/restart freshness;
- manual-resume no-automation evidence;
- role memory and role binding archive status;
- FlowPilot skill improvement report path and written status;
- controlled-stop/completion notice status;
- final report readiness and user-visible summary evidence.

Terminal completion is invalid when this suite is missing, stale, or records an
unresolved blocker.

## Controller Break-Glass Records

`controller_break_glass/` is a run-scoped development-mode emergency area for
FlowPilot control-plane failures. It is not normal project evidence and cannot
approve gates, close nodes, mutate routes, read sealed bodies, or repair
target-project work.

`controller_break_glass/incidents/*.json` uses
`flowpilot.controller_break_glass_incident.v1`. Each incident records why the
normal control flow appeared broken, which normal repair lanes were checked,
which Controller-visible sources were inspected, the suspected FlowPilot
control-plane defect, allowed reads/writes, forbidden actions, validation plan,
exit criteria, related patch ids, and final disposition.

`controller_break_glass/patches/*.json` uses
`flowpilot.controller_break_glass_patch.v1`. Each patch records the incident id,
temporary compensation kind, touched paths, validation evidence, rollback notes,
final disposition, and whether a permanent FlowPilot root fix remains needed.

`controller_break_glass/index.json` lists incidents and patches for terminal
review. Terminal closure or the FlowPilot skill improvement report must disclose
any current-run break-glass use and its temporary compensation status.

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

## PM Suggestion Ledger

`pm_suggestion_ledger.jsonl` is the run-scoped ledger for reviewer, worker, and
FlowGuard operator suggestions that need Project Manager attention. It is
separate from sealed packet/result bodies; entries may cite packet envelopes,
result envelopes, review reports, model reports, evidence files, commands, or
state references, but must not copy sealed body content.

Each entry uses `flowpilot.pm_suggestion_item.v1` and records:

- source role and source output reference;
- suggestion summary and evidence references;
- classification: `current_gate_blocker`, `current_node_improvement`,
  `future_route_candidate`, `nonblocking_note`, or
  `flowpilot_skill_improvement`;
- authority basis, including whether a reviewer found a minimum-standard
  failure, a FlowGuard operator reported a formal model-gate blocker, or a
  worker/FlowGuard operator note is advisory only;
- impact triage: local minor change, current-node adjustment, route or
  acceptance change, or product behavior/state change, plus whether PM
  considered FlowGuard operator product-modeling and why;
- PM disposition: `adopt_now`, `repair_or_reissue`, `mutate_route`,
  `defer_to_named_node`, `reject_with_reason`, `waive_with_authority`,
  `stop_for_user`, or `record_for_flowpilot_maintenance`;
- closure status and closure evidence.

Current-gate blockers block gate closure until repaired and rechecked by the
same review class, waived with authority, routed through mutation, or stopped
for the user. Deferred suggestions must name a downstream node or gate. Rejected
suggestions must include a PM reason. FlowPilot-skill improvement suggestions
link to `flowpilot_skill_improvement_report.json` and do not block the current
project unless PM separately classifies a true current-project blocker.
Final route-wide ledger construction and terminal closure require a clean PM
suggestion ledger: every item has a final PM disposition, current-gate blockers
are closed or stopped, and role authority is valid for the classification.

For generated UI concept targets, the observation also records whether the
candidate appears to be an independent concept, an existing screenshot, an
existing-image variant, a desktop/window capture, old route UI evidence, or
prior failed evidence with cosmetic changes. The later authenticity decision
must cite this observation.

## Lifecycle

`lifecycle/latest.json` is the unified inventory snapshot for pause, restart,
and terminal cleanup. It records the status seen across:

- current FlowPilot manual-resume binding records;
- `.flowpilot/current.json`;
- `.flowpilot/runs/<run-id>/state.json`;
- `.flowpilot/runs/<run-id>/execution_frontier.json`;
- latest manual-resume evidence.

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
