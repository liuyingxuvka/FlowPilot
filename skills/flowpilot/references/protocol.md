# FlowPilot Protocol Reference

This reference is the compact operator protocol for the `flowpilot` skill. The
long-form public explanation lives in `docs/protocol.md`.

## Startup

1. On FlowPilot invocation, enter `startup_pending_user_answers`.
2. Ask the three startup questions:
   - background agents: allow six live background subagents, or use
     single-agent six-role continuity for this run;
   - scheduled continuation: allow heartbeat/automation jobs, or use manual
     resume only for this run;
   - display surface: open Cockpit UI immediately when startup state is ready,
     or use chat route signs for this run.
   End the assistant response immediately after these questions. Do not inspect
   files, start tools, create route state, launch subagents, probe heartbeat, or
   show the banner in the same response. FlowPilot remains in
  `startup_pending_user_answers` until the user's later reply supplies all
  three answers. Do not ask the user to choose a mode.
3. Record the explicit answer set in state/frontier startup activation
   evidence. A compact later user reply may satisfy all three only when the
   choices are explicit.
4. Emit the fenced `FlowPilot` ASCII startup banner in chat. The banner means
   the startup-question gate is open.
5. Create or load `.flowpilot/`, allocate a fresh `run_id`, create
   `.flowpilot/runs/<run-id>/`, write `.flowpilot/current.json`, and update
   `.flowpilot/index.json`. These top-level files are only pointers/catalogs.
   Current control state must live under the run directory. The active-run
   resolver is authoritative: read `.flowpilot/current.json`, then load
   `.flowpilot/runs/<run-id>/`. Old top-level state files are legacy evidence
   only and must not silently override an active run. Continuing prior
   work still creates a new run and writes a
   `.flowpilot/runs/<run-id>/prior_work_import_packet.json`; old state,
   routes, agent IDs, screenshots, icons, or evidence may be referenced as
   read-only input only and must not become current control state.
6. Commit the showcase-grade long-horizon floor.
7. Run visible full grill-me before freezing the contract. In the same round,
   draft the intended floor, seed the improvement candidate pool, seed the
   initial validation direction, and surface product-function questions. Do
   not freeze the contract yet.
8. Create the fixed six-agent crew for the new formal FlowPilot task and write
   `.flowpilot/runs/<run-id>/crew_ledger.json` plus one compact role memory
   packet under `.flowpilot/runs/<run-id>/crew_memory/` for project manager,
   human-like reviewer, process
   FlowGuard officer, product FlowGuard officer, worker A, and worker B. Each
   role record separates `role_key` for authority/routing, `display_name` for
   chat/UI labels, and diagnostic-only `agent_id` for same-task continuation
   diagnostics. At formal startup, all live background subagent IDs must be
   freshly spawned for this FlowPilot task after the startup answers and
   current route allocation. IDs from prior routes, old crew ledgers, or older
   role-memory packets are audit history only and must not be resumed,
   relabeled, or counted as current live-agent evidence.
9. Ask the project manager to ratify the startup self-interrogation and own
   material understanding, product-function architecture, route,
   heartbeat-resume, repair, and completion decisions from this point forward.
   The main assistant becomes the controller for packet flow, not the default
   implementation worker.
10. Before PM product-function synthesis or route decisions, require a
    PM-authored material-intake packet envelope/body pair and reviewer dispatch approval.
    The authorized worker writes
    `.flowpilot/runs/<run-id>/material_intake_packet.json`: inventory,
    source summaries, source authority/freshness/contradiction classification,
    local skill and host capability inventory, coverage map, and unread or
    deferred materials. Local skills are candidate resources only until PM
    selection. Controller-origin material intake is invalid unless a PM packet
    explicitly assigns that administrative task to the controller and the
    reviewer approves dispatch.
11. The human-like reviewer approves or blocks material sufficiency. The packet
    is PM-ready only when obvious sources are not missing, large materials are
    sampled or scoped honestly, summaries are specific, contradictions and
    uncertainty are visible, and PM route design would not be misled.
12. The project manager writes `.flowpilot/runs/<run-id>/pm_material_understanding.json` from
    the reviewed packet and user intent. It records source-claim matrix, open
    questions, material complexity (`simple`, `normal`, or `messy/raw`), and
    whether materials require a formal discovery, cleanup, modeling,
    validation, or research subtree before implementation.
13. When a material, mechanism, source, validation, reconciliation, or
    experiment gap affects dependent decisions, PM writes a formal research
    package under `.flowpilot/runs/<run-id>/research/<research-package-id>/`.
    The package names the decision, route impact, allowed source/tool
    boundaries, worker owner, stop conditions, and reviewer direct-check
    requirements. Worker output is only a pointer. The human-like reviewer
    directly checks original sources, search results, local files, logs,
    screenshots, or experiment outputs. Reviewer failure returns to worker
    rework, follow-up research, route mutation, user clarification, or block.
    PM may use the result only after reviewer sufficiency passes and PM records
    absorption or route mutation.
14. Require the project manager to write
    `.flowpilot/runs/<run-id>/product_function_architecture.json` before contract freeze:
    user-task map, product capability map, feature necessity decisions,
    display rationale, missing high-value feature review, negative scope, and
    functional acceptance matrix.
14. Have the product FlowGuard officer approve or block modelability and
    product-function coverage, and have the human-like reviewer challenge
    usefulness, unnecessary display, missing workflow support, bad defaults,
    and failure-state gaps. If either blocks, the project manager revises the
    architecture before the route continues.

    Before freezing the contract, the project manager also writes
    `.flowpilot/runs/<run-id>/root_acceptance_contract.json` and selects
    `.flowpilot/runs/<run-id>/standard_scenario_pack.json`. The root contract
    turns the PM's important hard requirements into early proof obligations.
    The scenario pack defines the baseline happy-path, edge/failure,
    regression, and PM-risk replay set that terminal review must exercise.
15. Freeze the acceptance contract as a floor in
    `.flowpilot/runs/<run-id>/contract.md` from
    the approved product-function architecture and startup interrogation.
16. Write the capabilities manifest, including material handoff and
    product-function architecture evidence.
17. Ask the project manager to write the PM child-skill selection manifest from
    the product capability map, frozen contract, capabilities manifest, and
    local skill inventory. The PM classifies candidate skills as `required`,
    `conditional`, `deferred`, or `rejected`; local availability alone never
    creates route work.
18. Ask the project manager to discover child-skill gates only from
    PM-selected skills, load each likely child skill's `SKILL.md` and relevant
    references, and extract a child-skill gate manifest with key stages,
    required checks, standards, evidence needs, skipped-reference reasons,
    visible mini-route milestones, and required approver roles.
19. Have the human-like reviewer, process FlowGuard officer, and product
    FlowGuard officer review their slices of the manifest. The project manager
    then approves or blocks manifest inclusion in route modeling, the
    execution frontier, and the PM runway. The controller and workers are
    forbidden approvers for child-skill gates.
20. Verify the real `flowguard` package and required skills.
21. Inspect dependency/tool needs and write a dependency plan.
22. Install only the minimum dependencies needed for FlowPilot itself and the
    current route/model checks.
23. Defer future route, chunk, or native-build dependencies until the node or
    check that actually needs them.
24. Probe host continuation capability only after the scheduled-continuation
    startup answer is recorded. If the user allowed scheduled continuation and
    setup fails, stop and ask for a new decision instead of silently switching
    to manual resume.
25. If the user allowed scheduled continuation and the host supports real
    wakeups, create the automated continuation: a stable one-minute heartbeat
    launcher. The launcher loads persisted route/frontier state and the packet
    ledger rather than carrying route-specific next-jump instructions in its
    prompt. On wakeup it loads role memory, resumes or replaces each role from
    that memory, then asks the project manager for the current `PM_DECISION`
    and completion-oriented runway. The controller may relay only PM packets,
    reviewer dispatch/review decisions, worker results, visible-plan sync, and
    status/control-stop notices.
26. If the user selected manual resume, record `manual-resume` mode and do not
    create heartbeat automation.
27. Record the controlled-stop notice policy: completed routes emit a
    completion notice; controlled nonterminal stops emit a resume notice that
    says whether to wait for heartbeat or type `continue FlowPilot`.
28. Ask the project manager for the initial route-design decision.
29. Ask the process FlowGuard officer to use FlowGuard as process designer for
    the active route.
30. Generate a candidate route tree from the approved product-function
    architecture, contract, and PM-approved child-skill gate manifest.
31. The process FlowGuard officer authors, runs, interprets, and approves or
    blocks the root development-process model against the candidate tree.
32. The product FlowGuard officer authors, runs, interprets, and approves or
    blocks the root product-function model for the target product or workflow
    behavior, using the approved product-function architecture as a source
    artifact.
32. The matching officers inspect failures for both model scopes and write
    approve/block reports.
33. Freeze the checked candidate as the active route JSON and write derived
    Markdown summary.
34. Write `.flowpilot/runs/<run-id>/execution_frontier.json` from the checked route, active
    node, next node, current mainline, fallback, checks before advance, and the
    current-node completion guard. Include actor authority for the current
    gate: draft owner, execution owner, required approver, forbidden
    approvers, approval status, approval evidence path, independent validation
    requirement, completion report-only prohibition, and independent validation
    evidence path. Also record the
    latest PM completion runway, including downstream steps, hard-stop
    conditions, checkpoint cadence, and any PM stop signal.
35. Sync the visible Codex plan list from the latest PM completion runway,
    replacing the current plan projection while preserving old decisions and
    checkpoints as history. If the host exposes a native visible plan/task
    list tool, such as Codex `update_plan`, call that tool immediately with
    the PM runway before executing work. Persisted `.flowpilot` evidence alone
    is not enough when the native tool exists.
36. Emit the simplified English FlowPilot Route Sign Mermaid in chat when this
    is startup, a new major `flow.json` route-node entry, parent/module or leaf
    route-node entry, PM current-node work brief, legacy key node change, route
    mutation, review/validation failure return, completion review, or user
    request, unless Cockpit UI is open and showing the same graph. Major node
    means an effective node in the current route/mainline, not an internal
    subnode, micro-step, or heartbeat tick. Include active route, active node, next jumps,
    checks, fallback or repair branches, continuation state, and acceptance
    delta as nearby text. If the route returns for repair, the Mermaid must
    show that return edge and the reviewer must check the visible chat block
    before the node can advance. Generated files or display packets alone do
    not satisfy this gate.
37. Run the startup activation review before any child-skill execution, image
    generation, implementation, formal route chunk, or completion work. There
    is no third startup opener or runtime startup-check script. The human-like
    reviewer personally checks facts and writes
    `.flowpilot/runs/<run-id>/startup_review/latest.json`; the project manager is the only
    role that may write `.flowpilot/runs/<run-id>/startup_pm_gate/latest.json` and set
    `work_beyond_startup_allowed: true`.

    The human-like reviewer report must verify matching active route,
    canonical current-run state, execution frontier, current six-role crew
    ledger, current role memory, `.flowpilot/current.json`,
    `.flowpilot/index.json`, the run manifest, prior-work import packet when
    continuing, the three explicit startup answers, stop-and-wait evidence,
    banner-after-answers evidence, live-subagent startup freshness,
    continuation readiness, and `startup_activation` records in state and
    frontier. It must also verify old top-level control state is absent,
    legacy-only, or quarantined and is not being used as current state. It
    must also check user authorization against actual state,
    old-route and old-asset cleanup when a clean start was requested, the real
    route heartbeat automation at one minute when scheduled continuation is
    allowed, manual-resume evidence when manual continuation is selected,
    residual route state, and shadow-route evidence. It must bind the
    background-agent answer to actual
    subagent state: if the user allowed background agents, verify six live
    role-bearing subagents were freshly spawned for this FlowPilot task after
    that user decision and after current route allocation, and verify none of
    their `agent_id` values comes from prior route ledgers or older role-memory
    packets. If the user chose single-agent continuity, verify the explicit
    fallback authorization and do not claim live subagents. The reviewer writes a report only; the reviewer
    does not approve startup and does not open the gate. The project manager
    reads the report. If it contains blockers, PM sends remediation items back
    to authorized workers through a PM packet and requires a new factual reviewer report. If it
    is clean, PM writes `pm_start_gate` evidence opening startup from that
    exact report.

    Work beyond startup is illegal until the PM records
    `work_beyond_startup_allowed: true` from the clean factual report. If the
    three answers are incomplete, the prompt did not stop for the user's
    reply, answers are inconsistent with subagent/continuation evidence, or
    required cleanup evidence is missing, route the issue back through PM and
    workers. A route-local file without matching canonical
    state/frontier/crew/continuation evidence is a shadow route and must be
    quarantined or superseded before continuing.
38. Start only the first packet-gated chunk whose continuation mode is known.
    The PM writes a physical packet envelope/body pair, the reviewer approves dispatch,
    the worker receives only that envelope plus the body file addressed to its role,
    and the worker returns a physical result envelope/body pair before stopping for the
    next packet. The controller relays result envelope -> reviewer -> PM ->
    next packet envelope and continues internally when `stop_for_user: false`.
    The installed runtime is `skills/flowpilot/assets/packet_runtime.py`; the
    repository wrapper is `scripts/flowpilot_packets.py`. Missing physical
    files or body text in controller context blocks dispatch.
    Every PM decision to the controller must include a controller reminder:
    the main assistant is only the packet-flow controller and must not
    implement, install, edit, test, approve, or advance from its own evidence.
    If the reminder is missing, the controller requests a corrected PM decision
    instead of dispatching work.
    Every controller-to-sub-agent message must also include a role reminder for
    that recipient, and every sub-agent response must echo both the controller
    boundary and its own role boundary. Missing reminders are blockers, not
    cosmetic omissions.
    On heartbeat or manual resume, the controller reloads the packet ledger and
    resumes from the packet holder. If a worker result is already present, it
    goes to reviewer. If holder, dispatch evidence, worker identity, or result
    state is unclear, the controller asks PM for recovery/reissue/reassignment
    and must not finish the packet itself.
39. Start only the first chunk whose continuation mode is known. Automated
    routes use heartbeat restore; manual-resume routes load the same
    state/frontier/crew-memory inputs in the active turn. In both modes the
    project manager issues a completion-oriented runway, the controller syncs that
    runway into the visible plan, and focused parent grill-me, parent-subtree
    review, unfinished-current-node recovery check, focused node grill-me,
    lightweight self-check, quality package, child-skill gates when needed,
    dual-layer product/process gates, human-like inspection gates, and
    verification have been defined.

Recommended explicit invocation for public docs, README examples, and GitHub
usage:

```text
Use FlowPilot. Ask the startup questions first.
```

FlowPilot invocation only opens the three-question startup prompt. It is not
authorization for background agents, fallback execution,
scheduled jobs, manual resume, or a default display surface. The assistant must stop immediately after
asking those questions, and the banner is emitted only after the later user
answer set is complete.

## Material Intake And PM Handoff

Before PM product-function architecture, contract freeze, route generation, or
capability routing, the PM writes a material-intake packet envelope/body pair,
the reviewer approves dispatch, and an authorized worker writes
`.flowpilot/runs/<run-id>/material_intake_packet.json`. It inventories user-provided and
repository-local materials, summarizes what each source appears to contain,
classifies authority, freshness, completeness, contradictions, privacy/safety
notes, inventories locally installed skills and host capabilities as
candidate-only resources, maps coverage to user intent, and names unread or
deferred materials. Controller-origin material intake cannot close the gate
unless the PM packet explicitly assigns that administrative action and the
reviewer approves dispatch.

The human-like reviewer approves material sufficiency before the project
manager uses the packet. The reviewer must open or sample the actual materials
behind the packet, not only read the worker's packet. The reviewer blocks if
obvious sources are missing, large sources are not scoped honestly, summaries
are shallow, contradictions or uncertainty are hidden, or the packet would
mislead route design.

The project manager then writes `.flowpilot/pm_material_understanding.json`.
It is an interpretive handoff: source-claim matrix, open questions, material
complexity (`simple`, `normal`, or `messy/raw`), route consequence, and whether
formal discovery, cleanup, modeling, validation, research, or reconciliation
nodes are required before implementation. Messy/raw materials cannot feed a
route decision directly without that discovery decision.

If the PM cannot safely decide from reviewed materials, the gap becomes a
PM-owned research package instead of a loose note. The package records the
decision to be made, the route impact, allowed local/user/web/browser/source
types, host capability decision, private/paid/account hard gates, worker owner,
stop conditions, and reviewer direct-check requirements. Worker reports must
include raw evidence pointers, negative findings, contradictions, and
confidence boundaries. The reviewer must directly check original sources or
experiment outputs; a summary-only pass is invalid. If the reviewer blocks,
the PM returns concrete rework to the worker, inserts follow-up research or
validation, mutates the route, asks the user, or blocks. Product architecture,
route generation, node acceptance, and implementation that depend on the gap
remain blocked until reviewer sufficiency passes and PM records how the result
was absorbed or how the route changed.

## Product Function Architecture Gate

After the material handoff and before contract freeze, the project manager
writes `.flowpilot/runs/<run-id>/product_function_architecture.json`. Required contents:

- high-standard posture: FlowPilot invocation means the project is important,
  the PM sets the highest reasonably achievable standard for strong AI workers,
  and rough-demo completion is not acceptable;
- highest achievable product target and unacceptable-result review: what the
  strongest feasible result should look like, and which placeholder, fake,
  thin, misleading, unstable, incomplete, or low-quality outputs must fail;
- semantic fidelity policy: map user goals to material support, identify
  forbidden downgrades, and route material gaps to discovery, staged delivery
  with explicit gaps, user clarification, or block rather than silently
  redefining the requested product;
- user-task map;
- product capability map;
- feature decisions marked `must`, `should`, `optional`, or `reject`;
- display rationale for every visible label, control, status, card, alert,
  empty state, and persistent text;
- missing high-value feature review;
- negative scope and rejected displays;
- functional acceptance matrix with inputs, outputs, states, failure cases,
  checks, and evidence paths.

The product FlowGuard officer approves modelability and product-function
coverage. The human-like reviewer challenges usefulness, ambition, and
completeness by comparing the PM architecture against the user request,
inspected materials, and expected workflow reality: unnecessary display,
missing workflow support, bad defaults, hidden semantic downgrades, placeholder
artifacts that would be embarrassing to show, weak failure states, and user-task
gaps. Contract freeze, route generation, capability routing, and implementation
are blocked until both review slices are resolved.

## PM Child-Skill Selection

After the product-function architecture and capabilities manifest, and before
child-skill gate extraction, the project manager writes
`.flowpilot/runs/<run-id>/pm_child_skill_selection.json`. This artifact is the
boundary between "the machine has this skill" and "the route should use this
skill."

The PM reads the product capability map, frozen contract, capabilities
manifest, and local skill inventory, then classifies candidate skills as
`required`, `conditional`, `deferred`, or `rejected`. Required and conditional
skills name the product capabilities they support, trigger conditions,
hard-gate or user-approval needs, files to load, and references deferred with
reason. Available but unused skills receive negative-selection reasons so the
route does not grow accidental UI, publishing, README, promotion, or other
domain work merely because those skills exist locally.

Child-skill route discovery may proceed only from this PM selection manifest.
If a later node reveals a new needed skill, the PM updates the selection
manifest before the current-node child-skill manifest is refined.

## Root Acceptance Contract And Standard Scenarios

Before contract freeze, the project manager writes
`.flowpilot/runs/<run-id>/root_acceptance_contract.json`. It records the small
set of PM-owned root requirements that must become route-wide proof
obligations: why each requirement matters, the acceptance threshold, the
minimum experiment or inspection evidence, the owner, the required approver,
and the terminal replay expectation.

The project manager also selects or writes
`.flowpilot/runs/<run-id>/standard_scenario_pack.json`. This is the compensating
scenario baseline used when individual nodes cannot know every downstream
detail at startup. It includes happy-path, boundary/failure, regression,
state/lifecycle, localization/accessibility, and user-risk scenarios when
applicable. Terminal review replays this pack plus any risk scenarios added by
node acceptance plans.

## Node Acceptance Plans

Before a formal route chunk or implementation-bearing node starts, FlowPilot
first refreshes and visibly displays the current-node FlowPilot Route Sign from
the active `flow.json` and `execution_frontier.json`. Use `major_node_entry` for
ordinary major route nodes, `parent_node_entry` for parent/module entry,
`leaf_node_entry` for leaf entry, and `pm_work_brief` when the PM issues the
current-node work brief. When Cockpit UI is closed or not proven visible, paste
the chat-ready Mermaid block before any tool call or file edit for that node.
Generated diagram files alone do not satisfy node entry.

After the visible route-sign gate passes and before the node acceptance plan is
approved, the project manager performs a current-node high-standard recheck.
For every major, parent, module, and leaf node, PM reopens
`product_function_architecture.json` and checks the current node against
`high_standard_posture`, `highest_achievable_product_target`,
`unacceptable_result_review`, and `semantic_fidelity_policy`. The recheck must
answer how the node advances the strongest feasible target, what low-quality or
placeholder result it could degrade into, whether material or implementation
constraints are silently lowering semantic fidelity, and whether PM should raise
the node, add a sibling or repair node, insert discovery or validation, ask the
user, block, or proceed.

Only after that recheck does the project manager write the node's
`node_acceptance_plan.json`. It maps the current node to the root acceptance
contract, child-skill gates, risk hypotheses, concrete experiments or manual
walkthroughs, required evidence, and required approver.

The plan is intentionally node-local. It must not explode every future route
obligation up front, but every current-node requirement, known risk, material
gap, mechanism gap, evidence gap, and dependency on later review must be named.
If a gap needs worker search, source reconciliation, external lookup, or an
experiment, the plan links an approved research package or requires PM to write
one before dependent work proceeds. PM-risk items from these plans become
terminal replay scenarios unless resolved earlier by repair and recheck.

## FlowPilot Skill Improvement Notes

Each node, repair, review, child-skill closure, parent replay, controlled
pause, and terminal boundary may expose issues in FlowPilot itself: unclear
protocol, weak templates, missing fields, hard-to-find code paths,
model/tooling friction, evidence governance gaps, automation friction,
pause/restart gaps, or Cockpit display gaps. Any role may append a concise
observation to
`.flowpilot/runs/<run-id>/flowpilot_skill_improvement_observations.jsonl`.
Initialize `.flowpilot/runs/<run-id>/flowpilot_skill_improvement_report.json`
at run start with status `live_updating` so paused runs still preserve the
lesson.

These observations do not block the current project and do not require fixing
the FlowPilot root repository inside the current run. If a small FlowPilot
weakness affects the active project, compensate locally, record the
observation, and continue. At terminal closure, the project manager writes
`.flowpilot/runs/<run-id>/flowpilot_skill_improvement_report.json` for later
manual FlowPilot maintenance, including the case where no obvious skill issue
was observed.

## Defect And Evidence Governance

Every formal run initializes
`.flowpilot/runs/<run-id>/defects/defect_ledger.json`,
`.flowpilot/runs/<run-id>/defects/defect_events.jsonl`,
`.flowpilot/runs/<run-id>/evidence/evidence_ledger.json`, and
`.flowpilot/runs/<run-id>/evidence/evidence_events.jsonl`,
`.flowpilot/runs/<run-id>/generated_resource_ledger.json`, and
`.flowpilot/runs/<run-id>/activity_stream.jsonl` before review, repair, pause,
or terminal closure. Any discovering role writes the first defect event. PM
triages severity, owner, route impact, and close condition. Same-class
reviewer/officer recheck is required before PM closes a blocker.

Blocking defect flow:

```text
open -> accepted/fixing -> fixed_pending_recheck -> closed
```

`open` blockers and `fixed_pending_recheck` items block node closure, route
advancement, final ledger approval, and terminal completion. Evidence is
classified separately as `valid`, `invalid`, `stale`, or `superseded`, with
source kind `live_project`, `fixture`, `synthetic`, `historical`, or
`generated_concept`. Fixture evidence may prove capability but must be
disclosed separately from live-project proof. Invalid or stale evidence cannot
close a current gate.

Every generated concept, image, icon, screenshot, diagram, model output, or
similar resource is registered in the generated resource ledger immediately
when created. Each item records origin, path, owning node or gate, and one
disposition. `pending` is allowed only before closure. Terminal dispositions are
`consumed_by_implementation`, `included_in_final_output`, `qa_evidence`,
`flowguard_evidence`, `user_flow_diagram`, `superseded`, `quarantined`, or
`discarded_with_reason`. Terminal completion may only close after every
generated resource has a current terminal disposition and reason.

The activity stream is append-only. PM decisions, reviewer holds/releases and
reports, officer modeling actions, worker reports, route mutations, checkpoint
writes, heartbeat/manual-resume actions, and terminal closure events append
progress records as they happen. Cockpit and chat progress displays read from
this stream plus current route/frontier state, so users see progress without
manual refresh or ad hoc status reconstruction.

## Parent Backward Replay

Do not infer "important" parent nodes from semantics. The trigger is purely
route structure: every effective route node with children is a parent/composite
node and must run a local backward replay before that parent closes. Labels
such as high risk, integration, feature, or downstream dependency may make the
review more detailed, but they do not decide whether review is required.

When the checked route is created or mutated, the project manager enumerates
all effective parent/composite nodes from `flow.json` into the frontier. As
each parent reaches closure, PM writes
`.flowpilot/runs/<run-id>/routes/<route-id>/nodes/<parent-node-id>/parent_backward_replay.json`.
The human-like reviewer starts from the parent-level delivered result, then
checks the parent goal, child rollup, child evidence, child node acceptance
plans, and current product behavior. Child-local passes are pointers only.

After each replay segment, PM records continue, repair an existing child, add
or route to a sibling child, rebuild the child subtree, bubble impact to the
next parent, or PM stop. Repair or route mutation makes affected child evidence
and parent rollups stale, and the same parent replay reruns before closure.
Terminal review later consumes these local parent replays as evidence pointers
but still independently replays the final delivered product.

## Universal Adversarial Approval Baseline

Every PM, reviewer, and FlowGuard officer approval must be an independent
adversarial validation event. Completion reports, worker summaries,
screenshots, smoke logs, model-result snippets, and PM summaries are pointers
only; they cannot be the approval basis by themselves.

Each approval record includes `independent_validation` evidence: completion
report only is false; pointer reports consulted; direct sources checked;
state fields, route/frontier/ledger files, screenshots, logs, model files, or
materials checked; commands, probes, walkthroughs, model checks, or samples run;
adversarial hypotheses tested; concrete evidence references;
risk-or-blindspot triage that classifies every finding as fixed, routed to
repair, current-gate blocker, terminal replay scenario, non-risk note, or
explicit role-approved exception; and
approve/block/request-more-evidence/mutate/PM-stop decision.

Approval records must not park real unresolved risks as acceptable residuals.
When a finding is a real risk, the approver sends the route back to repair,
adds a current-node check, adds a terminal replay scenario, requests evidence,
or blocks completion. The completed route can contain resolved issues,
non-risk notes, and explicit role-approved exceptions only.

PM approvals attack route, frontier, ledger, stale evidence, waiver authority,
blockers, downstream consequences, unresolved counts, and consistency with the
frozen user goal. Reviewer approvals attack the artifact, behavior, source
material, output, UI surface, log, screenshot, backend effect, delivered
product, and edge/failure cases directly. FlowGuard officer approvals attack
model boundary, model files, commands or valid unchanged reuse, state/edge
counts, invariant results, missing labels, counterexamples, and blindspots.

An approval without this evidence is pending or blocked. PM cannot launder a
report-only reviewer/officer pass; the correct role must recheck the gate.

The project manager owns reviewer timing. Before worker or officer work that
will later need review, the PM writes a review hold instruction naming the
expected gate and saying the reviewer waits. After authorized output,
verification, and anti-rough-finish evidence are ready, the PM writes a review
release order naming the gate, evidence paths, scope, and required
inspections. Reviewer work before that release is precheck only: it may note
risks for PM, but it cannot open, close, or block the gate.

## Reviewer Fact-Check Baseline

The human-like reviewer is a factual reviewer, not a report reader. For every
reviewer-owned gate, the reviewer may use worker reports as pointers, but must
also inspect the underlying facts appropriate to that gate before writing a
pass, block, challenge, or sufficiency decision.

Reviewer fact checks must name what was directly checked:

- source artifacts or material samples for material sufficiency;
- user request, inspected materials, and expected workflow reality for
  product-function architecture usefulness;
- live startup state, route, frontier, role memory, heartbeat or manual-resume
  evidence, and cleanup boundary for startup;
- loaded child-skill source instructions, mapped gates, evidence plan, actual
  child-skill outputs, and output/evidence match for child-skill gates;
- actual product behavior, rendered output, logs, screenshots, interactions, or
  backend effects for implementation inspections;
- delivered product first, then root acceptance, parent/module nodes, leaf-node
  behavior, node acceptance plans, current route/frontier/ledger/evidence files,
  and PM replay map for terminal human backward replay.

A reviewer decision that cites only a worker/PM summary without direct
fact-check evidence is invalid. PM decisions may rely on reviewer reports only
after those reports identify the factual sources checked and contain no current
gate blockers.

## Execution Loop

Repeat until complete or blocked:

1. Resolve `.flowpilot/current.json`, then load
   `.flowpilot/runs/<run-id>/state.json`,
   `.flowpilot/runs/<run-id>/execution_frontier.json`,
   `.flowpilot/runs/<run-id>/crew_ledger.json`,
   `.flowpilot/runs/<run-id>/crew_memory/`, active route,
   active node, continuation mode, last heartbeat or manual-resume record,
   lifecycle evidence, and last checkpoint.
   `.flowpilot/current.json` to `.flowpilot/runs/<run-id>/` is authoritative;
   top-level legacy state is import or quarantine evidence only and must not
   override the active run.
2. Rehydrate all six role identities and work memories before PM runway work.
   Stored agent ids may be resumed only when they belong to the same active
   FlowPilot task-born cohort. A new formal FlowPilot task must create fresh
   live subagents instead of resuming prior-route IDs. If live agents are
   unavailable, ask for the missing startup/fallback decision before replacing
   roles from memory. Record resumed, replaced, seeded, blocked, and
   unavailable roles in a crew rehydration report covering project manager,
   reviewer, process FlowGuard officer, product FlowGuard officer, worker A,
   and worker B. Do not lazily rehydrate a role only when it is first needed.
   Live background agents are the default startup target; role continuity
   through persisted memory is allowed only after explicit fallback approval.
3. Ask the rehydrated project manager for a completion-oriented runway from
   the current position to project completion. The runway names the current
   gate, downstream steps, hard-stop conditions, checkpoint cadence, and any PM
   stop signal.
4. Confirm the route is checked, summaries are synced, the execution frontier
   matches the active route version, and the visible Codex plan is synced from
   the latest PM runway. The sync record must name the method: native plan tool
   called when available, or explicit chat/`.flowpilot` fallback when no native
   tool exists. The projection must include downstream runway items, not only
   the current gate.
5. If `unfinished_current_node` is true, or
   `current_node_completion.advance_allowed` is false, resume `active_node`.
   Do not jump to `next_node` until the current-node completion guard passes.
   Load the persisted `current_subnode` or `next_gate` selected by the project
   manager for that active node, execute at least that gate in the current
   heartbeat or manual-resume turn when executable, then continue along the PM
   runway as far as hard gates and real execution limits allow. Do not write only a
   future-facing "continue to X" decision while the gate is still executable.
   If the selected gate has draft evidence but lacks the required role's
   approval, request that approval or block; do not let the controller
   self-approve.
6. Confirm no hard gate, issue branch, or unmerged sidecar worker work is open.
7. Confirm automated heartbeat health when supported, or manual-resume
   state/checkpoint freshness when unsupported, then confirm
   unfinished-current-node recovery state. Continuation evidence records host
   kind (`codex_heartbeat_automation`, `windows_scheduled_task`,
   `manual_resume`, or `blocked_unsupported`) and the exact host evidence
   source.
8. Run focused parent-scope grill-me, then rerun the current parent node's
   FlowGuard process model against its existing child subtree and rerun the
   parent product-function model before entering child work.
9. Emit the visible node roadmap in chat before defining implementation work.
10. Run focused node-level grill-me for the active leaf node.
11. Build or refresh the active leaf product-function model and derive tests or
   manual experiments from it.
12. Run a lightweight self-check for the current continuation micro-step.
13. Run the quality package: feature thinness, improvement classification,
    child-skill mini-route visibility, validation strength, and rough-finish
    risk.
14. Before child-skill execution, have the project manager refine the
    PM-owned child-skill gate manifest for the current node, write current
    gate authority records into the execution frontier, and then run
    child-skill conformance gates for any invoked child skill.
15. Define the next chunk's verification before execution.
16. Execute the bounded chunk.
17. Run the declared verification.
18. Run anti-rough-finish review before checkpoint.
19. Run human-like inspection with product context and manual/product-style
    experiments before checkpoint.
20. If inspection fails, grill the finding into a specific issue, grill the
    project manager on repair strategy, ask the project manager for the repair
    route decision, mutate the route, create a repair node, run repair
    process/product models, write repair evidence, and recheck with the same
    inspector class.
21. Fix implementation failures inside the same route when the route still fits.
22. Create a new route version when verification exposes a model gap or
    completion review raises the standard.
23. Refresh role memory packets for every role that made a meaningful decision,
    inspection, model approval, sidecar report, or blocker note in this turn.
    Compact structured summaries are authoritative; raw transcripts are not.
24. Write node completion evidence, set the frontier completion guard to
    `advance_allowed: true`, then write heartbeat or manual-resume evidence and
    checkpoint evidence after verified progress.

FlowPilot uses three self-interrogation depths. Full grill-me is for formal
boundaries: startup product-function architecture and contract freeze, route
mutation or standard expansion, and completion review. Full rounds derive
active layers and require at least 100 questions per active layer. Startup
full grill-me also seeds the improvement candidate pool and initial validation
direction, and feeds the PM product-function architecture, instead of
separate post-freeze interviews for those same topics. Focused grill-me is for phase,
group, module, leaf-node, and child-skill entry and uses 20-40 questions by
default, up to 50 for complex boundaries. Lightweight self-check is for
continuation micro-steps and tiny reversible choices and uses 5-10 questions.
Every round records its tier, scope id, question count, and evidence. Startup
asks whether Cockpit UI or chat should be the primary progress surface. If the
user chose Cockpit, open it immediately after startup route/frontier state is
ready; if the user chose chat, or Cockpit is unavailable or not proven visible,
show the simplified English FlowPilot Route Sign Mermaid, next jumps, checks,
fallback or repair exits, continuation state, and acceptance delta.
Formal startup, route mutation, and completion self-interrogation evidence is
only draft evidence until the project manager ratifies the scope, layer
coverage, count, and decision set. The project manager's ratification path is
stored in the frontier authority record.

The user flow diagram is the single display view over canonical `.flowpilot`
state, not an alternate execution path. Chat and Cockpit UI render the same
simplified English 6-8 stage or route-node graph from
`.flowpilot/runs/<run-id>/diagrams/user-flow-diagram.mmd`, with the current
stage and active route/node highlighted. Superseded or paused routes stay in
history with replacement reasons and checkpoint/failure evidence.

If Cockpit UI is not open, the chat Mermaid block is mandatory at startup,
major route-node entry, parent/module or leaf route-node entry, PM current-node
work brief, legacy key node change, route mutation, review or validation
failure returns, completion review, and explicit user requests. The route sign
must show a visible
`returns for repair` edge when review, validation, or route mutation sends the
route back to an earlier or current repair node.

Raw FlowGuard Mermaid exports are diagnostic only. They are disabled by
default and generated only on explicit request. Route mutation invalidates the
old user flow diagram; recheck the route and refresh the artifact before
showing it as current progress.

The human-like reviewer must check the visible display surface. In
closed-Cockpit cases the reviewer must confirm that the Mermaid block appeared
in chat, matches the active route/frontier node, and includes the repair edge
when required. A file-only check does not pass the gate.

When `scripts/flowpilot_user_flow_diagram.py` is available, it is the standard
route-sign hook: generate chat Markdown with
`--markdown --trigger <trigger> --write` (`major_node_entry` is the preferred
trigger for ordinary route-node entry; `key_node_change` is a legacy alias),
paste that exact block into chat when
required, then record the reviewer gate with
`--reviewer-check --mark-chat-displayed --write`. If the script is unavailable,
manually compose the same English Mermaid from the active route/frontier and
record equivalent reviewer evidence.

Each full round must also cover the full layer matrix: goal/acceptance,
functional capability, data/state/source of truth, implementation strategy and
toolchain, UI/UX when user-facing, validation/QA, recovery/heartbeat/route
updates, and delivery/showcase/public-boundary quality. Focused rounds may
emphasize the active scope, but they must still record local cross-layer
impacts, unchanged layers, and parent impact-bubbling decisions. A single-axis
UI-only or backend-only interview does not satisfy a full gate.

For formal multi-hour routes, continuation evidence must include the real
host-level continuation or wakeup record when the host supports it. If no such
tool exists, record `manual-resume` fallback/limitation instead of treating
JSON heartbeat files as a passed real-continuation gate. Unsupported hosts must
not create heartbeat automation.

Every meaningful route scope has two FlowGuard scopes: the
development-process model and the product-function model. The process model
checks how FlowPilot completes the node; the product model checks how the
product, workflow, UI, backend behavior, data, or user-visible result should
behave. A process-only pass is not enough for implementation, checkpoint, or
completion.

Model execution is role-specific. The process FlowGuard officer authors, runs,
interprets, and approves or blocks process-model coverage. The product
FlowGuard officer authors, runs, interprets, and approves or blocks
product-model coverage. The controller may provide context and receive the
report, but it must not author or run FlowGuard model files for the officers.
Passing command output without the matching officer's ownership, model-boundary
check, command execution or valid unchanged reuse, counterexample/missing-label
inspection, cited model files, state fields, state/edge counts, blindspots, and
approval is a draft, not a completed gate.

Model gates are dispatched as officer-owned asynchronous gates when live
background roles are available. The PM writes a modeling request with an
officer output root and a controller non-dependent coordination boundary. While
the matching officer authors, runs, interprets, and reports, the controller may
continue only non-dependent coordination such as read-only status
reconciliation, dependency inventory routing, and relaying already-authorized
packets that cannot satisfy or bypass the pending model gate. Implementation, route
freeze, checkpoint closure, completion closure, or any protected gate remains
blocked until the officer report is approved.

Officer reports must prove execution ownership with `model_author_role`,
`model_runner_role`, `model_interpreter_role`, `approved_by_role`,
`commands_run_by_officer`, model files, input snapshots, state/edge counts,
invariant and missing-label results, counterexample inspection, PM risk-tier
extraction, model-derived review agenda, toolchain/model improvement
suggestions, confidence boundary, blindspots, and any valid unchanged-reuse
basis. If the host cannot let live officers run tools, FlowPilot records
explicit single-agent fallback and does not claim parallel officer execution.
Controller outputs are pointers only.

PM-initiated FlowGuard modeling is a decision-support move, not a vague
handoff. When the project manager cannot confidently choose a route, repair,
feature, target-object hypothesis, file/protocol structure, or validation path
from existing evidence, the PM may write a structured modeling request and
assign it to the process FlowGuard officer, the product FlowGuard officer, or
both. The request names the decision, uncertainty, evidence, candidate options
or option-generation need, assigned officer scope, required answer shape,
officer output root, and controller non-dependent coordination boundary. The
officer first checks modelability. Missing evidence becomes an
evidence-collection node; an over-broad question becomes split modeling
requests. A valid report includes coverage, blindspots, failure paths,
PM-facing risk tiers, model-derived review agenda, toolchain or model
improvement suggestions, human walkthrough recommendations, recommendation,
confidence, next smallest executable action, and route mutation candidate. It
must avoid absolute "no risk" wording; it states the model boundary and gives
PM decision options. The PM synthesizes the report and records the route
decision.

Controller route memory is the PM's durable view of what already happened.
The Controller refreshes `.flowpilot/runs/<run-id>/route_memory/route_history_index.json`
and `.flowpilot/runs/<run-id>/route_memory/pm_prior_path_context.json` from the
current frontier, route, mutation ledger, stale-evidence ledger, review
markers, and research/modeling source paths. The Controller may write only an
index and brief; it has no route decision authority and must not read sealed
packet or result bodies.

Before route drafting, resume continuation, node acceptance planning, repair
choice, route mutation, parent segment decisions, evidence-quality packaging,
final ledger construction, or closure, the PM reads both route-memory files
and returns `prior_path_context_review`. That review cites both paths and
states which completed nodes, superseded nodes, stale evidence, prior blocks,
and experiments affected the decision. The Controller summary is not product
evidence; it only points the PM to source files that may need direct review.

Human-like inspection is a route mechanism, not a comment. Inspectors load the
contract, route, product model, child-skill evidence, screenshots/logs/output,
and parent context; then they operate or inspect the product like a real
reviewer. Blocking issues must be made specific through inspector grilling and
must mutate the route into repair work. A repair closes only after repair
process/product models, repair evidence, and same-inspector recheck pass.
Human-like inspection is reviewer-owned: the controller cannot substitute a
self-review for the human-like reviewer's neutral observation, pass/block
decision, or same-class recheck.

Every human-like inspection starts with a neutral observation pass before
judgement. The inspector records what the artifact, screenshot, output, or
exercised feature actually appears to be: visible content, controls, state,
window/taskbar/browser artifacts, response to attempted operations, and what
required behavior was or was not observable. For UI concepts, the observation
explicitly states whether the image appears to be an independent concept
target, an existing screenshot, an existing-image variant, a desktop/window
capture, old route UI evidence, or prior failed evidence with cosmetic changes.
The pass/fail judgement must cite that observation. If observation and claimed
evidence type conflict, the gate fails or requests more evidence.

Every review judgement must also classify findings before approval:
`current_gate_required`, `future_gate_required`, or `nonblocking_note`.
Current-gate obligations include any evidence, child-skill step, visual asset
check, interaction check, or acceptance criterion required by the active gate.
They cannot be approved as "pass with caveat" or "do later". A current-gate
caveat is a blocking issue and must trigger PM repair-strategy interrogation,
route mutation or reset, stale-evidence invalidation, repair work, and
same-inspector recheck. Future-gate obligations are allowed only when they are
not required by the active gate and are mapped to a named downstream gate or
node in the execution frontier. Nonblocking notes are permitted only after all
current-gate obligations are clear.

A failing judgement is strict. It cannot continue as "accepted with
constraints" when the gate is blocked. FlowPilot marks the current child or
subnode as failed, stale, or superseded, invalidates affected evidence and
parent rollups, creates a new route version, rewrites the execution frontier,
and points the next executable gate at a repair target. Use the smallest
structural repair that covers the finding:

- reset the existing child when the original child scope can cover the failure;
- insert an adjacent repair/regeneration sibling when clean work should not
  overwrite failed evidence, such as concept regeneration after authenticity
  failure;
- split into several focused children when the finding exposes multiple
  missing responsibilities;
- rebuild the child subtree or bubble impact upward when parent interfaces or
  the parent product model changed.

Every reset or inserted child then runs its own focused interrogation,
development-process model, product-function model, execution, neutral
observation, inspection, and same parent/composite recheck.

Every effective route node with children must also run a parent backward replay
before it closes. Child-local passes are inputs, not sufficient closure
evidence. The parent review reloads the child evidence, replays it against the
parent product-function model, inspects whether the children compose into the
parent goal, and either passes or mutates the route. Failure strategies are:
return to an affected existing child, insert an adjacent sibling child, rebuild
the child subtree, or bubble the impact to the next parent when the parent
contract changed. The affected evidence and parent rollups become stale until
the changed child/subtree passes and the same parent backward review reruns.

Pause, restart, and terminal closure use a unified lifecycle reconciliation
gate. Before claiming any of those states, FlowPilot scans Codex app heartbeat
automations, `.flowpilot/runs/<run-id>/state.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`, and latest heartbeat or
manual-resume evidence. `scripts/flowpilot_lifecycle.py` provides a read-only
inventory and required action list; actual Codex automation changes still use
the official Codex app automation interface.

Heartbeat automations should stay stable after creation. Route mutations,
next-node changes, and current-mainline plan updates are persisted in
`execution_frontier.json`; the heartbeat simply reloads that frontier on the
next wakeup. Change the heartbeat automation only when the host continuation is
missing, stale, or requires an official reset.

Stable heartbeat reload is an execution gate, not a passive reminder. While
`unfinished_current_node` is true or `advance_allowed` is false, the heartbeat
must select the persisted `current_subnode` or `next_gate` for `active_node`
and either execute that gate or record a concrete blocker. Heartbeat evidence
must name the selected gate, action attempted, result, and updated completion
guard. A heartbeat that only writes "next I will..." is a no-progress failure.

Automated continuation is heartbeat-only lifecycle state. The route heartbeat
cadence is fixed at one minute: route heartbeat automations use
`rrule: FREQ=MINUTELY;INTERVAL=1`, and route/frontier evidence records
`route_heartbeat_interval_minutes: 1`. Creating or repairing real heartbeat
continuation writes lifecycle evidence with the heartbeat id, cadence, active
state, and official host automation source. If the heartbeat cannot be created
or verified, roll back to `manual-resume` before route execution or record a
concrete blocker.

On terminal closure for automated routes, write terminal/inactive route state,
write the inactive lifecycle snapshot back to
`.flowpilot/runs/<run-id>/state.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`, write lifecycle evidence,
and then disable or delete the heartbeat automation. For manual-resume routes,
record that no heartbeat automation exists to stop.

This lifecycle policy is not node-local. Ordinary checkpoints, node
transitions, user-flow-diagram refreshes, and Codex plan syncs must not
recreate, re-register, start, restart, or re-enable heartbeat automation unless
they are explicitly in the lifecycle setup/repair gate.

## Capability Gates

Required:

- the three-question startup gate completed before showcase commitment and self-interrogation;
- visible self-interrogation evidence before contract freeze;
- PM-owned product-function architecture before contract freeze, including
  feature decisions, display rationale, missing-feature review, negative
  scope, product officer modelability approval, and reviewer usefulness
  challenge;
- user flow diagram before route execution, fresh FlowPilot Route Sign display
  at each current-node entry, and visible node roadmap before formal chunks;
- continuation readiness before behavior-bearing work: real one-minute route
  heartbeat schedule and heartbeat health when supported, or manual-resume
  packet freshness when unsupported;
- execution frontier and visible Codex plan sync before behavior-bearing work;
- FlowGuard dependency, process design, and model checks before
  behavior-bearing work;
- root, parent, leaf, repair, and capability product-function model checks
  whenever those scopes affect delivered behavior;
- PM-owned child-skill gate manifest before route modeling: discover child
  skills only from the PM selection manifest, read each invoked
  `source_skill`'s `SKILL.md`, load relevant
  references or record skips, map the child workflow and completion standard
  into route gates, show a child-skill mini-route of key milestones, assign
  required approvers, and write the evidence checklist;
- current-node child-skill manifest refinement before child-skill execution or
  implementation that depends on child-skill evidence;
- child-skill conformance model when the child skill materially affects the
  active node;
- strict gate-obligation review model before capability work that can be
  closed by a reviewer, so current-gate caveats cannot advance and future
  obligations must be mapped to named downstream gates;
- current-node high-standard recheck completed by the PM against the strongest
  feasible product target, unacceptable-result bar, semantic-fidelity policy,
  and likely local downgrade risks before node acceptance plan approval;
- quality package before implementation: feature thinness, improvement
  classification, child-skill mini-route visibility, validation strength, and
  rough-finish risk;
- child-skill evidence audit, evidence/output match, domain-quality review,
  iteration-loop closure, and assigned role approvals before the parent route
  node resumes;
- PM-owned final route-wide gate ledger before terminal completion. The PM
  rebuilds it from the current route and execution frontier, resolves effective
  and superseded nodes, collects child-skill, human-review, product-model, and
  process-model gates, resolves generated-resource lineage with dispositions
  `consumed_by_implementation`, `included_in_final_output`, `qa_evidence`,
  `flowguard_evidence`, `user_flow_diagram`, `superseded`, `quarantined`, or
  `discarded_with_reason`, checks stale evidence, replays the standard scenario
  pack and node-risk scenarios, triages
  every risk or blindspot, records zero unresolved current obligations and zero
  unresolved residual risks, builds a terminal human backward replay map,
  requires the reviewer to start from the delivered product and replay root,
  parent, and leaf-node obligations by hand, records PM segment decisions and a
  repair/restart policy, and then records PM ledger approval;
- strict obligation classification before any reviewer pass: current-gate
  obligations clear, future obligations named, and nonblocking notes separated
  from blockers;
- anti-rough-finish review before checkpoint or completion closure;
- human-like product inspection before checkpoint and final completion, with
  route mutation and same-inspector recheck for blocking issues;
- parent backward replay before every effective route node with children can
  close, with child-evidence replay, parent product-model comparison,
  human-like parent review, PM segment decision, and structural route mutation
  when child composition fails;
- capability evidence sync before implementation.

Capabilities sourced from child skills may complete only after their own
completion standards are met. A route may not replace a child skill with a
weaker FlowPilot summary, and every skipped child-skill step needs an explicit
reason, waiver, blocker, or task-irrelevance note.

The parent route cannot continue on a claim that a child skill was used. It
needs the mapped child-skill steps, step evidence, output match, domain-quality
decision, iteration closure, assigned role approvals, and completion-standard
verification.

For UI skills, expose only key milestones such as `contract/concept target ->
frontend implementation -> design iteration -> deviation review -> geometry QA
-> screenshot QA -> final verdict`. Do not copy every UI prompt rule into
FlowPilot.

Conditional:

- UI routes require child-skill-routed UI evidence, not FlowPilot-authored UI
  design prompts. Invoke `autonomous-concept-ui-redesign` for UI redesign,
  implementation, polish, visual iteration, deviation review, and layout QA.
  The orchestrator owns the concept-led front half internally, then composes
  `frontend-design`, `design-iterator`, `design-implementation-reviewer`,
  image generation when needed, and geometry/screenshot QA. Do not require the
  old `concept-led-ui-redesign` skill.
- When the user has not set a different iteration count, FlowPilot records the
  autonomous UI refinement budget as 10 `design-iterator` rounds by default
  with a maximum of 20 rounds.
- Before UI implementation, record the source skill's concept-target decision:
  generated/selected target, authoritative reference, explicit waiver, or
  blocker. Post-implementation rendered QA evidence cannot be relabeled as this
  pre-implementation decision.
- For generated concept targets, record a separate authenticity decision. A
  generated file is not enough: the target must be an independent design
  concept, not an existing screenshot, existing-image variant, desktop capture,
  taskbar-inclusive capture, old route UI, or prior failed UI evidence with
  cosmetic changes. If authenticity fails, the child-skill loop fails and the
  route mutates back to clean concept regeneration.
- Before the authenticity decision, record a neutral visual observation of the
  candidate image: what is visibly present, whether it appears to be a true
  independent concept, and whether it looks like a captured UI, an
  existing-image variant, or contaminated old evidence.
- After neutral observation, record an aesthetic verdict and concrete reviewer
  reasons for generated concept targets before implementation planning. A
  concept that is authentic but ugly, weak, incoherent, template-like, or
  disconnected from the shared visual direction routes back to concept repair
  or regeneration.
- After UI implementation, record the source skill's rendered-QA evidence and
  loop-closure decision for material concept/implementation differences.
- Product-facing visual assets such as app icons, logos, splash screens, or
  README hero imagery are routed through the same UI child-skill evidence when
  they are in scope. FlowPilot records scope, aesthetic verdict, concrete
  reasons, and evidence paths; the UI child skills own visual style and
  generation details.
- App/software icons for desktop, mobile, packaged web, browser-extension, or
  branded software artifacts require real application identity evidence from
  the UI child skill. A selected icon or in-app logo is not enough unless it is
  also bound to the platform surfaces that exist for that target: runtime
  window/app icon, taskbar/dock/shelf icon, tray/menu-bar icon when present,
  and package/shortcut/installer manifest when packaging is in scope. If the
  platform still shows a host runtime icon, completion is partial or blocked
  until the gap is fixed or explicitly waived with scope reason.
- After rendered screenshot QA, record a rendered-UI aesthetic verdict and
  concrete reviewer reasons before divergence or loop closure. A screenshot
  existing is not proof that the UI looks good enough.
- Subagent opportunity checks happen at child-node entry. Parent/module review
  may identify likely sidecar areas, but it does not spawn subagents or assign
  node ownership.
- Sidecar subagents may only receive bounded helper tasks inside the active
  child node. They cannot own the child node, route advancement, acceptance
  floor, checkpoint, or completion decision.
- Reuse a suitable idle subagent before spawning a new one. Spawn only on demand
  when no idle subagent fits and the task is worth the coordination cost.
- Sidecar reports require an authorized integration/review packet before
  dependent implementation, checkpoint, route advancement, or completion.

## Terminal States

`complete` is allowed only when final verification exists, anti-rough-finish
review passed, feature/acceptance/quality-candidate reviews are complete,
every structurally required local parent backward replay has a reviewer pass
and PM segment decision, product-function model replay and final human-like
inspection passed,
PM-owned final route-wide gate ledger has been rebuilt from the current route,
its generated-resource lineage is resolved, its unresolved count is zero, the
human-like reviewer has replayed it backward from the delivered product through
root, parent, and leaf-node segments in the PM-built replay map, every replay
segment has a PM decision, repair/restart policy is recorded, and the PM has
approved the clean ledger with independent adversarial audit evidence citing route/frontier,
effective entries, stale/superseded evidence, waiver authority, unresolved
counts, reviewer replay, standard scenario replay, node acceptance plan
coverage, and risk-or-blindspot triage with zero unresolved residual risks,
completion self-interrogation finds no obvious high-value work remaining, and
final report evidence exists. Open inspection issues, unrechecked repairs, or
missing same-inspector recheck evidence block completion. For routes with
automated heartbeat continuation, completion closure writes terminal lifecycle
state back to local state/frontier/lifecycle evidence before stopping the
heartbeat. Terminal closure also runs
`.flowpilot/runs/<run-id>/terminal_closure_suite.json`, refreshing terminal
state/frontier/ledger/checkpoint evidence, controlled-stop/completion notice
status, automation lifecycle, role memory, and final user-report readiness.
`blocked` is required when a hard gate is denied, the model
cannot be stabilized, experiments are exhausted, or dependencies cannot be
connected.
