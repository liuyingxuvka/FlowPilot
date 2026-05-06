# FlowPilot Protocol

FlowPilot is the project controller. FlowGuard is the executable modeling layer
used to design and validate the controller route, capability routing, recovery
branches, heartbeat behavior, and any task-local behavior models.

## Startup

1. On FlowPilot invocation, enter `startup_pending_user_answers`.
2. Ask three startup questions: background-agent permission,
   scheduled-continuation permission, and whether to open Cockpit UI. End the assistant response immediately
   after these questions. Do not inspect files, start tools, create route state,
   launch subagents, probe heartbeat, or show the banner in the same response.
   FlowPilot remains in `startup_pending_user_answers` until the user's later
   reply supplies all three answers. Do not ask the user to choose a mode.
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
7. Run visible full grill-me style self-interrogation. In the same startup
   round, draft the intended floor, seed the improvement candidate pool, seed
   the initial validation direction, and surface product-function questions.
   Do not freeze the contract yet.
8. Create the fixed six-agent crew for the new formal FlowPilot task and write
   `.flowpilot/runs/<run-id>/crew_ledger.json` plus one compact role memory
   packet under `.flowpilot/runs/<run-id>/crew_memory/` for project manager,
   human-like reviewer, process
   FlowGuard officer, product FlowGuard officer, worker A, and worker B.
   Resolve the live-subagent startup gate at the same time. The default target
   is six live background agents freshly spawned for this task after the
   startup answers and current route allocation. Prior-route or earlier-task
   `agent_id` values are audit history only and must not be resumed or counted
   as current live-agent evidence. If authorization is missing, pause and ask.
   If the user asked for live background agents but the host/tool appears
   unable to provide them, treat that as an unproven capability failure until
   the human-like reviewer directly probes the host/tool state and writes the
   finding for PM. Only the PM may record single-agent six-role continuity as
   a capability fallback, and worker/front-executor claims are pointers only.
9. Ask the project manager to ratify the startup self-interrogation and own
   material understanding, product-function architecture, route,
   heartbeat-resume, repair, and completion decisions from this point forward.
10. Before PM product-function synthesis or route decisions, require the main
    executor to write `.flowpilot/runs/<run-id>/material_intake_packet.json`: inventory,
    source summaries, source authority/freshness/contradiction classification,
    local skill and host capability inventory, coverage map, and unread or
    deferred materials. Local skills are candidate resources only until PM
    selection.
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
    `.flowpilot/runs/<run-id>/product_function_architecture.json` before contract freeze.
    It must include a user-task map, product capability map, feature necessity
    decisions, display rationale for every visible element, missing high-value
    feature review, negative scope, and a functional acceptance matrix.
14. Have the product FlowGuard officer approve or block modelability and
    product-function coverage, and have the human-like reviewer challenge
    usefulness, unnecessary display, missing workflow support, bad defaults,
    and failure-state gaps. If either blocks, the project manager revises the
    architecture before the route continues.
15. Freeze the acceptance contract as a floor, not a ceiling, from the
    approved product-function architecture and startup self-interrogation.
16. Write the capabilities manifest, including product-function architecture
    evidence.
17. Ask the project manager to write the PM child-skill selection manifest from
    the product capability map, frozen contract, capabilities manifest, and
    local skill inventory. The PM classifies candidate skills as `required`,
    `conditional`, `deferred`, or `rejected`; local availability alone never
    creates route work.
18. Ask the project manager to discover child-skill gates only from
    PM-selected skills, load each likely child skill's `SKILL.md` and relevant
    references, and extract a child-skill gate manifest with key stages,
    required checks, standards, evidence needs, skipped references with
    reasons, visible mini-route milestones, and required approver roles.
19. Have the human-like reviewer, process FlowGuard officer, and product
    FlowGuard officer review their slices of the manifest. The project manager
    then approves or blocks manifest inclusion in route modeling, the
    execution frontier, and the PM runway. The controller, worker A, and
    worker B are forbidden approvers for child-skill gates.
20. Verify FlowGuard and required dependency skills.
21. Inspect dependency/tool needs and write a dependency plan.
22. Install only the minimum dependencies needed for FlowPilot itself and the
    current route/model checks.
23. Defer future route, chunk, or native-build dependencies until the node or
    check that actually needs them.
24. Probe host continuation capability only after the scheduled-continuation
    startup answer is recorded. If the user allowed scheduled continuation and
    setup fails, do not silently switch to manual resume. The human-like
    reviewer must directly check whether the host has real scheduled
    continuation and whether any candidate heartbeat is attached to this
    current run. A same-name automation from another thread, workspace, route,
    or stale run is not heartbeat evidence. PM may record manual-resume as a
    capability fallback only after that reviewer report.
25. If the user allowed scheduled continuation and the host supports real
    wakeups, create the automated continuation: a stable one-minute heartbeat
    launcher. The launcher loads persisted route/frontier state rather than
    carrying route-specific next-jump instructions in its prompt. On wakeup it
    loads role memory, resumes or replaces each role from memory, then asks
    the project manager for a completion-oriented runway from the current
    position to project completion.
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
32. The matching officers inspect counterexamples for both model scopes and
    write approve/block reports.
33. Freeze the checked candidate as route `flow.json` and generate English
    `flow.md`.
34. Write `.flowpilot/runs/<run-id>/execution_frontier.json` from the checked route, active
    node, current subnode/gate when applicable, next node, current mainline,
    fallback, checks before advance, and the current-node completion guard.
    While a node is unfinished, the frontier must name the concrete
    `current_subnode` or `next_gate` that the next continuation turn should
    execute.
    It must also name the actor authority for that gate: draft owner,
    execution owner, required approver, forbidden approvers, approval status,
    approval evidence path, independent validation requirement, completion
    report-only prohibition, independent validation evidence path, and blocked
    reason if applicable. It also records
    the latest PM completion runway, including downstream steps, hard-stop
    conditions, checkpoint cadence, and any PM stop signal.
35. Sync the visible Codex plan list from the latest PM completion runway,
    replacing the current plan projection while preserving older PM decisions
    and checkpoints as history. If the host exposes a native visible plan/task
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
    allowed, manual-resume evidence when manual continuation is selected or
    reviewer-verified scheduler unavailability is PM-downgraded,
    residual route state, and shadow-route evidence. It must bind the
    background-agent answer to actual
    subagent state: if the user allowed background agents, verify six live
    role-bearing subagents were freshly spawned for this FlowPilot task after
    that user decision and after current route allocation, and verify none of
    their `agent_id` values comes from prior route ledgers or older role-memory
    packets. If live agents are unavailable or damaged, the reviewer must
    directly probe and say so; PM may then record single-agent continuity as a
    capability fallback without treating the worker's failed-start report as
    proof. If the user chose single-agent continuity, verify the explicit
    fallback authorization and do not claim live subagents.

    It must bind the scheduled-continuation answer to actual automation state:
    if heartbeat is used, verify the concrete automation id, cadence, status,
    target thread/workspace, prompt or metadata, current `run_id`, current
    route, and frontier source. Name equality alone is insufficient because an
    automation with the same name may belong to another thread, workspace, or
    old run. If scheduler/heartbeat support is unavailable or damaged, the
    reviewer must directly probe and report that fact before PM records
    manual-resume fallback.

    It must bind the display-surface answer to actual display state: if the
    user requested Cockpit and Cockpit is missing or damaged, the reviewer must
    directly probe and report that fact before PM records chat route signs as a
    display fallback. That fallback is only a route-display fallback; it does
    not satisfy a product requirement to build or repair the Cockpit UI. The
    reviewer writes a report only; the reviewer
    does not approve startup and does not open the gate. The project manager
    reads the report. If it contains blockers, PM sends remediation items back
    to authorized workers through a PM packet and requires a new factual reviewer report. If it
    is clean, PM writes `pm_start_gate` evidence opening startup from that
    exact report.

    Work beyond startup is illegal until the PM records
    `work_beyond_startup_allowed: true` from the clean factual report. If the
    three answers are incomplete, the prompt did not stop for the user's reply,
    answers are inconsistent with subagent/continuation evidence, or required
    cleanup evidence is missing, route the issue back through PM and workers. A
    route-local file without matching canonical state/frontier/crew/continuation
    evidence is a shadow route and must be quarantined or superseded before
    continuing.
38. Start the first bounded chunk only after continuation mode is known.
    Automated routes use heartbeat restore; manual-resume routes load the same
    state/frontier/crew-memory inputs in the active turn. In both modes the
    project manager issues a completion-oriented runway, the controller syncs that
    runway into the visible plan, and continuation readiness,
    parent-subtree review, unfinished-current-node recovery check,
    child-skill gates when needed, dual-layer product/process gates,
    human-like inspection gates, the quality package, and verification are
    defined.

Do not begin with a "should FlowPilot be enabled?" decision. In a FlowPilot
context, controller state is enabled. A formal FlowPilot route is not a
lightweight tier: if FlowPilot is the active driver, it starts at showcase-grade
scope. Tiny maintenance may record continuity in `.flowpilot/`, but it should
not be reported as a full formal FlowPilot route unless the showcase gates ran.
The startup banner is a user-visible launch marker, not route evidence; it
exists so the user can immediately see when the heavy FlowPilot controller has
started. The banner is illegal in the same assistant response that asks the
three startup questions.

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

Material intake is a first-class startup gate between PM ratification of
self-interrogation and PM product-function architecture. The controller
does the descriptive work first: it inventories materials, reads or samples
enough to say what each source is for, records source quality and uncertainty,
inventories locally installed skills and host capabilities as candidate-only
resources, and writes `.flowpilot/runs/<run-id>/material_intake_packet.json`.

The human-like reviewer then approves or blocks sufficiency. The reviewer must
open or sample the actual materials behind the packet, not only read the
worker's packet. Approval means the packet matches the real inspected sources
closely enough for PM planning: obvious sources are not missing, large sources
are scoped honestly, contradictions are visible, and uncertainty is not hidden.
A reviewer block returns to intake; the PM cannot override a current material
sufficiency gap.

After reviewer approval, the project manager writes
`.flowpilot/pm_material_understanding.json`. This is interpretive, not merely a
second inventory: it maps claims to sources, lists open questions, classifies
material complexity, and decides whether the next route can proceed directly or
must insert discovery, cleanup, spreadsheet analysis, data modeling, research,
validation, or reconciliation nodes. Messy/raw materials make material
understanding part of the formal route, not a hidden pre-step.

If the PM cannot safely decide from reviewed materials, the gap becomes a
PM-owned research package instead of a loose note. The package records the
decision to be made, route impact, allowed local/user/web/browser/source types,
host capability decision, private/paid/account hard gates, worker owner, stop
conditions, and reviewer direct-check requirements. Worker reports include raw
evidence pointers, negative findings, contradictions, and confidence
boundaries. The reviewer directly checks original sources or experiment output;
a summary-only pass is invalid. If the reviewer blocks, PM returns concrete
rework to the worker, inserts follow-up research or validation, mutates the
route, asks the user, or blocks. Product architecture, route generation, node
acceptance, and implementation that depend on the gap remain blocked until
reviewer sufficiency passes and PM records how the result was absorbed or how
the route changed.

## Product Function Architecture

The product-function architecture gate is the missing design layer between
startup self-interrogation, reviewed material handoff, and contract freeze. It
is owned by the project manager, not by the controller, and it must exist
before route generation or implementation.

The canonical artifact is `.flowpilot/runs/<run-id>/product_function_architecture.json`.
It records:

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
- the user-task map;
- the product capability map;
- feature necessity decisions: `must`, `should`, `optional`, or `reject`;
- display rationale for every visible label, control, status, card, empty
  state, alert, and persistent text;
- missing high-value feature review;
- negative scope and rejected displays;
- functional acceptance matrix with inputs, outputs, states, failure cases,
  checks, and evidence paths.

The product FlowGuard officer approves or blocks whether the architecture can
be modeled and checked. The human-like reviewer challenges usefulness,
ambition, and completeness before the contract freezes by comparing the PM
architecture against the user request, inspected materials, and expected
workflow reality: unnecessary features, unnecessary visible text, missing
workflow support, bad defaults, hidden semantic downgrades, placeholder
artifacts that would be embarrassing to show, failure-state gaps, and weak
user-task coverage. A product-function model later in the route validates the
design; it does not replace this pre-contract PM synthesis gate.

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
`.flowpilot/runs/<run-id>/root_acceptance_contract.json`. It records only the
root-level hard requirements and high-risk requirements, proof type for each
requirement, report-only prohibitions, and which obligations must later be
carried into node acceptance plans. It does not attempt to define every node's
future detailed test plan.

The project manager also selects
`.flowpilot/runs/<run-id>/standard_scenario_pack.json`. Standard scenarios are
route-local compensating fixtures or states for high-risk requirements that the
live project may not naturally contain: multi-run indexes, terminal-complete
state, blocked gates, stale/conflicting frontier, missing artifacts, long
localized text, absent host capability, and legacy or old asset contamination.
Unused relevant scenarios require a PM reason. Scenario evidence feeds node
plans and final replay; it does not complete a route by itself.

The contract may freeze only after the root acceptance contract, proof matrix,
and required standard scenario selection exist.

## Node Acceptance Plans

At active node entry, FlowPilot first refreshes and visibly displays the
current-node FlowPilot Route Sign from the active `flow.json` and
`execution_frontier.json`. Use `major_node_entry` for ordinary major route
nodes, `parent_node_entry` for parent/module entry, `leaf_node_entry` for leaf
entry, and `pm_work_brief` when the PM issues the current-node work brief. When
Cockpit UI is closed or not proven visible, paste the chat-ready Mermaid block
before any tool call or file edit for that node. Generated diagram files alone
do not satisfy node entry.

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

Only after that recheck does the project manager write
`.flowpilot/runs/<run-id>/routes/<route-id>/nodes/<node-id>/node_acceptance_plan.json`.
The plan maps inherited root high-risk requirements, node-local obligations,
experiments, checks, fixtures, screenshots, model replays, standard scenarios,
approver roles, and recovery paths. Implementation and node checkpoint closure
are blocked until required node experiments are passed or triaged. If a node
exposes a material, mechanism, source, or evidence gap that needs worker search,
source reconciliation, external lookup, or an experiment, the plan links an
approved research package or requires PM to write one before dependent work
proceeds. This keeps startup focused on root thresholds while forcing each node
to define its own concrete evidence and experiments before it closes.

## Current Node Work Authorization

The PM completion runway is a map, not permission to start every downstream
item. At any moment, the only authorized execution scope is the current
`active_node` plus the `current_subnode` or `next_gate` recorded in
`.flowpilot/runs/<run-id>/execution_frontier.json`.

Before the main executor, worker A, worker B, a child-skill route, verification,
polishing, or review-evidence drafting starts work, the project manager issues a
current-node work brief. The brief names the authorized node and gates, the
current-node step plan, expected artifacts, evidence paths, required approvers,
the visible route-sign display, and any downstream route context marked as
context only.

Workers and the main executor must treat that brief as the full work boundary.
They may read the downstream runway for context, but they must not implement,
generate assets for, verify, polish, or submit future-node work. If future-node
work appears necessary, the worker stops and asks PM for a formal transition
decision instead of doing the work speculatively.

Before tools or edits, each worker writes a node-entry declaration in its first
output or role report. The declaration acknowledges the entered node,
authorized node, current gates, current-node step plan, current route-sign
display, downstream context as context-only, and the no-future-node-work rule.
FlowPilot refreshes and displays the current user flow diagram when a node
opens, when the PM work brief is issued, and before substantial current-node
execution starts. If Cockpit is unavailable, the chat Mermaid block is the
visible display.

Every worker or main-executor submission starts with a scope declaration:
`submitted_node_id`, `submitted_gate_id`, `authorized_node_id`,
`authorized_gate_ids`, `future_node_work_performed`, and evidence paths limited
to current-node work. The human-like reviewer checks this declaration before
quality review. If the submission belongs to a future node, the reviewer stops
ordinary review, records an out-of-node submission finding, and sends it to PM.

PM then chooses exactly one path:

- reject the submission and return work to the current active node;
- record a formal PM node transition first, refresh route/frontier/plan and the
  user flow diagram, then request a new submission under the newly active node.

Future-node work cannot be accepted as current evidence, checkpoint evidence,
or completion evidence by catching the route up later.

## Parent Backward Replay

FlowPilot does not guess which route nodes are important enough for local
backward review. The trigger is structural: every effective route node with
children is a parent/composite node and must run an independent parent backward
replay before that parent can close. Semantic labels such as high risk,
integration, feature, or downstream dependency may add context to the review,
but they are not required to trigger it and cannot be used to skip it.

When the checked route is written or mutated, the project manager enumerates
all effective parent/composite nodes from `flow.json` into the execution
frontier and, for each parent as it reaches closure, writes
`.flowpilot/runs/<run-id>/routes/<route-id>/nodes/<parent-node-id>/parent_backward_replay.json`.
The human-like reviewer starts from the current parent-level delivered result,
then checks the parent goal, child rollup, child evidence, child node
acceptance plans, and current product behavior. Child-local passes are only
pointers. The reviewer must personally inspect or operate the relevant current
artifact and write factual review evidence.

After each parent replay segment, the project manager records one decision:
continue, repair an existing child, add or route to a sibling child, rebuild
the child subtree, bubble impact to the next parent, or PM stop. A repair or
route mutation makes the affected child evidence and parent rollup stale. The
same parent backward replay reruns after the repair before the parent can
close. Parent replay evidence is later consumed by terminal review, but
terminal review still independently replays the delivered product across root,
parent, and leaf obligations.

## PM Review And Modeling Packages

The project manager is also the authorization boundary for review and FlowGuard
modeling. Reviewers and FlowGuard officers may read the full route as context,
but they may only review or model the scope explicitly named by PM.

Before any node review, parent backward replay, terminal backward replay,
anti-rough-finish review, human-like inspection, screenshot QA, or final review
starts, PM issues a review package. The package names the authorized node and
gates, review purpose, evidence to inspect, review subnodes to execute, stop
boundary, and the return-to-PM path for out-of-scope work or missing
prerequisite evidence.

Review packages are executable review routes, not report-reading requests. The
human-like reviewer must perform adversarial direct inspection inside the
authorized review scope: operate the product or command path when available,
open and maximize or resize relevant UI windows, capture or inspect fresh
screenshots, exercise clicks and keyboard paths, inspect generated files or
state, and compare findings with the current node, product model, contract, and
evidence. Worker reports are pointers only and cannot satisfy review by
themselves.

Large reviews are split into PM-authorized review subnodes. A node exit review
typically includes scope check, evidence lineage check, direct artifact or
product walkthrough, model/verification reconciliation, residual-risk summary,
and PM decision. A terminal review walks backward from delivered product to root
acceptance through named route nodes. The reviewer cannot add review subnodes,
expand to future nodes, or continue reviewing after a scope mismatch unless PM
issues an updated review package.

Before any FlowGuard model gate starts, PM issues a modeling package. It names
the authorized model scope, exact PM decision needed, protected node or gate,
allowed inputs, expected report shape, and blocked downstream actions.
FlowGuard officers may report counterexamples, missing evidence, route-mutation
suggestions, and PM decision options, but they do not advance the route, accept
evidence, or expand modeling scope without PM authorization.

All review and modeling reports return to PM. PM is the only role that accepts
the report into route evidence, rejects it, expands the package, mutates the
route, or advances the active node.

## Actor Authority

FlowPilot's six-agent crew is an authority system, not a decorative report
list. Every formal gate records who may draft it, who executes it, who must
approve it, and who is forbidden to approve it. The controller is the packet
flow coordinator only: it can load state, relay PM packets, relay reviewer
decisions, relay worker results, sync the visible plan from PM decisions,
record status, and enforce hard stops. It cannot create worker evidence, run
ordinary implementation commands for worker nodes, edit product files, approve
gates, or advance the route from controller-origin evidence. For FlowGuard
model gates, the matching FlowGuard officer must author, run, interpret, and
approve or block the model.

Canonical authority rules:

- the project manager approves startup self-interrogation ratification,
  product-function architecture synthesis, route advancement,
  heartbeat-resume runway selection, PM stop signals, repair strategy, route
  mutation, and completion;
- the process FlowGuard officer authors, runs, interprets, and approves or
  blocks development-process model coverage;
- the product FlowGuard officer approves or blocks pre-contract
  product-function architecture modelability, then authors, runs, interprets,
  and approves or blocks product-function model coverage;
- the human-like reviewer owns pre-contract usefulness challenge, neutral
  observation, pass/block inspection, and same-class recheck;
- worker A and worker B only produce bounded sidecar reports. They cannot
  approve gates, mutate routes, checkpoint, or complete the route.

Child-skill gates use the same authority matrix. The project manager owns
route-design extraction of child-skill stages, checks, standards, evidence
needs, visible mini-route milestones, and required approvers. The human-like
reviewer approves human/product/visual/interaction review judgements; the
process FlowGuard officer approves process and conformance gates; the product
FlowGuard officer approves product-function impact gates; and the project
manager approves route inclusion, route mutation, parent return, and final
child-to-parent closure. Authorized workers may draft evidence or
implementation output, but their self-approval is invalid.

Every packet has a mandatory role-origin audit. Before a reviewer passes any
packet result, the reviewer checks the PM-authored packet, the reviewer
dispatch approval, the assigned worker or authorized role, and the actual
result author. If the actual author is the controller, unknown, or different
from the assigned role, the reviewer must return
`block_invalid_role_origin`, record the controller-boundary warning, and send
the packet back to PM for reissue, repair by the assigned role, quarantine,
route mutation, user block, or stop. Controller-origin evidence cannot be
accepted as "good enough" and cannot be repaired by the controller itself.

Work packets use an envelope/body split. The PM gives the controller only a
`packet_envelope` with `packet_id`, `from_role`, `to_role`, `node_id`,
`is_current_node`, `body_path`, `body_hash`, `return_to`, `next_holder`, and
controller allowed/forbidden actions. The detailed packet body lives at the
referenced body path and is readable only by the addressed role, with reviewer
and PM access limited to review, repair, or completion decisions. The
controller may read envelopes, update holder/status, relay envelopes, display
the required route sign, wait for returns, and ask PM for the next decision.
The controller may not read or execute packet/result bodies, implement code,
generate assets, run product validation, approve gates, close nodes, rewrite
hashes, or relabel a wrong-role completion.

All formal packet/result/review/PM mail must route through the controller. Each
relay writes a `controller_relay` signature with the controller agent id,
sender role, target role, holder before/after, envelope hash, and explicit
`body_was_read_by_controller: false` plus `body_was_executed_by_controller:
false`. The receiving role verifies that relay signature before opening any
body. Missing signatures, wrong targets, hash mismatch, private role-to-role
delivery, or missing no-read/no-execute declarations block body open and force
sender reissue through PM.

If the controller reads or executes a sealed internal body, it cannot continue
relaying that mail. It records a contaminated return-to-sender entry and PM must
request a fresh replacement from the original sender. Post-hoc signing,
cosigning, relabeling, or hash rewriting cannot make the old mail valid.

The split is a runtime artifact, not only prose. The physical packet runtime
writes `packet_envelope.json` and `packet_body.md` under
`.flowpilot/runs/<run-id>/packets/<packet-id>/`, computes the body hash from
the body file, and builds a controller handoff from envelope fields only. The
controller context must not contain packet body text. If the body is present in
the controller handoff or the packet files are missing, dispatch and review are
blocked before content inspection.

Worker, reviewer, officer, and PM returns use the same envelope/body split.
The returning role gives the controller a `result_envelope` naming
`packet_id`, `completed_by_role`, `completed_by_agent_id`, `node_id`,
`result_body_path`, `result_body_hash`, and `next_recipient`. Detailed
commands, files, screenshots, evidence, and findings go into the result body.
The controller relays the result envelope only. Reviewer and PM read the
result body only from their authorized review/decision position.

The role-origin audit is envelope-aware. The reviewer checks
`packet_envelope.to_role`, `result_envelope.completed_by_role`, and whether
`completed_by_agent_id` belongs to that role. Body hashes in both envelopes
must match the referenced bodies, and stale bodies after route mutation cannot
be accepted. Wrong-role completion cannot be fixed by cosigning, renaming, or
rewriting the envelope; PM must reissue or repair the packet through the
correct role.

The reviewer also performs a mail-chain audit before every subnode and
major-node closure. The audit checks controller relay signatures, recipient
pre-open checks, holder continuity, absence of private mail, and replacement
coverage for contaminated, rejected, unopened, or missing mail. If a required
letter was not opened when needed, reviewer sends the audit to PM. PM chooses
restart node, repair node, or sender reissue; controller cannot fill the gap.

The project manager owns reviewer timing. Before worker or controller work
that will later need review, the PM writes a review hold instruction naming the
expected gate and saying the reviewer waits. After worker output,
verification, and anti-rough-finish evidence are ready, the PM writes a review
release order naming the gate, evidence paths, scope, and required
inspections. Reviewer work before that release is precheck only: it may note
risks for PM, but it cannot open, close, or block the gate.

If a required authority blocks a gate, FlowPilot does not advance on evidence
existence. It records the block, grills the issue when needed, asks the project
manager for repair-strategy interrogation, mutates or blocks the route, and
rewrites the execution frontier. If a required authority is missing on
heartbeat resume, FlowPilot restores or replaces that role before work
continues; if it cannot, the gate blocks rather than falling back to
controller-origin self-approval.

## Universal Adversarial Approval Baseline

Every PM, reviewer, and FlowGuard officer approval is an independent
adversarial validation event. Completion reports, worker summaries, screenshots,
smoke logs, model-result snippets, and PM summaries are pointers only; they
cannot be the approval basis by themselves.

Every approval record must include an `independent_validation` block or point
to a role-approval evidence file. That evidence records:

- `completion_report_only: false`;
- report inputs used only as pointers;
- direct sources personally checked by the approving role;
- exact state fields, ledger entries, route/frontier files, model state fields,
  screenshots, logs, or material sources checked;
- commands, probes, walkthroughs, model checks, or samples run by the approving
  role;
- adversarial hypotheses tested against stale evidence, missing gates,
  unreachable behavior, incorrect waivers, bad model boundaries, or
  report-only approval;
- concrete evidence references such as file paths, screenshot paths, command
  output, state/edge counts, model labels, counterexamples, or ledger entry ids;
- risk or blindspot triage. A risk-like item must be classified as
  `blocking`, `test_gap`, `evidence_gap`, `route_gap`, `resolved_issue`,
  `non_risk_scope_note`, `explicit_exception_with_required_approval`, or
  `false_positive`.

PM approvals attack the decision surface: current route/frontier/ledger,
stale and superseded evidence, unresolved counts, waiver authority, blocker
handling, downstream consequences, and consistency with the frozen user goal.
Reviewer approvals attack the artifact or behavior directly: source material,
UI surface, output, log, screenshot, backend effect, delivered product, and
failure or edge cases. FlowGuard officer approvals attack the model boundary:
model files, commands or valid unchanged reuse, state/edge counts, invariant
results, missing labels, counterexamples, and blindspots.

An approval without independent validation evidence is pending or blocked. A PM
cannot launder a report-only reviewer or officer pass by accepting it later;
the gate must be rechecked by the correct role.

Unresolved risks are not acceptable residuals. If a role finds a real risk,
the PM routes it to repair, route mutation, QA, more evidence, correct-role
waiver, or PM stop. Non-risks are renamed to scope notes. Exceptions require
the correct approver and proof that the frozen contract is not lowered.

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

Router-owned proof is narrower than reviewer approval. The router may replace
reviewer effort only for mechanical checks backed by
`flowpilot.router_owned_check_proof.v1`: router-computed state, packet-runtime
hash checks, or host receipts bound to the current run. Self-attested AI claims,
payload booleans, default-option claims, and Controller summaries do not count
as proof. Startup now records `startup/startup_mechanical_audit.json`; reviewer
startup reports must separately cover any listed
`reviewer_required_external_facts`. Packet result reviews may rely on the
router proof only for envelope/hash mechanics, not for result quality or
acceptance judgement.

The six agents are persistent roles, and the default startup target is six
live background agents. Live subagent continuity still depends on host and tool
support, so FlowPilot must not treat missing live agents as an invisible
downgrade. It pauses for a user decision, records either live startup evidence
or explicit single-agent role-continuity authorization, and only then proceeds.
The authoritative recovery state is `.flowpilot/runs/<run-id>/crew_ledger.json`
plus compact role memory packets under `.flowpilot/runs/<run-id>/crew_memory/`.
Each role memory packet
stores the role charter, authority boundary, frozen contract pointer, current
route position, latest decisions, open obligations, blockers, evidence paths,
and "do not redo" notes. On heartbeat or manual resume, FlowPilot may try to
resume a stored agent id, but if that fails it must either start a replacement
live agent after authorization or replace the role from the latest memory
packet after explicit fallback approval. A replacement role started only from a
generic prompt is not recovered and cannot approve gates.

Crew identity uses three separate fields. `role_key` is the stable authority
and routing id. `display_name` is the user-facing chat/UI label. `agent_id` is
only a diagnostic/recovery handle and must not be shown as the primary label or
used as the authority key.

## Retired Run Modes

FlowPilot no longer has run modes. `Use FlowPilot`, an existing `.flowpilot/`
directory, host inability to pause, prior route state, or a generic request to
continue cannot authorize background agents, scheduled jobs, fallback
execution, or display-surface choices.

Removing modes does not lower hard gates or quality tier. Every formal
FlowPilot route keeps the same showcase-grade completion floor and still
requires explicit approval for hard gates.

## Self-Interrogation And Heartbeat

Startup self-interrogation must be visible in chat and persisted as structured
evidence. FlowPilot uses three depths instead of repeating a full grill-me at
every scope:

- full grill-me at formal boundaries: startup, route mutation or standard
  expansion, and completion review;
- focused grill-me at bounded boundaries: phase, group, module, leaf node, and
  child-skill entry;
- lightweight self-check at continuation micro-steps and tiny reversible choices.

Full grill-me derives the dynamic layer matrix and asks at least 100 questions
per active layer. A 100-question total across many layers is not enough. The
startup full round also seeds improvement candidates and initial validation
direction; do not run separate post-freeze interviews for those same topics. A
focused round asks 20-40 questions by default and may go up to 50 for complex
module, child-skill, state, or source-of-truth boundaries. A lightweight
self-check asks 5-10 targeted questions.

The coverage requirement is layered. A formal round must explicitly cover:

- goal and acceptance floor;
- functional capability and feature completeness;
- data/state, persistence, idempotency, and source of truth;
- implementation strategy, architecture, dependencies, and toolchain;
- UI/UX, interaction, visual quality, accessibility, and localization when a
  user-facing surface exists;
- validation, tests, screenshots, model checks, and manual QA;
- recovery, heartbeat, retries, route updates, and blocked exits;
- delivery/showcase quality, packaging, README/demo evidence, public boundary,
  and final presentation.

Focused node-level rounds emphasize the active node's domain but still record
which cross-layer impacts are unchanged, which require local checks, and which
must bubble to the parent route model. A UI node cannot claim a full grill-me
gate if lower-level capability, state, implementation, validation, and delivery
questions were skipped.

Each major route node should run focused node-level grill-me before defining
the next chunk. Each continuation micro-step should run a lightweight self-check
before execution when it starts new work.

Until the desktop Cockpit is available, chat is the temporary cockpit. At
startup, every new major `flow.json` route-node entry, parent/module or leaf
route-node entry, PM current-node work brief, legacy key node change, route
mutation, review or validation failure returns, completion review, or explicit
user request, emit the same simplified English FlowPilot Route Sign Mermaid
that the Cockpit UI displays. Do not refresh it on every heartbeat or internal
subnode/micro-step. The diagram is a 6-8 stage or route-node FlowPilot process
view with the current stage highlighted, plus short text for the active route,
active node, next checks, continuation state, and acceptance delta.

The user flow diagram is a display of existing `.flowpilot` route/frontier
state, not a new execution path. Chat and UI use the same generated Mermaid
source at `.flowpilot/runs/<run-id>/diagrams/user-flow-diagram.mmd`. Superseded
or paused routes remain history, not separate primary diagrams.

When Cockpit UI is not open, the chat Mermaid block is a hard gate. A generated
file, Markdown preview, or display packet alone does not satisfy the gate, and
`chat_displayed_in_chat` may be marked true only after the exact Mermaid block
appeared in the assistant message. Route mutation, review failure, validation
failure, or any backtrack to a repair target must add a visible `returns for
repair` edge before the route sign can be treated as current.

Raw FlowGuard Mermaid exports are engineering diagnostics. They are disabled by
default, generated only on explicit request, and must not replace the user flow
diagram in chat or the Cockpit UI. Route mutation invalidates the previous user
flow diagram; recheck the route and refresh the diagram before showing it as
current progress.

The human-like reviewer must check the visible display surface. In
closed-Cockpit cases the reviewer must confirm that the Mermaid block appeared
in chat, matches the active route/frontier node, and includes the repair edge
when required. A generated file or raw FlowGuard graph alone does not pass this
gate.

When `scripts/flowpilot_user_flow_diagram.py` is available, it is the standard
route-sign hook: generate chat Markdown with
`--markdown --trigger <trigger> --write` (`major_node_entry` is the preferred
trigger for ordinary route-node entry; `key_node_change` is a legacy alias),
paste that exact block into chat when
required, then record the reviewer gate with
`--reviewer-check --mark-chat-displayed --write`. If the script is unavailable,
manually compose the same English Mermaid from the active route/frontier and
record equivalent reviewer evidence.

## PM-Initiated FlowGuard Modeling Requests

FlowGuard is not only a final checker. The project manager may proactively use
FlowGuard as a modeling tool whenever a meaningful decision is uncertain: route
choice, node split, repair strategy, feature direction, target product behavior,
file or protocol structure, unknown software/object behavior, validation
strategy, or whether more evidence is needed.

The PM creates a structured modeling request and assigns it to the process
FlowGuard officer, the product FlowGuard officer, or both. Process requests ask
"how should FlowPilot do this?" Product requests ask "what is the target system
or product behavior?" Combined requests are valid when route choice depends on
target-object uncertainty.

Each request must name the decision, uncertainty, evidence sources, candidate
options or option-generation need, assigned officer scope, required answer
shape, officer output root, and controller parallel-preparation boundary.
The assigned officer first checks modelability. If evidence is missing, the
route gains evidence-collection work. If the request is too broad, it is split
into smaller modelable requests. A report is valid only after modelability is
resolved.

Each report must include model coverage, blindspots, failure paths, PM-facing
risk tiers, model-derived review agenda, toolchain or model improvement
suggestions, human walkthrough recommendations, recommendation, confidence,
next smallest executable action, and any route mutation candidate. It must not
claim absolute "no risk"; it states the model boundary, what was and was not
proved, and the concrete PM decision options. The PM then records a decision:
continue current route, mutate route, add evidence work, split request, repair
before advance, or block with a concrete reason. Officers advise from models;
the PM owns the route decision.

Heartbeat records alone are not enough to claim unattended recovery. FlowPilot
first probes whether the host supports real wakeups or automations. When the
host supports them, FlowPilot creates a real continuation schedule or wakeup,
checks that heartbeat before each node, and repairs it through the official
host interface if it is missing. When the host does not support them, FlowPilot
records `manual-resume` mode and uses `.flowpilot/` state, PM runways, and
checkpoints for handoff/resume without creating heartbeat automation.

The real continuation, when available, should be a stable launcher. It tells
FlowPilot to resolve `.flowpilot/current.json`, then load
`.flowpilot/runs/<run-id>/state.json`, the active `flow.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`,
`.flowpilot/runs/<run-id>/crew_ledger.json`,
`.flowpilot/runs/<run-id>/crew_memory/`,
`.flowpilot/runs/<run-id>/packet_ledger.json`, lifecycle evidence, and latest
heartbeat or manual-resume evidence. It then
rehydrates the fixed crew by resuming stored agent ids when possible. If live
agents are unavailable, it records the block and asks before replacing roles
from memory packets. After live startup or explicit fallback authorization is
recorded, it records the rehydration status and asks the project manager for
the current `PM_DECISION` and next completion-oriented runway.
The resolver order is mandatory on heartbeat and manual resume:
`.flowpilot/current.json` to `.flowpilot/runs/<run-id>/` is authoritative, and
top-level legacy state must be ignored except as import or quarantine evidence.
Route mutations, next-node changes, PM runway changes, packet-holder changes,
and current-mainline plan updates are persisted in files and then reflected in
chat/plan output; ordinary route changes should not rewrite the heartbeat
automation prompt.
The heartbeat or manual-resume turn also loads the current gate's authority
record. If a gate has draft evidence but lacks the required approver, it
requests that approval or records a blocker; it does not treat the draft as
complete.

Heartbeat and manual resume also load `packet_ledger.json`. If no current
packet is active, the controller asks PM for `PM_DECISION`. If PM issues or
reissues a packet envelope/body pair, the decision must include
`controller_reminder`, and the envelope goes to the reviewer for dispatch
approval before any worker sees the body. If a worker result envelope is
already present, the controller sends that `RESULT_ENVELOPE` to reviewer. If
the holder, worker identity, prior reviewer dispatch, envelope/body hash, or
worker-result state is ambiguous, the controller blocks and asks PM for
recovery, reissue, reassignment, quarantine, or route mutation. It does not
read bodies, infer missing worker work, or finish the packet itself.

The frontier has a current-node completion guard. If
`unfinished_current_node` is true or
`current_node_completion.advance_allowed` is false, the heartbeat or
manual-resume turn resumes `active_node` and treats `next_node` only as a
planned future jump. The jump is legal only after node status, required gates,
declared verification, node evidence, and continuation/checkpoint evidence are
written.

On heartbeat or manual resume, "continue later" is not progress. FlowPilot
first restores all six role identities and work memory from
`crew_ledger.json` and every role memory packet, then writes a crew
rehydration report covering project manager, reviewer, process FlowGuard
officer, product FlowGuard officer, worker A, and worker B. It must not lazily
rehydrate a role only when that role is first needed. FlowPilot asks the
project manager for a completion-oriented runway only after the crew memory
rehydration gate passes. It syncs that runway into the visible plan, then loads
the persisted `current_subnode`, `next_gate`, and packet recovery state for
the unfinished active node. It continues the internal packet loop as far as PM
and reviewer decisions allow, then continues along the PM runway until a PM
stop signal, hard gate, blocker, route mutation, or real environment/tool limit
stops progress. Continuation evidence must name the host kind
(`codex_heartbeat_automation`,
`windows_scheduled_task`, `manual_resume`, or `blocked_unsupported`), the exact
host evidence source, the PM runway, selected gate, packet recovery state,
role-memory rehydration result, actions attempted, results, checkpoint writes,
and updated completion guard. It may not end by only writing a future-facing
decision such as "continue to X" while the packet loop remains executable.

The visible plan sync is a host-facing control gate. When a native plan tool is
available, the controller must call it, not only update `.flowpilot` files.
The synced projection must contain the current executable gate and downstream
runway items toward completion; a one-step projection is stale-plan evidence.
If no native plan tool exists, record the fallback projection method and show
the runway in chat, but do not claim that the native Codex plan was synced.

If the host exposes reminders, monitors, wakeups, or automation tools, the
route records the continuation ID, cadence, wakeup condition, heartbeat
evidence, and fallback in `.flowpilot/heartbeats/`. If the host
lacks real continuation support, that limitation is recorded as
`manual-resume`; plain heartbeat files do not count as a passed
real-continuation gate for multi-hour formal work.

Automated continuation is heartbeat-only lifecycle state. The route heartbeat
cadence is fixed at one minute. Route heartbeat automations use
`rrule: FREQ=MINUTELY;INTERVAL=1`, and route/frontier evidence records
`route_heartbeat_interval_minutes: 1`. Whenever FlowPilot creates or repairs
real continuation, it writes lifecycle evidence with the heartbeat id,
cadence, active state, and official host automation source. If the heartbeat
cannot be created or verified, roll back to `manual-resume` before route
execution or record a concrete blocker.

When an automated route reaches `complete` or terminal shutdown, FlowPilot
writes terminal/inactive route state, writes the inactive lifecycle snapshot
back to `.flowpilot/runs/<run-id>/state.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`, lifecycle evidence, and
then stops the heartbeat automation. Manual-resume routes record that no
heartbeat automation exists to stop.

Pause, restart, and terminal closure all use the same lifecycle reconciliation
gate: scan Codex app heartbeat automations, `.flowpilot/current.json`,
`.flowpilot/runs/<run-id>/state.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`, and latest
heartbeat/manual-resume evidence before writing a new lifecycle state. Use
`scripts/flowpilot_lifecycle.py` for the read-only inventory; use the official
Codex app automation interface for Codex automation changes. Ordinary
checkpoint writes, node transitions, user-flow-diagram refreshes, and visible
plan syncs must not recreate, re-register, start, restart, or re-enable
heartbeat automation unless they are explicitly in the lifecycle setup/repair
gate.

Controlled nonterminal pause also writes
`.flowpilot/runs/<run-id>/pause_snapshot.json` with the current route/node,
open blockers, fixed-pending-recheck items, evidence caveats, heartbeat/agent
lifecycle, cleanup boundary, and artifacts that must not be reused in a fresh
run.

## Defect And Evidence Governance

Each formal run has a PM-owned defect ledger under
`.flowpilot/runs/<run-id>/defects/` and an evidence credibility ledger under
`.flowpilot/runs/<run-id>/evidence/`. It also has an append-only activity
stream at `.flowpilot/runs/<run-id>/activity_stream.jsonl`. Any role that
discovers a defect writes the first event. PM triages severity, owner, route
impact, and closure condition. Open blockers and `fixed_pending_recheck`
defects block node closure, route advancement, final ledger approval, and
terminal completion.

Evidence that may close a gate is classified as `valid`, `invalid`, `stale`,
or `superseded`, with source kind `live_project`, `fixture`, `synthetic`,
`historical`, or `generated_concept`. Fixture evidence can prove a capability,
but final reporting must disclose it separately from live-project evidence.
Invalid or stale evidence cannot close a current gate.

Every generated concept, image, icon, screenshot, diagram, model output, or
similar resource is registered in the generated resource ledger immediately
when it is created. Each item records origin, path, owning node or gate, and
one disposition: `selected`, `used`, `superseded`, `discarded`, `deleted`, or
`quarantined`. Terminal completion may only close after every generated
resource has a current disposition and reason.

The activity stream is append-only. PM decisions, reviewer holds/releases and
reports, officer modeling actions, worker reports, route mutations, checkpoint
writes, heartbeat/manual-resume actions, and terminal closure events append
progress records as they happen. Cockpit and chat progress displays read from
this stream plus current route/frontier state, so users see progress without
manual refresh or ad hoc status reconstruction.

## Dual-Layer Product And Process Modeling

Every meaningful FlowPilot scope has two FlowGuard scopes:

- development-process model: how FlowPilot completes the node, writes evidence,
  recovers, mutates the route, verifies, and advances;
- product-function model: how the product, workflow, UI, backend behavior,
  data, state, and user-visible result should behave.

This applies to root project scope, parent scope, leaf node scope, repair node
scope, child-skill capability scope, and final completion scope. A process-only
pass is not enough for implementation, checkpoint, or completion.

The matching FlowGuard officer owns model execution. The process FlowGuard
officer authors, runs, interprets, and approves or blocks process model
coverage. The product FlowGuard officer authors, runs, interprets, and
approves or blocks product model coverage. The controller may provide
context and receive the report, but it must not author or run FlowGuard model
files on the officer's behalf. The officer approval must cite the model
boundary, model files, commands run or valid unchanged reuse, state/edge counts,
invariant results, missing labels, counterexamples inspected, and blindspots.
If an officer blocks, the route follows the same repair/mutation path as a
human-like inspection block.

FlowGuard model gates are officer-owned asynchronous gates when live background
roles are available. The PM writes a modeling request, assigns it to the
matching process/product officer, and records an officer output root under the
active run. While that officer authors, runs, interprets, and reports, the main
executor may continue only non-dependent preparation: read-only context review,
dependency inventory, non-model evidence drafts, or scaffold work that cannot
satisfy or bypass the pending model gate. Implementation, route freeze,
checkpoint closure, completion closure, and any protected gate remain blocked
until the officer report is approved.

Every officer report proves execution ownership with `model_author_role`,
`model_runner_role`, `model_interpreter_role`, `approved_by_role`,
`commands_run_by_officer`, model files, input snapshots, state/edge counts,
invariant and missing-label results, inspected counterexamples, PM risk-tier
extraction, model-derived review agenda, toolchain/model improvement
suggestions, confidence boundary, blindspots, and any valid unchanged-reuse
basis. Main-executor outputs can be cited only as pointers. If the host cannot
let live officers run tools, FlowPilot records explicit single-agent fallback
and does not claim parallel officer execution.

When entering a parent layer, FlowPilot reruns both the current parent process
model and product-function model. When entering a leaf, FlowPilot checks the
leaf process model and product-function model, then derives tests or manual
experiments from the product model before implementation.

After implementation and declared verification, FlowPilot runs human-like
inspection before checkpoint or completion closure. Inspectors load the frozen
contract, current route, product-function model, child-skill evidence,
screenshots/logs/output, and parent context. They operate or inspect the
product like a real reviewer: compare concept against rendered output for UI
work, exercise user interactions or backend behavior, look for duplicated or
conflicting controls, check language/content coverage, and ask whether the
result is a complete product rather than a running artifact.

For UI, browser, desktop, click, hover, visual, localization, or rendered-output
gates, worker reports and automated captures are evidence pointers only. The
human-like reviewer must personally perform the walkthrough or block the gate
with a concrete reason the surface cannot be operated. A pass must record the
reviewer's own opened surfaces, viewport/window sizes, click or keyboard paths,
tabs/settings/support/language/tray controls checked when relevant, unreachable
controls, text overlap or clipping, excessive whitespace, crowded areas, layout
density, visual hierarchy, readability, and responsive fit.

Reviewer reports must also contain concrete repair or enhancement suggestions
when weaknesses are observed. Examples include what to add to large empty
regions, what to simplify in crowded regions, which hierarchy or spacing should
change, where text is clipped or occluding other elements, and which interaction
path is not discoverable. The project manager routes those suggestions as local
repair, route mutation, downstream follow-up, waiver by the correct role, or PM
stop. A report that only summarizes worker screenshots, screenshot QA, or an
interaction smoke log is `worker_report_only` evidence and cannot approve a
human-review gate.

Before any pass/fail judgement, the inspector writes a neutral observation of
what was actually seen or exercised. For screenshots and UI concepts, this is a
plain description of visible content, layout, chrome/taskbar/window artifacts,
old-route names, and whether the image appears to be an independent concept or
a captured/modified implementation. For functional checks, it records what was
operated, what response occurred, and which required behavior was not
observable. The later judgement must cite this observation; if the observation
contradicts the claimed evidence type, the gate fails or requests more
evidence.

Every inspection gate also classifies obligations before any pass decision:
`current_gate_required`, `future_gate_required`, or `nonblocking_note`.
Current-gate obligations are the active gate's own required evidence, required
child-skill steps, required visual/function checks, or declared acceptance
criteria. They cannot be accepted as "pass, do later". If any current-gate
obligation is missing, stale, untested, or only promised for later, the gate is
blocked and routed to repair. Future-gate obligations are allowed only when
they are not required by the active gate and are mapped to a named downstream
gate or node in the execution frontier. Nonblocking notes may be kept as notes
only after all current-gate obligations are clear. The project manager cannot
close, checkpoint, or advance a gate that has a current-gate caveat.

A blocking inspection issue must be grilled until it has evidence, expected
result, actual result, severity, affected node, affected parent rollups,
affected product model, repair target, and same-inspector recheck condition.
Then it mutates the route:

```text
inspection failure -> issue grill -> PM repair strategy grill
-> PM repair route decision -> route mutation -> repair node
-> repair process model -> repair product model -> repair evidence
-> same-inspector recheck -> resume original route or parent rollup
```

FlowGuard does not score aesthetics directly. It enforces that a failed
human-like inspection cannot be ignored, cannot checkpoint, and cannot
complete until repair and same-inspector recheck evidence pass.

For UI concepts, app icons, product-facing visual assets, and rendered UI
screenshots, the human-like reviewer must write an aesthetic judgement after
neutral observation and before pass/block closure. Record `aesthetic_verdict`
as `pass`, `weak`, or `fail`, plus concrete reasons tied to the shared visual
direction, concept target, product audience, and visible evidence. Reasons may
cover palette, typography, spacing rhythm, material treatment, icon or asset
style, hierarchy, density, composition, polish, distinctiveness, and whether
the result looks template-like, cheap, incoherent, cluttered, or disconnected
from the product. `fail` blocks implementation, checkpoint, package polish,
and completion until repair or regeneration is re-reviewed. `weak` can pass
only with a recorded reason why it is acceptable at this gate or with a
specific follow-up repair target.

A failed gate is a structural decision, not a soft note. FlowPilot marks the
failed child/subnode and its evidence as failed, stale, or superseded, bumps
the route version only after a project-manager repair-strategy grill. That PM
interrogation must decide whether the original child can cover the issue,
whether to reset the child, insert an adjacent repair or regeneration child,
split missing responsibilities into focused children, rebuild the subtree, or
bubble impact upward. It also records stale evidence, repair target, execution
plan, and same-inspector recheck condition. Only then does FlowPilot rewrite
the execution frontier and move the next gate to the repair path. Each reset
or new child then reruns focused interrogation, process model, product model,
execution, neutral observation, inspection, and parent/composite recheck.

Every parent/composite node uses the same structural rule: if the effective
route node has children, it must have a local V-model style backward replay
before it closes. Passing every child locally is not enough. FlowPilot reloads
the child evidence, replays it against the parent product-function model, and
uses human-like inspection to judge whether the children compose into the
parent goal. If not, FlowPilot mutates the route structurally:

- jump back to an affected existing child and invalidate that child plus the
  affected parent rollup;
- insert an adjacent sibling child when the existing child is insufficient;
- rebuild the child subtree when the parent model or interfaces changed;
- bubble the impact to the next parent when the higher contract is affected.

After the changed child or subtree passes, FlowPilot reruns the same parent
backward review before the parent may close. The same pattern repeats upward
for module, phase, and root completion scopes.

## Chunk Execution

Every formal chunk must have:

- intent;
- expected artifacts;
- verification commands or checks;
- allowed exits;
- rollback or recovery route if applicable.

No formal chunk may start until its verification is defined.
No formal chunk may start until host continuation mode is known, continuation
readiness has been checked (automated heartbeat health or manual-resume
freshness), focused
parent-scope grill-me, parent-subtree FlowGuard review, focused node-level
grill-me, and the lightweight continuation self-check are complete. No formal
chunk may start until the fresh current-node FlowPilot Route Sign and current
node roadmap have been shown in chat or, when Cockpit is the primary surface,
visibly confirmed in Cockpit.
No formal chunk may start until `.flowpilot/runs/<run-id>/execution_frontier.json` matches
the active route version and the visible Codex plan has been synced from that
frontier.
No next-node jump may occur while the frontier current-node completion guard
still says the active node is unfinished.

No formal chunk may start until the current parent subtree has been reviewed by
FlowGuard and any unfinished-current-node recovery check confirms that the
route is not skipping an incomplete leaf. If the current node was interrupted
before validation and evidence, the next continuation turn resumes that node
instead of advancing.
No formal chunk may start until the current parent product-function model and
active leaf product-function model have been checked.

Before formal execution, run the reusable quality package:

```text
enter parent or node -> refresh and visibly display FlowPilot Route Sign
-> focused grill-me -> quality package
-> FlowGuard/route check -> execute chunk -> verify -> checkpoint
```

The package records whether the current scope is too thin, whether a low-risk
high-value improvement exists, whether child-skill key milestones are visible
as a mini-route, whether validation is strong enough, and whether checkpoint
closure would be rushed. Classify improvement candidates as small/current
node, medium/later node, large/route mutation, or not doing with reason.

Before checkpoint, run an anti-rough-finish review. If the verified result is
thin, missing states, weakly evidenced, or visibly rushed, do bounded rework
instead of writing the checkpoint.
After anti-rough-finish review, run human-like inspection. Treat technical
verification, screenshots, logs, or app launch as inspection inputs, not as
substitutes for inspection. A checkpoint is allowed only after inspection
passes or every blocking issue has been repaired and rechecked by the same
inspector class.
Before writing the checkpoint, refresh role memory packets for every role that
made a meaningful decision, inspection, FlowGuard approval/block, sidecar
report, or blocker note in the turn. The compact structured packet is the
authoritative recovery state; raw chat transcripts are optional evidence only.

Before writing the checkpoint, also run the lightweight FlowPilot skill
improvement check for the node. Any role may report a FlowPilot skill issue:
unclear protocol, weak template, missing review field, hard-to-find code path,
model/tooling friction, Cockpit display gap, or similar. Append real
observations to
`.flowpilot/runs/<run-id>/flowpilot_skill_improvement_observations.jsonl`.
If no issue is observed, record only that the check was considered; do not
create heavy empty node reports. These observations are independent of the
current project's acceptance gates and do not block current project completion.

Before closing any parent/composite checkpoint, run the local parent backward
replay for that structural parent node. Replay child evidence against the
parent product model, inspect whether the children compose into the parent
goal, require a PM segment decision, and mutate the route if the repair
requires an existing-child rework, an adjacent sibling child, a child-subtree
rebuild, or parent impact bubbling.

## Recursive Route Planning

The first route is a checked model result. FlowPilot generates a candidate
route tree, uses FlowGuard to simulate the root route, and freezes the checked
candidate as the first route version.

When entering a parent layer, FlowPilot treats the existing child plan as model
input:

```text
load child subtree -> emit subtree map -> focused parent grill-me ->
process officer checks parent process model ->
product officer checks parent product model -> adjust or enter children
```

If the parent model finds missing, stale, oversized, misplaced, or unnecessary
child nodes, FlowPilot enters a formal route mutation boundary. The mutation
creates a new route version, rechecks the affected subtree, writes a transition
record, rewrites the execution frontier, syncs the visible Codex plan, and
reruns the same parent review before child execution.

Changes use local re-simulation plus impact bubbling. Start with the direct
parent of the changed node. Rerun higher layers only when the impact affects
their contract. Rerun the whole tree when the impact reaches the root or the
acceptance floor, delivery target, source of truth, major implementation
strategy, or cross-phase dependency changes.

## Experiments

If the next action is unclear, run a bounded experiment instead of a formal
chunk.

Experiment output must state:

- question;
- method;
- evidence;
- conclusion;
- whether the model or route must change.

## Route Updates

Create a new route when structure changes:

- new or removed phase;
- new recovery branch;
- switched implementation strategy;
- discovered model gap;
- rollback then alternate route.
- parent-subtree review changes child nodes;
- child-skill conformance review exposes a route-level gap.
- the quality package classifies an improvement as medium or large.
- human-like inspection or backward review finds a blocking product,
  interaction, visual, localization, conflict, or completion-quality issue.

Do not create a new route for simple progress updates.
Create or revise a route when completion self-interrogation finds obvious
high-value work that should raise the standard.

Changing the chat or Cockpit display of the current route is not enough reason
to create a new route. Use heartbeats, node reports, and checkpoints for
ordinary progress visibility.
Changing the next jump inside an existing checked route is written to the
execution frontier and plan projection; it does not require changing the
heartbeat automation prompt.

## Dependency And Tool Installation

Safe project-local installation is allowed by default when it is needed to run
the active route node, current chunk, checks, or implementation. Record the
missing tool, planned command, reason, and post-install verification before
running it. Record the result afterward.

Do not install every likely dependency during startup. Startup records the
dependency plan and performs only minimal controller/model-check bootstrap.
Known future dependencies should be marked `deferred` until their node or
verification command is active.

Ask before heavy, global, system-wide, paid, private-account, destructive, or
irreversible installation work. Approval allows the install when needed; it does
not mean the install should run before the route reaches the need.

## Child Skill Fidelity

When FlowPilot routes work to another skill, that skill's `SKILL.md` becomes a
hard input to the route. The project manager must first select the skill in
the PM child-skill selection manifest. Only then does the PM read the child
skill, map its workflow and completion standard into the current gates, write
an evidence checklist, assign required approvers, and complete or explicitly
justify each required step.

This is stricter than a prompt reminder. The route should not continue into
implementation or completion until the child-skill contract is loaded, its
requirements are mapped, the PM-owned gate manifest exists, approver roles are
assigned, the evidence plan exists, and final evidence shows the child skill's
own completion standard was met or explicitly waived by the correct role.
FlowPilot must also project key child-skill milestones into current node
details as a mini-route, without copying the child skill's detailed prompt text.

FlowPilot must not compress child skills into vague shortcuts. For example,
`autonomous-concept-ui-redesign` means the non-interactive built-in concept-led
workflow, implementation, iteration, deviation-review, geometry-QA,
screenshot-QA, app-icon realization, and final-verdict pipeline;
`model-first-function-flow` means the real FlowGuard applicability decision,
model, checks, counterexample review, and adoption note where required.

Child-skill use has its own conformance loop:

```text
inventory local skills -> PM selects required/conditional skills
-> load instructions -> extract PM gate manifest
-> assign required approvers -> map workflow -> write evidence checklist
-> show child-skill mini-route -> model/check conformance
-> execute child workflow -> collect evidence -> audit evidence/output match
-> domain-quality review -> strict obligation classification
-> iteration closure -> assigned role approvals -> verify child completion
-> resume parent node
```

For UI skills, the visible mini-route should stay at milestone level, such as
`contract/concept target -> frontend implementation -> design iteration ->
deviation review -> geometry QA -> screenshot QA -> final verdict`. The UI
child skills own the visual execution details.

If any child-skill step is missing, stale, mismatched, or too low quality, the
route returns to the child-skill loop. The parent node does not resume until
the child skill's own completion standard is verified and the current
child-skill gates have the assigned role approvals or explicit blocker/waiver
evidence.
The parent node also does not resume when the child-skill reviewer writes a
current-gate caveat. Current-gate caveats are blocking findings, not future
tasks.

## Prompt Layer Boundary

FlowPilot owns route control, not domain-specific prompt stacks. It records
when a domain skill is needed, loads that skill's instructions, maps the
workflow into the route, and checks that evidence exists before implementation
or completion.

Detailed rules for UI design, visual polish, screenshot review, concept
generation, app icons, FlowGuard modeling technique, or platform-specific
implementation belong to their child skills. FlowPilot should refer to those
skills and their evidence instead of copying their detailed prompt text.

## UI And Visual Evidence

For UI, desktop UI, dashboard, icon, or visual showcase routes, FlowPilot
requires the relevant child skills and evidence; it does not prescribe the
visual design itself.

FlowPilot checks these process facts:

- a UI or visual route was detected;
- `autonomous-concept-ui-redesign` was invoked for UI redesign, implementation,
  polish, visual iteration, deviation review, layout QA, and final UI verdict;
- its internal evidence records built-in concept-led framing/search gates,
  `frontend-design` implementation, `design-iterator` rounds or a recorded
  skip, and `design-implementation-reviewer` deviation review or a recorded
  skip;
- when the user has not set a different iteration count, FlowPilot records the
  autonomous UI refinement budget as 10 `design-iterator` rounds by default
  with a maximum of 20 rounds;
- the child skill produced or explicitly waived the pre-implementation concept
  target/reference decision;
- generated concept targets have both a source decision and an authenticity
  decision. The source gate proves imagegen or an authoritative reference was
  used; it does not prove the target is a valid concept. The authenticity gate
  rejects existing screenshots, existing-image variants, desktop captures,
  taskbar-inclusive captures, old route UI, and prior failed UI evidence with
  cosmetic changes. Authenticity failure blocks implementation and mutates the
  route back to clean concept regeneration;
- generated concept targets include a neutral pre-judgement observation that
  says what the image visibly appears to depict before the authenticity
  decision is made;
- generated concept targets include an aesthetic verdict with concrete
  reviewer reasons before UI implementation planning;
- rendered QA evidence exists after implementation when required by the child
  skill;
- geometry QA evidence exists after implementation and before final visual
  closure; screenshots are required visual sanity evidence but not sufficient
  anti-overlap proof;
- rendered QA evidence includes a rendered-UI aesthetic verdict with concrete
  reviewer reasons before divergence or loop closure;
- rendered QA evidence includes reviewer-owned personal walkthrough evidence
  for interactive UI surfaces: reachable/unreachable controls, exercised
  click/keyboard paths, language/settings/support/tray controls when relevant,
  text overlap/clipping, whitespace, density, crowded areas, hierarchy,
  readability, responsive/window-size fit, and concrete design recommendations;
- material concept/implementation differences have a child-skill loop-closure
  decision;
- product-facing visual assets, when created, are included in the same UI
  child-skill evidence;
- product-facing visual assets include an aesthetic verdict with concrete
  reviewer reasons before UI or package completion;
- post-implementation screenshots are not relabeled as pre-implementation
  concept evidence unless the child skill or user explicitly waived the concept
  target.

## Controller Route Memory And PM Prior-Path Context

The Controller maintains current-run route memory as source-path indexes under
`.flowpilot/runs/<run-id>/route_memory/`:

- `route_history_index.json` records the active frontier, effective nodes,
  completed nodes, superseded nodes, route mutations, stale evidence ids,
  review block/pass markers, research or modeling outputs, and concrete source
  paths.
- `pm_prior_path_context.json` is the PM-facing decision brief derived from the
  same index.

Both files are generated by the Controller, but the Controller has no decision
authority and must not read sealed packet or result bodies to build them. These
files are navigation aids and source indexes, not product acceptance evidence.

Before any protected PM decision, the Controller refreshes route memory and
the PM must read both files. Protected decisions include route drafting,
resume continuation, current-node acceptance planning, repair choice, route
mutation, parent segment decisions, evidence-quality packaging, final ledger
construction, and closure. The PM output must include
`prior_path_context_review` with both route-memory source paths, completed
nodes considered, superseded nodes considered, stale evidence considered,
prior blocks or experiments considered, and the impact on the decision. If the
PM treats the Controller summary as evidence instead of an index, the decision
is invalid.

## Final Route-Wide Gate Ledger

Before terminal completion, the project manager rebuilds
`.flowpilot/runs/<run-id>/final_route_wide_gate_ledger.json` from the current active route,
not from the initial plan. The ledger is dynamic: it reads current-run
`state.json`, `execution_frontier.json`, the active `flow.json`, capability evidence, node
reports, repair records, child-skill manifests, reviewer reports, model
reports, waivers, and superseded-node history.

The ledger must resolve:

- which route version is current;
- which nodes and gates are effective after route mutation;
- which nodes or gates are superseded, and why;
- every child-skill gate and child-skill completion standard still relevant to
  the current route;
- every human-like inspection, structurally required local parent backward
  replay, strict-obligation, and same-inspector recheck gate;
- every product-function and development-process model gate;
- root acceptance contract obligations, selected standard scenarios, and node
  acceptance plans for all effective nodes;
- every generated resource, including concept images, product-facing visual
  assets, screenshots, route diagrams, model reports, and other generated
  artifacts, with a current generated-resource-ledger disposition of
  `selected`, `used`, `superseded`, `discarded`, `deleted`, or `quarantined`;
- stale, invalidated, missing, waived, blocked, and unresolved evidence;
- residual risk triage with zero unresolved residual risks.

The project manager then converts the clean ledger into
`.flowpilot/runs/<run-id>/terminal_human_backward_replay_map.json`. This is an
ordered human-review map, not another evidence checklist. It tells the
human-like reviewer to start from the delivered product itself, then walk
backward through root acceptance, effective parent/module nodes, and every
effective leaf node. For each segment the reviewer must personally inspect or
operate the current artifact, compare it with the root contract, parent goal,
node acceptance plan, standard scenarios, and node-risk scenarios, and write a
human-review report. Worker reports, screenshots, model summaries, and ledger
entries are pointers only.

After each replay segment, the project manager records a segment decision:
continue, repair, route mutation, correct-role exception, or PM stop. The PM
may not accept a segment that the reviewer checked only from reports. If the
reviewer finds a real product, parent, leaf-node, interaction, evidence, or
risk issue, the PM routes it to the appropriate repair target and records
which downstream nodes and evidence became stale. A repair normally restarts
the final human backward replay from the delivered product. A narrower restart
from an impacted ancestor is allowed only when the PM records a concrete reason
showing the repair cannot affect earlier segments. In all cases, repair or
route mutation makes the existing terminal ledger stale; the final ledger is
rebuilt, the replay map is rebuilt, reviewer backward replay reruns, and PM
approval is reissued before completion can continue.

PM completion approval is valid only after the terminal human backward replay
passes, every replay segment has a PM decision, the repair/restart policy is
recorded, the ledger's `unresolved_count` is zero, and the PM has written
independent adversarial audit evidence for the completion decision. The PM
audit cites the current route/frontier, effective ledger entries,
stale/superseded evidence checks, waiver authority, unresolved counts, reviewer
replay path, selected scenario replay, node acceptance plan coverage, and risk
triage. If any entry is missing, stale, blocked, unapproved, wrongly
superseded, untriaged, or still risk-bearing, the PM chooses repair, route
mutation, correct-role waiver, or PM stop. After repair or route mutation, the
final ledger is rebuilt and replayed again before completion can continue.

Completion reports must not carry unresolved residual risks. The terminal
ledger can retain resolved issues, non-risk scope notes, and explicit
exceptions with required approval; it cannot close while `blocking`,
`test_gap`, `evidence_gap`, or `route_gap` items remain.

## Completion

Completion requires:

- frozen contract still intact;
- route checked;
- current summaries synced;
- required capability evidence present;
- subagent work merged;
- final verification passed;
- anti-rough-finish review passed;
- every completed node has product-function model evidence, human-like
  inspection evidence, and any blocking issue closed through same-inspector
  recheck;
- every completed review gate has strict obligation evidence showing that no
  current-gate requirement was deferred as a caveat;
- every effective route node with children has local parent backward replay
  evidence, including the structural trigger, reviewer replay, PM segment
  decision, and route mutation/rerun evidence for any failed parent rollup;
- final product-function model replay and final human-like inspection passed;
- final feature matrix, acceptance matrix, and quality-candidate reviews
  completed;
- completion self-interrogation found no obvious high-value work remaining;
- PM-owned final route-wide gate ledger rebuilt from the current route, with
  effective nodes resolved, child-skill gates collected, root acceptance and
  node acceptance obligations accounted for, selected standard scenarios
  replayed, evidence credibility ledger reconciled, stale evidence checked,
  superseded nodes explained, zero unresolved items, zero open blockers, zero
  fixed-pending-recheck defects, zero unresolved residual risks, terminal human backward replay map
  built, reviewer replay from delivered product through root, parent, and leaf
  nodes passed, every replay segment has a PM decision, repair/restart policy
  recorded, and PM ledger approval recorded;
- terminal closure suite synchronized terminal state files, refreshed terminal
  evidence, rebuilt final ledger if evidence changed, reconciled lifecycle
  authorities, and found zero required cleanup actions;
- PM-owned FlowPilot skill improvement report written from the run's
  observation log, including the no-obvious-issue case. The report's
  observations are for later manual FlowPilot root-repo maintenance and do not
  require root-repo fixes before the current project completes;
- host continuation mode reconciled: heartbeat shutdown when automated
  continuation was used, or manual-resume no-automation evidence written when
  unsupported;
- lifecycle reconciliation scanned Codex heartbeat automations, local state,
  frontier, and heartbeat/manual-resume evidence;
- terminal continuation lifecycle state written back to local
  state/frontier/lifecycle/heartbeat or manual-resume evidence;
- crew ledger and role memory packets archived with final role statuses;
- completion report emitted.
