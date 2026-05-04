---
name: flowpilot
description: Opt-in only. Use this skill only when the user explicitly asks to use FlowPilot or the flowpilot skill, for example "Use FlowPilot" or "使用 FlowPilot"; do not activate implicitly for large tasks, existing .flowpilot directories, UI redesigns, heartbeat requests, or repository work.
---

# FlowPilot

FlowPilot is a project-level orchestration skill. It turns a substantial
software request into a showcase-grade, model-backed control loop that can
survive long sessions, handoffs, route changes, verification failures,
standard increases, and optional parallel work.

Use FlowPilot for the project controller. Use FlowGuard for executable process
design, route validation, and task-local behavior models.

## Core Rule

Do not lower or reinterpret the frozen acceptance contract. Treat the frozen
contract as the acceptance floor, not as the ceiling. The model, route, next
chunk, recovery path, and capability choices may change, and later
self-interrogation may raise standards when obvious high-value work remains.
The original completion floor may not silently change.

## Experimental Packet-Gated Control Plane

When a formal FlowPilot run uses background agents, the main assistant is the
controller, not the default implementation worker. The controller may hold the
global route state, relay messages, maintain the live status board, and request
the next decision, but it must not personally perform product implementation,
stateful project work, route advancement, review closure, or PM approval.

The controller's allowed actions are:

- record and relay PM-authored node packets;
- relay worker results to the reviewer;
- relay reviewer decisions to the PM;
- maintain a packet/status ledger;
- perform read-only consistency checks needed to route the packet;
- stop for the user only on hard blockers, explicit human gates, or completion.

The controller's forbidden actions are:

- writing product code, project data, route evidence, screenshots, or release
  artifacts for a worker node;
- installing dependencies or running stateful commands for a worker node;
- marking route nodes complete from controller-origin evidence;
- writing reviewer pass decisions or PM advance decisions for itself;
- dispatching a worker without a current PM packet and reviewer dispatch pass;
- using later route knowledge to expand a worker packet beyond its current
  node.

Role-origin evidence is a hard gate. Only artifacts produced by the authorized
role for the current node can close that node. Controller-origin
implementation artifacts cannot close worker gates. Controller-origin review
artifacts cannot close reviewer gates. Controller-origin PM approval artifacts
cannot close PM gates. If the reviewer detects a role-origin mismatch, the
decision must be `block_invalid_role_origin`, and the PM may not advance from
that evidence. The PM must either discard the evidence, issue a repair packet
to an authorized worker, or quarantine/restart the run if the contamination
affects trust in the route.

Workers use least-context node packets. A worker receives only the current
packet, not the full route, not downstream nodes, and not a general instruction
to complete the whole project. Each packet must include:

```text
NODE_PACKET:
  packet_id:
  node_id:
  objective:
  inputs:
  allowed_read_paths:
  allowed_write_paths:
  allowed_commands_or_side_effects:
  forbidden_actions:
  acceptance_slice:
  verification_required:
  return_format:
  stop_after_result: true
```

Worker output is a packet result, not a route decision:

```text
NODE_RESULT:
  packet_id:
  node_id:
  status: completed | blocked | needs_pm
  changed_files:
  commands_run:
  evidence:
  open_issues:
  request_next_packet: true
```

PM and reviewer decisions must be machine-consumable:

```text
REVIEW_DECISION:
  packet_id:
  decision: pass | block | needs_repair | needs_user
  can_pm_advance: true | false
  blocking_issues:
```

```text
PM_DECISION:
  decision: issue_next_packet | repair_current | mutate_route | block_user | complete
  next_packet:
  stop_for_user: true | false
  controller_reminder: "Controller: relay and coordinate only. Do not implement, install, edit, test, approve, or advance from your own evidence."
```

Every PM response to the controller must include `controller_reminder`. The PM
must restate that the main assistant is only the packet-flow controller and may
not personally perform implementation, dependency installation, stateful
commands, gate approval, route advancement, or evidence generation. If a PM
response omits this reminder, the controller must request a corrected
`PM_DECISION` before dispatching work.

Every sub-agent response to the controller must include the same controller
role reminder, adapted to that agent's role. The controller must also include a
role reminder in every message it sends to a sub-agent:

```text
ROLE_REMINDER:
  controller_boundary: "Main assistant is Controller only: relay, coordinate, record status, and request role decisions. It must not implement or close gates from its own evidence."
  recipient_role:
  recipient_allowed_actions:
  recipient_forbidden_actions:
  return_to_controller_only: true
```

If a worker, reviewer, PM, officer, simulator, or verifier response omits its
role reminder, the controller requests a corrected response before using it as
gate evidence. If the controller omits the recipient role reminder when
dispatching a packet, the reviewer must block dispatch as
`missing_role_reminder`.

The worker stops after `NODE_RESULT`, but the FlowPilot controller does not
stop for the user merely because a worker, reviewer, or PM produced an
intermediate packet. If `stop_for_user` is false and no hard blocker exists,
the controller immediately continues the internal loop: reviewer result -> PM
decision -> next packet -> reviewer dispatch approval -> worker dispatch.

If a host provides a tool broker or permission layer, every state-changing tool
call must require a current execution ticket derived from PM and reviewer
decisions. If no such broker exists, the role-origin evidence rule still
applies: unauthorized controller work is invalid and cannot close any gate.

The live FlowPilot status surface should report packet location rather than
implementation progress invented by the controller:

```text
Flow Status:
  run_id:
  active_node:
  packet_id:
  holder: PM | Reviewer | WorkerA | WorkerB | Controller | User
  pm_authorization:
  reviewer_dispatch:
  worker_status:
  reviewer_result:
  next_expected_event:
  controller_allowed_action:
```

## Required Dependencies

- Real `flowguard` Python package.
- `model-first-function-flow` skill.
- `flowpilot.dependencies.json` in the source repository for installer-readable
  dependency checks.
- Persistent project directory with `.flowpilot/`.

Before model-backed work:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
```

If this fails, connect the real FlowGuard toolchain or mark setup blocked. Do
not create a fake substitute.

For repository installation, prefer:

```powershell
python scripts/install_flowpilot.py --install-missing
python scripts/check_install.py
```

Before public release, use `python scripts/check_public_release.py`. That
preflight is scoped to the FlowPilot repository only and must not publish,
package, push, tag, or upload companion skills.

Host-specific tools are capability-mapped. In Codex, visual routes may satisfy
`raster_image_generation` through the built-in `imagegen` skill. Other hosts
may use a differently named image-generation provider, but FlowPilot must
record the provider identity and check evidence before running the visual gate.

## Explicit Activation Only

FlowPilot is opt-in only. Enable the controller only when the user explicitly
asks to use FlowPilot or the `flowpilot` skill in the current thread. Do not
infer activation from task size, long-running scope, repository type, UI work,
heartbeat language, or the presence of `.flowpilot/`.

If a project already contains `.flowpilot/`, treat it only as resume or
continuity state after explicit invocation. The directory is not a trigger by
itself.

Every formal FlowPilot invocation creates a new active run directory under
`.flowpilot/runs/<run-id>/`. The top-level `.flowpilot/current.json` is only a
pointer to the active run, and `.flowpilot/index.json` is only a catalog of
runs for audit and Cockpit tabs. All mutable control state for the run lives
under that run root. The active-run resolver is authoritative: read
`.flowpilot/current.json`, then load `.flowpilot/runs/<run-id>/`. Old top-level
state files are legacy evidence only and must not silently override an active
run. If the user asks to continue previous work, create a new run anyway,
record `continues_from_run_id`, and import prior run/project materials as
read-only inputs; do not reuse old control state, old live-agent IDs, old route
gates, old screenshots, or old generated assets as current evidence.

If the user is editing, auditing, discussing, or repairing the FlowPilot skill
itself without explicitly asking to use FlowPilot, treat that as ordinary
repository work. Do not start a FlowPilot route, heartbeat, subagent crew,
startup banner, or startup questionnaire for that maintenance task.

Preferred user-facing invocation when a formal route is intended:

```text
Use FlowPilot. Ask the startup questions first.
```

This wording matters. FlowPilot invocation is only permission to enter the
startup questionnaire. It is not permission to choose a default mode, start
background subagents, skip background subagents, create heartbeat/automation
jobs, or fall back to manual resume.

## Four-Question Startup Gate

Before the banner, route creation, child skills, image generation,
implementation, or model-backed work, FlowPilot must ask exactly these startup
questions and stop until all four have explicit answers:

1. Run mode: `full-auto`, `autonomous`, `guided`, or `strict-gated`.
2. Background agents: allow the standard six live background subagents, or use
   single-agent six-role continuity for this run.
3. Scheduled continuation: allow heartbeat/automation jobs, or use manual
   resume only for this run.
4. Display surface: open the FlowPilot Cockpit UI immediately when startup
   state is ready, or keep using chat route signs for this run.

The user may answer in one compact sentence, such as
`FlowPilot: full-auto, allow background agents, allow heartbeat, open Cockpit`.
That counts as all four answers only if the answers are explicit. If any answer is
missing, ambiguous, or says to pause, FlowPilot must remain in
`startup_pending_user_answers` and ask for the missing answer. Do not infer an
answer from "use FlowPilot", from the task's importance, from current tool
availability, or from previous routes.

After asking the four questions, the assistant's response must end immediately
and control must return to the user. Do not keep planning, inspecting files,
starting tools, creating route state, launching subagents, probing heartbeat, or
showing the banner in the same response that asks the questions. Record this as
`startup_activation.startup_questions.dialog_stopped_for_user_answers: true`
before accepting a later user reply as startup-question evidence.

Only after the four startup answers are recorded from the later user reply may
FlowPilot emit the startup banner in a fenced `text` block. The banner means the
startup-question gate is open and formal FlowPilot startup has begun:

```text
███████╗██╗      ██████╗ ██╗    ██╗██████╗ ██╗██╗      ██████╗ ████████╗
██╔════╝██║     ██╔═══██╗██║    ██║██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝
█████╗  ██║     ██║   ██║██║ █╗ ██║██████╔╝██║██║     ██║   ██║   ██║
██╔══╝  ██║     ██║   ██║██║███╗██║██╔═══╝ ██║██║     ██║   ██║   ██║
██║     ███████╗╚██████╔╝╚███╔███╔╝██║     ██║███████╗╚██████╔╝   ██║
╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝
```

A formal FlowPilot route is not a lightweight tier. If FlowPilot is the active
driver, start at showcase-grade scope with long-horizon expectations, visible
self-interrogation, host-probed continuation, FlowGuard process design, and
completion-time high-value review. If the host supports real wakeups, use real
heartbeat continuity. If the host does not support wakeups, record manual
resume evidence instead of downgrading the route.

For tiny maintenance inside an already active FlowPilot project, record
continuity in `.flowpilot/` when useful, but do not claim that a full formal
FlowPilot route has completed unless the showcase-grade gates actually ran.

## Startup Hard Gate

Formal FlowPilot startup is an activation transaction, not a collection of
optional status notes. Before any child skill, image generation, implementation
chunk, route-execution chunk, or completion work starts, the controller must
prove that the same active nonterminal route is current in:

- `.flowpilot/current.json` and `.flowpilot/index.json`;
- `.flowpilot/runs/<run-id>/run.json`;
- `.flowpilot/runs/<run-id>/state.json`;
- `.flowpilot/runs/<run-id>/execution_frontier.json`;
- `.flowpilot/runs/<run-id>/routes/<active-route>/flow.json`;
- `.flowpilot/runs/<run-id>/crew_ledger.json`;
- all six role memory packets;
- continuation evidence, either automated heartbeat readiness or explicit
  `manual-resume` no-automation evidence.

The human-like reviewer must personally check facts and write
`.flowpilot/runs/<run-id>/startup_review/latest.json`. This is not approval and it is not a
copy of worker claims. The report must include the actual evidence sources
checked: user answers, current run pointer/index, current state/frontier/route,
crew and role memory, live background-agent birth evidence, prior-run import
boundary, old-route/old-asset cleanup boundary, and real Codex heartbeat or
manual-resume evidence.

The project manager reads that factual report, either sends concrete
remediation items back to authorized workers through a PM-authored packet or writes
`.flowpilot/runs/<run-id>/startup_pm_gate/latest.json` opening startup from the current clean
reviewer report.

Opening startup does not authorize the controller to begin implementation. It
only authorizes the packet loop to begin. The first work beyond startup must be
a PM-authored `NODE_PACKET`, followed by reviewer dispatch approval. The
controller may not convert startup approval into direct execution, dependency
installation, source extraction, implementation, QA, or route advancement.

`startup_activation.work_beyond_startup_allowed` must be true in state and
frontier before work beyond startup, and that flag may be written only by the
PM start-gate decision after a clean factual reviewer report.
`startup_activation` must include `startup_preflight_review` and
`pm_start_gate` blocks.
`startup_activation.startup_questions`
must show that the four-question prompt was asked before the banner, that the
assistant stopped to wait for the user's reply, and that explicit answers for
run mode, background agents, scheduled continuation, and display surface were
later recorded before the banner is considered valid. The display-surface
answer controls the first user-facing progress surface after startup state is
ready: if the user chose Cockpit, open the Cockpit UI immediately and record
visible Cockpit evidence; if the user chose chat, show the chat FlowPilot Route
Sign as before. The reviewer report must compare user
authorization against actual state: live/single-agent role evidence,
heartbeat/manual-resume evidence, route/state/frontier consistency, stale or
residual route state, current run isolation, and any required old-route or old
asset cleanup. `startup_activation` must then agree
with those answers: live
background agents only when the user allowed them and only when all six role
agents were freshly spawned for this formal FlowPilot task after the startup
answers and current route allocation. A new FlowPilot task must not reuse,
resume, or relabel historical `agent_id` values from prior route ledgers or
role-memory packets as current live-agent evidence; historical IDs are audit
history only. Single-agent six-role continuity is allowed only when the user
selected it, and heartbeat/automation only when the user allowed scheduled
continuation. If any answer, wait-state evidence, fresh live-agent evidence,
reviewer report, PM open decision, or cleanup evidence is missing, stop at
startup and route remediation back through PM and workers; do not silently fall
back. If control files are written at the top-level `.flowpilot/` instead of
the active run root, quarantine or migrate them before startup can open. If
only a route-local file, generated concept,
screenshot, or implementation artifact exists without matching canonical
state/frontier/crew/continuation evidence, treat it as a shadow route,
quarantine or supersede it, and rerun startup instead of continuing from that
partial state.

FlowPilot is especially useful when the task involves:

- building or refactoring a large software system;
- stateful workflows, retries, queues, caches, or side effects;
- long-running work that benefits from heartbeat-style continuation when the
  host supports it;
- route updates or recovery branches;
- child-node sidecar subagents;
- user-facing UI that requires concept and screenshot verification.

## Run Modes

Run modes affect autonomy and human gates, not quality tier. Every formal
FlowPilot mode still uses the same showcase-grade completion floor.

- `full-auto`: the agent can execute non-destructive chunks and bounded
  recovery automatically, but still stops for hard gates.
- `autonomous`: the agent executes the route and stops only at hard gates,
  blockers, or materially ambiguous choices.
- `guided`: the agent drafts the route and asks before high-impact choices.
- `strict-gated`: every formal chunk waits for explicit human approval after
  verification is defined.

At startup, ask for these modes left-to-right from loosest to strictest:
`full-auto`, `autonomous`, `guided`, `strict-gated`. Do not record a default
mode for a formal route unless the user explicitly answers the mode question.
The simplified `Use FlowPilot` / `使用开始` trigger never carries implied startup
answers. It asks the four questions and stops; the next user reply may answer
all four in one compact sentence.

## Startup Workflow

1. On FlowPilot invocation, enter `startup_pending_user_answers`.
2. Ask the four startup questions: run mode, background-agent permission,
   scheduled-continuation permission, and whether to open Cockpit UI. End the
   assistant response immediately
   after the questions and wait for the user's reply. No plan continuation, tool
   call, route write, child-skill loading, imagegen, subagent startup, heartbeat
   probe, or banner is allowed in that question-asking response.
3. Record the explicit answer set in state/frontier startup activation
   evidence. Do not infer fallback authorization.
4. Emit the fenced startup banner in chat so the user can clearly see the
   startup-question gate has opened and the formal FlowPilot controller has
   started.
5. Enable FlowPilot, ensure `.flowpilot/` exists, create a new
   `.flowpilot/runs/<run-id>/` directory, update `.flowpilot/current.json` and
   `.flowpilot/index.json`, and record the selected mode inside the run root.
6. Commit the showcase-grade long-horizon floor. A formal FlowPilot invocation
   means the project is important: the project manager sets the highest
   reasonably achievable standard for strong AI workers, not the lowest viable
   route and not an estimate of the PM's own effort.
7. Run visible full grill-me using FlowPilot's formal invocation policy. In
   the same startup round, draft the intended acceptance floor, seed the
   improvement candidate pool, seed the initial validation direction, and
   surface product-function questions. Do not freeze the contract yet.
8. Create the fixed six-agent crew for the new formal FlowPilot task and write
   `.flowpilot/runs/<run-id>/crew_ledger.json` plus one compact role memory
   packet under `.flowpilot/runs/<run-id>/crew_memory/` for each role: project manager, human-like
   reviewer, process FlowGuard officer, product FlowGuard officer, worker A,
   and worker B. Persist role authority, agent ids or recovery status, latest
   report paths, memory paths, replacement rules, and role-memory freshness
   before formal route work. At formal startup, `agent_id` values must be new
   for this FlowPilot task. Stored IDs from older routes or earlier tasks may
   seed role memory or be listed as excluded history, but they must not be
   resumed or counted as the current six live background agents. Same-route
   heartbeat/manual-resume turns may later resume or replace only this
   task-born cohort.
9. Give the project manager the startup self-interrogation evidence, draft
   floor, current crew ledger, and current role memory packets. The project
   manager ratifies the startup interrogation. From this point the project
   manager owns route, resume, repair, and completion decisions; the main
   assistant becomes the controller for packet flow and may not act as the
   implementation worker unless a PM packet explicitly assigns a small
   controller-owned administrative task and the reviewer approves that role
   assignment.
9a. If background agents are allowed, work beyond startup must use the
    packet-gated control plane. The PM writes the first `NODE_PACKET`, the
    reviewer approves or blocks dispatch, and only then may a worker receive
    the packet. The controller relays packets and status only. If the
    controller performs implementation or writes gate-closing evidence itself,
    the reviewer must mark the evidence invalid for role-origin mismatch.
10. Before PM product-function synthesis or route decisions, require a
    PM-authored material-intake `NODE_PACKET` and reviewer dispatch approval.
    The authorized worker writes
    `.flowpilot/runs/<run-id>/material_intake_packet.json`. This packet
    inventories user-provided and repository-local materials, summarizes what
    each source is for, classifies authority/freshness/contradictions/missing
    context, inventories locally available skills and host capabilities as
    candidate resources, and names what remains unread or uncertain. Local
    skill availability is descriptive material only; it is not permission to
    invoke that skill. If the controller writes this artifact without explicit
    PM packet assignment and reviewer dispatch approval, the reviewer must
    reject it as controller-origin evidence.
11. The human-like reviewer must approve material sufficiency before PM route
    planning. The reviewer checks whether the packet is clear enough for the
    project manager: no obvious sources omitted, source summaries are not
    superficial, large tables/documents are sampled or scoped honestly,
    contradictions and uncertainty are visible, and the packet will not
    mislead route design. If the reviewer blocks, the PM issues a repair
    `NODE_PACKET` to an authorized worker; the controller only relays the
    packet and may not revise the intake itself.
12. The project manager writes
    `.flowpilot/pm_material_understanding.json` from the reviewed packet and
    user intent. It records source-claim matrix, open questions, material
    complexity (`simple`, `normal`, or `messy/raw`), and whether materials can
    feed product/route design directly or require a formal discovery, cleanup,
    modeling, validation, or research subtree before implementation.
13. If the PM records a material, mechanism, source, validation, or experiment
    gap that affects product architecture, route choice, node acceptance, or
    implementation, the PM must convert that gap into a formal research package
    before dependent planning continues. The package assigns worker A, worker B,
    or another explicitly authorized non-controller worker to search, inspect,
    reconcile, model, or run a bounded
    experiment; records allowed source/tool boundaries including web/browser
    availability and private/paid/account hard gates; and defines reviewer
    source checks and stop conditions. Worker output is a pointer only. The
    human-like reviewer must directly check original sources, search results,
    local files, logs, screenshots, or experiment outputs before passing
    sufficiency. Reviewer failure returns to worker rework, route mutation,
    user clarification, or block. PM may use the result only after reviewer
    sufficiency passes and PM absorbs the research into material understanding,
    product architecture inputs, or a route mutation.
14. Require the project manager to synthesize
    `.flowpilot/runs/<run-id>/product_function_architecture.json` before contract freeze.
    The package must include a user-task map, product capability map, feature
    necessity decisions (`must`, `should`, `optional`, `reject`), a high-standard
    posture, strongest feasible product target, explicit unacceptable-result
    review, semantic-fidelity and no-silent-downgrade policy, display rationale
    for every visible label/control/status/card, missing high-value feature
    review, negative scope, and a functional acceptance matrix.
15. The product FlowGuard officer approves or blocks whether the architecture
    can be modeled and checked. The human-like reviewer challenges usefulness:
    unnecessary features, unnecessary visible text, missing workflow support,
    bad defaults, weak failure states, silent semantic downgrades, placeholder
    or embarrassing artifacts, and gaps between user tasks and product
    behavior. If either role blocks, the project manager revises the package
    before the route continues.
16. Freeze the acceptance contract as a floor, not a ceiling, from the
    approved product-function architecture and startup self-interrogation.
17. Write `capabilities.json`, including product-function architecture
    evidence.
18. Ask the project manager to write
    `.flowpilot/runs/<run-id>/pm_child_skill_selection.json` from the product
    capability map, frozen contract, capabilities manifest, and local skill
    inventory. The PM classifies candidate skills as `required`,
    `conditional`, `deferred`, or `rejected`, with reasons. Skills that exist
    locally but do not serve the product are rejected or deferred; availability
    alone never creates route work.
19. Ask the project manager to discover child-skill gates only from the
    PM-selected skills. For each likely invoked child skill, load the child
    skill's `SKILL.md` and only the relevant references, then extract a
    child-skill gate manifest: key stages, required checks, standards,
    evidence needs, skipped references with reasons, and the visible
    mini-route. This is route-design input, not an execution-time afterthought.
19. Assign `required_approver` for every child-skill gate before route
    modeling. Product, visual, interaction, real-use, and strict-review gates
    require the human-like reviewer when they are review judgements; process
    and conformance gates require the process FlowGuard officer; product or
    functional behavior gates require the product FlowGuard officer; route
    inclusion, route mutation, and parent return require the project manager.
    The controller, worker A, and worker B are forbidden approvers for
    child-skill gates.
20. Have the human-like reviewer, process FlowGuard officer, and product
    FlowGuard officer review their slices of the child-skill gate manifest.
    The project manager then approves or blocks manifest inclusion in the
    initial route, execution frontier, and PM completion runway.
21. Verify FlowGuard and required skills.
22. Inspect dependency/tool needs and write a dependency plan.
23. Install only the minimum dependencies needed for FlowPilot itself and the
    current route/model checks.
24. Defer future route, chunk, or native-build dependencies until the node or
    check that actually needs them.
25. Probe the host continuation capability only after the user has answered
    the scheduled-continuation startup question. If the user allowed scheduled
    continuation and setup fails or is unsupported, stop and ask for a new
    decision; do not silently switch to manual resume.
26. If the user allowed scheduled continuation and the host supports real
    wakeups or automations, create the continuation as one lifecycle setup:
    stable one-minute heartbeat launcher. The heartbeat prompt should load
    persisted state, the execution frontier, packet ledger, crew ledger, and
    role memory packets, restore or replace the crew from that memory, and ask
    the project manager for the current `PM_DECISION` plus a
    completion-oriented runway. The controller may only relay PM packets,
    reviewer dispatch/review decisions, worker results, and status; it should
    not be rewritten for ordinary route or plan changes.
27. If the user selected manual resume, do not create heartbeat automation.
    Record `manual-resume` continuation mode,
    keep `.flowpilot/` state/checkpoints authoritative, and continue the formal
    route without claiming unattended recovery.
28. Ask the project manager for the initial route-design decision.
29. Ask the process FlowGuard officer to use FlowGuard as process designer for
    the control route. The PM writes an officer-owned modeling request first;
    the request is dispatched to the matching officer run directory and names
    any non-dependent read-only coordination the controller may relay while
    the officer works.
30. Generate a candidate route tree from the approved product-function
    architecture, frozen contract, and PM-approved child-skill gate manifest.
31. The process FlowGuard officer authors, runs, interprets, and approves or
    blocks the root development-process model against that candidate tree in
    its own officer run directory.
32. The product FlowGuard officer authors, runs, interprets, and approves or
    blocks the root product-function model for what the product or workflow
    itself must do, using the approved product-function architecture as a
    source artifact, in its own officer run directory.
33. The matching officers inspect counterexamples for both model scopes and
    write approve/block reports with `model_author_role`, `model_runner_role`,
    `model_interpreter_role`, `commands_run_by_officer`, input snapshots,
    state/edge counts, missing-label or counterexample inspection, PM risk
    tiers, model-derived review agenda, toolchain/model improvement
    suggestions, confidence boundary, blindspots, and decision. A report that
    only reviews controller-origin outputs is not a completed FlowGuard gate.
34. The process FlowGuard officer authors and runs the strict gate-obligation
    review model so reviewer caveats cannot close a current gate unless all
    current-scope obligations are already resolved.
35. Freeze the checked candidate as the first route version in `flow.json`.
36. Generate English `flow.md`.
37. Write `.flowpilot/runs/<run-id>/execution_frontier.json` from the checked route, active
    node, current subnode/gate when applicable, next node, current mainline,
    fallback, and checks before the next jump. Include the current-node
    completion guard: whether the active node is unfinished, the concrete
    `current_subnode` or `next_gate` that must run next, what evidence is
    required before advance, and whether advance is currently allowed. Include
    the latest project-manager completion runway: current gate, downstream
    steps to completion, role/hard-stop boundaries, checkpoint cadence, and any
    PM stop signal.
38. Sync the visible Codex plan list from the latest PM completion runway, not
    only from the next local gate. Replace the current visible plan projection
    whenever the PM issues a new runway, while retaining old PM decisions and
    checkpoints as history. If the host exposes a native visible plan/task
    list tool, such as Codex `update_plan`, call that tool immediately with
    the PM runway before executing work. Writing `.flowpilot` plan evidence
    alone does not satisfy this gate when the native tool exists. Do not
    change the heartbeat automation prompt just because the route or next jump
    changed.
39. Emit the simplified English FlowPilot Route Sign Mermaid in chat when this
    is startup, a new major `flow.json` route-node entry, parent/module or leaf
    route-node entry, PM current-node work brief, legacy key node change, route
    mutation, review/validation failure return, completion review, or user
    request, unless Cockpit UI is open and showing the same graph. Major node
    means an effective node in the current route/mainline, not an internal
    subnode, micro-step, or heartbeat tick. Include active route, active node, next jumps,
    checks, fallback or repair branches, continuation state, and current
    acceptance delta as nearby text. If the route returns for repair, the
    Mermaid must show that return edge and the reviewer must check the visible
    chat block before the node can advance. Generated files or display packets
    alone do not satisfy this gate.
40. Set `startup_activation` in state/frontier from the four-question prompt,
    the recorded stop-and-wait state, the four explicit startup answers,
    banner evidence, current route, execution frontier, crew ledger, role
    memory, live-subagent startup decision and current-task freshness,
    continuation, and visible plan evidence. The human-like reviewer then writes
    `.flowpilot/runs/<run-id>/startup_review/latest.json` from direct fact checks. The report
    checks user authorization against actual state, including background-agent
    count and role identity, the real route heartbeat automation at one minute
    when scheduled continuation is allowed, manual-resume evidence when manual
    continuation is selected, route/state/frontier consistency, residual or
    shadow route state, and any user-requested clean-start or old-asset
    cleanup. If the user allowed
    background agents, the reviewer verifies six live role-bearing subagents
    were freshly spawned for this FlowPilot task after that user decision and
    after current route allocation, and verifies that no current `agent_id`
    comes from prior route ledgers or older role-memory packets. If the user
    chose single-agent continuity, the reviewer verifies explicit fallback
    authorization and does not claim live subagents. The reviewer does not
    output approval and cannot open startup.
    The project manager reads the report. If it has blocking findings, the PM
    sends concrete remediation items back to authorized workers through a PM
    packet and requires another reviewer report after repair. If the report has no
    blockers, the PM writes `pm_start_gate` evidence opening startup from that
    exact factual report and sets `work_beyond_startup_allowed: true`.

    Do not run child skills, imagegen, implementation, formal route chunks, or
    completion work until the PM records
    `work_beyond_startup_allowed: true`. If the four startup answers are not
    complete, if the prompt did not stop for the user's reply, if the banner was
    emitted before the answers, if live-agent evidence conflicts with the
    background-agent answer, if any current live-agent ID was reused from prior
    routes or older tasks, or if continuation evidence conflicts with the
    scheduled-continuation answer, or if old-route cleanup evidence is missing
    after a clean-start user request, the PM sends the issue back for worker
    remediation. A route-local file without matching canonical
    state/frontier/crew/continuation evidence is a shadow route and must be
    quarantined or superseded before continuing.
40. Execute the first bounded chunk only after the continuation mode is known.
    In automated mode, the heartbeat rehydrates the crew from persisted role
    memory, asks the project manager for a completion-oriented runway, and the
    controller syncs that runway into the current visible plan projection.
    In manual-resume mode, the active turn loads the same
    state/frontier/crew-memory inputs and asks the project manager for the same
    completion-oriented runway. In both modes,
    parent-subtree review, unfinished-current-node recovery check, focused/node
    self-interrogation, the quality package, child-skill gates when needed,
    dual-layer product/process gates, human-like inspection gates, and
    verification must be defined before work advances.

## Material Intake And PM Handoff

This gate sits after startup self-interrogation is ratified and before the
project manager writes the product-function architecture, freezes the contract,
or chooses the initial route. It prevents FlowPilot from planning from an
unclear pile of files, screenshots, tables, notes, prior route evidence, or
unread repository state.

Material intake is worker-owned under packet control. The PM writes a
material-intake `NODE_PACKET`, the reviewer approves dispatch, and the
authorized worker writes
`.flowpilot/runs/<run-id>/material_intake_packet.json`. The controller may
relay source lists and status only; controller-origin intake evidence cannot
close this gate. The packet records:

- `user_intent`: the user request and the decision the materials must support;
- `material_inventory`: each user-provided, repository-local, generated, or
  referenced source, with path/source, format, size or scope, current status,
  and why it might matter;
- `source_summaries`: what each source appears to contain, what it is for, and
  what it does not prove;
- `source_quality`: authority, freshness, completeness, contradiction risk,
  privacy/safety concerns, and whether the source is primary evidence, context,
  or only a lead;
- `local_skill_inventory`: installed local skills and host capabilities that
  might help the route, recorded as candidate resources only. The inventory
  includes skill names, `SKILL.md` paths, short descriptions, likely capability
  fit, hard gates or safety notes, read depth, and deferred/private items. It
  must say that raw availability is not authority to invoke the skill;
- `coverage_map`: which parts of the user intent are supported, unsupported,
  ambiguous, or in conflict;
- `unread_or_deferred_materials`: sources not fully inspected yet, with a
  reason and the risk of proceeding without them.

The human-like reviewer must review this packet before the project manager uses
it. The reviewer must open or sample the actual materials behind the packet,
not only read the worker's packet. The reviewer asks whether the packet is
PM-ready: obvious sources are not missing, large tables or documents were
sampled or scoped honestly, summaries are specific rather than decorative,
contradictions and uncertainty are visible, and the packet would not mislead
route design. A reviewer block returns the route to material intake; PM
approval cannot override a current material sufficiency gap.

After reviewer approval, the project manager writes
`.flowpilot/runs/<run-id>/pm_material_understanding.json`. It records the PM's interpretation
of the materials, a source-claim matrix for important route assumptions, open
questions, material complexity (`simple`, `normal`, or `messy/raw`), and the
route consequence. If materials are `messy/raw`, material understanding becomes
formal work: the PM inserts discovery, cleanup, spreadsheet analysis, entity
modeling, research, validation, or reconciliation nodes before product design
or implementation nodes that depend on those materials.

When the PM cannot safely decide from reviewed materials, the gap becomes a
PM-owned research package rather than an informal note. Use
`.flowpilot/runs/<run-id>/research/<research-package-id>/research_package.json`
to name the decision, route impact, source/tool boundaries, worker assignment,
evidence standard, reviewer direct-check requirements, and stop conditions.
The package may request local repository inspection, user-provided materials,
web search, browser/site inspection, source reconciliation, FlowGuard modeling,
or a bounded experiment only when the host capability and hard gates allow it.
If web/browser capability is absent or private/paid/account access would be
needed, PM routes to local-source fallback, user clarification, manual research,
or block; FlowPilot must not claim external research was done.

Worker A, worker B, or another explicitly authorized non-controller role
executes the package and writes `worker_report.json` with raw source pointers,
commands or probes, negative findings, contradictions, and confidence
boundaries. The controller cannot execute the research package or turn missing
research into controller-origin evidence; PM must assign a non-controller
worker role or block for user/environment action. The human-like reviewer then
writes `reviewer_report.json` after directly checking original sources, search
results, local files, logs, screenshots, or experiment outputs. A reviewer
decision based only on the worker summary is invalid. If the reviewer blocks,
PM returns a concrete rework package to the worker, inserts a follow-up node,
asks the user, mutates the route, or blocks. PM may feed the result into
product-function architecture, node acceptance, or route design only after
reviewer sufficiency passes and PM records how the result was absorbed or how
the route changed.

## Product Function Architecture Gate

This gate sits after startup full grill-me, project-manager ratification, and
reviewer-approved material handoff, and before acceptance contract freeze,
route generation, capability routing, or implementation. It answers what the
product must functionally do before FlowPilot commits the route.

The project manager owns the synthesis and writes
`.flowpilot/runs/<run-id>/product_function_architecture.json`. The package is required to
contain:

- `high_standard_posture`: records that FlowPilot invocation means an
  important project, target grade is highest reasonably achievable, the PM is
  setting worker standards, and rough-demo completion is not acceptable;
- `highest_achievable_product_target`: the strongest feasible product target,
  the route or specialized skills likely needed, and the experience and proof
  quality bars before the PM can call the result high quality;
- `unacceptable_result_review`: concrete placeholder, fake, thin, misleading,
  unstable, incomplete, or low-quality results that must fail review and route
  to repair, discovery, redesign, user clarification, or block;
- `semantic_fidelity_policy`: user goals mapped to material support, allowed
  representations, forbidden downgrades, and the rule that material gaps require
  discovery, staged delivery with explicit gaps, user clarification, or block
  rather than silently redefining the user's requested product;
- `user_task_map`: user jobs, trigger conditions, desired outcomes, and
  failure/recovery expectations;
- `product_capability_map`: product capabilities needed to serve those tasks,
  including state, data, workflow, UI, automation, integration, and reporting
  needs when relevant;
- `feature_decisions`: each candidate feature marked `must`, `should`,
  `optional`, or `reject`, with a reason and acceptance impact;
- `display_rationale`: every visible label, control, card, status, alert,
  empty state, and persistent text mapped to a user decision, system state, or
  necessary evidence. Decorative or unexplained text is rejected;
- `missing_feature_review`: high-value missing functions found by the PM
  after comparing user tasks, current ideas, and likely failure modes;
- `negative_scope`: rejected features, rejected displays, deferrals, and
  explicit non-goals with reasons;
- `functional_acceptance_matrix`: inputs, outputs, state transitions,
  permissions, failure cases, manual checks, automated checks, and evidence
  paths required to prove the product behavior.

The product FlowGuard officer approves or blocks modelability and coverage:
whether the architecture can be represented as product-function models and
checked without hand-waving. The human-like reviewer separately challenges
usefulness, ambition, and completeness by comparing the PM architecture against
the user request, inspected materials, and expected workflow reality:
unnecessary features, missing high-value workflow support, confusing display
choices, weak default states, failure states, hidden downgrades from the user's
meaning, placeholder artifacts that would be embarrassing to show, and gaps
between what users need and what the product exposes.

The acceptance contract freezes only after this package exists and both
review slices are resolved. Later product-function models refine and verify
the architecture; they do not replace this pre-contract PM product design
gate.

## PM Child-Skill Selection Gate

This gate sits after the PM product-function architecture and capabilities
manifest, and before child-skill route-design discovery. It answers which
available skills actually serve the product, instead of letting the local
machine's installed skills drive the route.

The project manager owns
`.flowpilot/runs/<run-id>/pm_child_skill_selection.json`. The PM reads the
product capability map, frozen contract, capabilities manifest, and local skill
inventory, then classifies each relevant candidate skill as:

- `required`: the skill is needed for the route's product or delivery
  capability;
- `conditional`: the skill is used only when a named trigger is reached;
- `deferred`: the skill may become useful later, but should not enter the
  initial route;
- `rejected`: the skill exists locally but does not serve this product or would
  add unsafe or out-of-scope work.

The selection manifest records decision reasons, supported product
capabilities, trigger conditions, hard gates or user approval needed, files to
load, references deferred with reason, and negative selection for available but
unused skills. Child-skill gate discovery may read and map only PM-selected
skills. If a later node reveals a new required skill, the PM updates this
selection manifest before refining the child-skill gate manifest.

## Root Acceptance Contract And Standard Scenarios

After the product-function architecture is approved and before contract
freeze, the project manager writes
`.flowpilot/runs/<run-id>/root_acceptance_contract.json`. This artifact does
not try to pre-plan every later node's detailed tests. It records only
project-level hard requirements, high-risk requirements, required proof types,
report-only prohibitions, root requirements that later node plans must inherit,
and the route-local standard scenario pack selected for high-risk proof.

The standard scenario pack lives at
`.flowpilot/runs/<run-id>/standard_scenario_pack.json`. It compensates for
states that the live project may not naturally contain, such as multi-run
indexes, terminal-complete state, blocked gates, stale/conflicting frontier,
missing source artifacts, long localized text, absent host capabilities, and
legacy or old asset contamination. Scenario selection is PM-owned and
reviewable. A scenario pass is evidence for a requirement; it is not
completion by itself. Unused relevant scenarios require a reason.

Contract freeze is blocked until the root acceptance contract exists, the root
proof matrix is written, and required standard scenarios are selected. This is
intentionally narrower than final review: it defines root proof obligations
early without pretending to know every future node's implementation detail.

## Node Acceptance Plans

At each active node entry, before implementation work, child-skill execution,
child-skill execution, focused grill-me, quality package work, or node
checkpoint, FlowPilot must first refresh and visibly display the current-node
FlowPilot Route Sign from the active `flow.json` and `execution_frontier.json`.
Use `major_node_entry` for ordinary major route nodes, `parent_node_entry` for
parent/module entry, `leaf_node_entry` for leaf entry, and `pm_work_brief` when
the PM issues the current-node work brief. When Cockpit UI is closed or not
proven visible, paste the chat-ready Mermaid block before any tool call or file
edit for that node. Generated diagram files alone do not satisfy node entry.

After the visible route-sign gate passes and before the node acceptance plan is
approved, the project manager performs a current-node high-standard recheck.
This recheck compares the current major, parent/module, or leaf node against
`product_function_architecture.high_standard_posture`,
`highest_achievable_product_target`, `unacceptable_result_review`, and
`semantic_fidelity_policy`. It must answer:

- how this node advances the strongest feasible product target;
- what low-quality, placeholder, or locally convenient result this node could
  degrade into;
- whether current material, evidence, implementation, or UI constraints are
  causing semantic downgrade from the user's intended product;
- whether the PM decision is to raise the current node, add a sibling or repair
  node, insert discovery or validation work, ask the user, block, or proceed.

Only after that recheck does the project manager write a node acceptance plan:
`.flowpilot/runs/<run-id>/routes/<route-id>/nodes/<node-id>/node_acceptance_plan.json`.

The node plan maps inherited root high-risk requirements, node-local
obligations, concrete experiments/checks/fixtures/screenshots/model replays,
standard scenarios, required approvers, and recovery paths. This is where
later details become concrete. If a node plan exposes a material, mechanism,
test, or evidence gap, the PM either links an existing approved research
package or writes a new research package for worker execution and reviewer
source validation before dependent implementation proceeds. The PM may also
return the route to QA, insert repair work, mutate the route, ask the user, or
block. A node checkpoint cannot close while required node experiments or
research packages are unrun, failed, unreviewed, or untriaged.

## FlowPilot Skill Improvement Notes

FlowPilot keeps a live self-improvement notebook that is independent of the
current project's acceptance gates. It records problems with FlowPilot itself:
unclear protocol text, weak templates, hard-to-find code paths, missing review
fields, model/tooling friction, evidence-governance gaps, pause/restart gaps,
Cockpit display gaps, or other issues that would be useful when later
maintaining the FlowPilot root repository.

These notes do not block the current project and do not require the root
FlowPilot repository to be fixed inside the current run. If a small issue
affects the active project, compensate locally and continue the route. True
project blockers such as missing permissions, unavailable dependencies, or a
required user choice remain ordinary route blockers; they are not parked in the
skill-improvement report.

Initialize `.flowpilot/runs/<run-id>/flowpilot_skill_improvement_report.json`
at run start with status `live_updating`. At each node checkpoint, parent
review, child-skill closure, repair review, controlled pause, or other
meaningful boundary, ask the roles whether the run exposed a FlowPilot skill
issue. Append any observation to:
`.flowpilot/runs/<run-id>/flowpilot_skill_improvement_observations.jsonl`.
When no issue is observed, it is enough to record the node-level check as
complete; do not write long empty node reports.

Before terminal completion, the project manager rebuilds:
`.flowpilot/runs/<run-id>/flowpilot_skill_improvement_report.json`.
The report summarizes all observations, temporary compensations used in this
run, candidate FlowPilot root-repo files to inspect later, and PM notes for a
human maintainer. It must also be written when no obvious FlowPilot skill
improvement was observed. The report is a terminal artifact, not a gate that
demands fixing the reported issues before the current project completes.

## Defect And Evidence Governance

Every formal run initializes these ledgers before review, repair, pause, or
completion work:

- `.flowpilot/runs/<run-id>/defects/defect_ledger.json`
- `.flowpilot/runs/<run-id>/defects/defect_events.jsonl`
- `.flowpilot/runs/<run-id>/evidence/evidence_ledger.json`
- `.flowpilot/runs/<run-id>/evidence/evidence_events.jsonl`
- `.flowpilot/runs/<run-id>/generated_resource_ledger.json`
- `.flowpilot/runs/<run-id>/activity_stream.jsonl`

Any role that discovers a product defect, FlowPilot skill defect, process
defect, evidence defect, or tool/environment defect records a defect event
immediately. The project manager then triages severity, owner, route impact,
and close condition. The PM owns prioritization and closure, but cannot close a
blocker by assertion: the same role class that owns the blocked gate must
recheck the repaired artifact first.

Blocking defects use this state flow:

```text
open -> accepted/fixing -> fixed_pending_recheck -> closed
```

`open` blocker defects and `fixed_pending_recheck` defects block node closure,
route advancement, final ledger approval, and terminal completion. A repair
report alone changes the state only to `fixed_pending_recheck`; it is not a
pass. If a reviewer or officer blocks a gate, FlowPilot records the blocker in
the defect ledger before routing repair work.

Evidence credibility is tracked separately from defect status. Every material
evidence item that may close a gate is classified by status:
`valid`, `invalid`, `stale`, or `superseded`, and by source kind:
`live_project`, `fixture`, `synthetic`, `historical`, or `generated_concept`.
Fixture evidence may prove a capability, but the final report must disclose it
separately from live-project evidence. Invalid or stale evidence cannot close a
current gate, even when a newer screenshot or report replaces it.

Every generated concept, image, icon, screenshot, diagram, model output, or
similar resource is registered in the generated resource ledger immediately
when it is created. Each item records origin, path, owning node or gate, and
one disposition. `pending` is allowed only before closure. Terminal dispositions
are `consumed_by_implementation`, `included_in_final_output`, `qa_evidence`,
`flowguard_evidence`, `user_flow_diagram`, `superseded`, `quarantined`, or
`discarded_with_reason`. Terminal completion may only close after every
generated resource has one terminal disposition, a supporting reason, and no
unresolved resource count.

The activity stream is append-only. PM decisions, reviewer holds/releases and
reports, officer modeling actions, worker reports, route mutations, checkpoint
writes, heartbeat/manual-resume actions, and terminal closure events append
progress records as they happen. Cockpit and chat progress displays read from
this stream plus current route/frontier state, so users see progress without
manual refresh or ad hoc status reconstruction.

## Persistent Six-Agent Crew

Formal FlowPilot routes use a fixed crew for the life of the project:

- project manager: route owner and decision authority for material
  understanding, startup route design, product-function architecture
  synthesis, heartbeat resume, node work, review failures, route mutation, and
  completion closure;
- human-like reviewer: neutral observation, manual/product-style inspection,
  startup preflight reports, material sufficiency review, pre-contract product
  usefulness challenge, pass/block reports for ordinary review gates, and
  same-class recheck. For the startup gate, the reviewer is report-only and
  never opens the gate; the reviewer does not mutate the route directly;
- process FlowGuard officer: owns, authors, runs, interprets, and approves or
  blocks development-process models for startup, parent, leaf, repair,
  heartbeat, route mutation, and closure;
- product FlowGuard officer: owns, authors, runs, interprets, and approves or
  blocks the pre-contract product-function architecture modelability review
  and product-function models for the root product, parent scopes, leaf nodes,
  repairs, child-skill behavior, and final product closure;
- worker A and worker B: bounded sidecar workers for disjoint helper tasks.

Write `.flowpilot/runs/<run-id>/crew_ledger.json` and one role memory packet under
`.flowpilot/runs/<run-id>/crew_memory/` before formal route work. The ledger names each role,
agent id when available, status, latest report path, authority boundary,
memory path, recovery rule, and whether the role is active, replaced, idle, or
archived. The memory packet is the durable role brain: role charter, authority
boundary, frozen contract pointer, current route position, latest decisions,
open obligations, blockers, evidence paths, and "do not redo" notes.

Each crew record must separate identity into three fields:

- `role_key`: the stable programmatic role id used for authority checks,
  routing, memory filenames, and recovery;
- `display_name`: the short human-facing label shown in chat, user flow diagrams, and
  Cockpit UI;
- `agent_id`: the host/runtime handle used only for same-task continuation and
  diagnostic evidence.

Do not use raw `agent_id` as the primary UI label or as the authority key.
Nickname changes, regenerated subagent display names, or replacement agents do
not change the `role_key`.

Live subagent continuity is a startup target with an explicit fallback gate.
Role continuity is mandatory. If the current user request explicitly authorizes
background agents and the host/tool policy permits them, FlowPilot spawns fresh
live subagents for the fixed roles and may use bounded sidecar work. At new
formal startup, it must not resume, relabel, or count historical `agent_id`
values from prior routes or older tasks as current live-agent evidence. If
live subagents are unavailable, not authorized, or not supported by the host,
FlowPilot pauses and asks for the missing decision instead of silently
downgrading. A recorded user choice to continue without live subagents lets
FlowPilot mark affected roles as `replaced_from_memory`, `memory_recovered`,
or an equivalent memory-seeded status, load the latest role memory packets,
and continue under the same authority boundaries. A heartbeat or manual resume
may try to resume a stored `agent_id` only when it belongs to the same active
FlowPilot task-born cohort and the host supports that operation, but it must
not assume that a live subagent still has private chat context. If the old
same-task agent cannot be resumed, FlowPilot either starts a replacement live
agent after authorization or, after explicit fallback approval, replaces that
role with the same role charter plus the latest role memory packet. A
replacement role that starts from a generic prompt without its memory packet is
not recovered and cannot approve gates.

Heartbeat recovery and manual resume load the ledger and all required role
memory packets first, restore all six role identities and work memories, check
the memory schema/freshness, and write a crew rehydration report for project
manager, reviewer, process FlowGuard officer, product FlowGuard officer,
worker A, and worker B. Do not lazily rehydrate a role only when it is first
needed. Only after that report records which roles were resumed, replaced,
seeded, blocked, or unavailable does FlowPilot ask the project manager for a
completion-oriented runway from the current route position to project
completion. If any required role is missing and cannot be replaced from memory,
the current gate blocks rather than falling back to controller approval.

After any meaningful role output, update both the role report path and the
role memory packet before checkpoint or route advancement. Store compact
structured memory, not raw full chat transcripts. Full transcripts may be kept
only as optional evidence when useful; they are not the authoritative recovery
state.

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

The main assistant is the controller, not the project manager and not the
default implementation worker. It relays packets, records status, performs
read-only consistency checks needed to route the packet, and enforces hard
stops by returning conflicts to the correct role. It may provide product
context, source paths, logs, screenshots, and prior evidence to authorized
roles, but it must not create gate-closing implementation evidence, reviewer
passes, PM decisions, or officer model approvals for itself. If the project
manager's decision conflicts with a hard safety gate, blocking reviewer report,
FlowGuard counterexample, or user instruction, the controller feeds that
conflict back to the project manager for a corrected route decision instead of
silently overriding the route.

## Actor Authority Matrix

Formal FlowPilot gates carry actor authority, not only evidence paths. The
controller may not draft gate-closing evidence, run ordinary state-changing
tools, edit project files, or integrate worker results as completion evidence
unless a PM packet explicitly assigns that narrow administrative action and
the reviewer approves dispatch. Worker and officer outputs remain drafts until
the correct required role approves the gate. FlowGuard model gates are
different: the matching FlowGuard officer is the draft owner, execution owner,
interpreter, and required approver. Evidence existence is not approval.

Each meaningful gate in `.flowpilot/runs/<run-id>/execution_frontier.json` records:

- `gate_id`;
- `draft_owner`: who may create draft evidence;
- `execution_owner`: who performs the main work or inspection;
- `required_approver`: the only role whose approval can advance the gate;
- `forbidden_approvers`: roles whose approval attempt is invalid;
- `approval_status`: `draft`, `pending`, `approved`, `blocked`, or
  `superseded`;
- `approval_evidence_path`;
- `independent_validation_required: true`,
  `completion_report_only_allowed: false`, and
  `independent_validation_evidence_path` for every PM, reviewer, or officer
  approval;
- `blocked_reason` and `route_mutation_required` when blocked.

Authority rules:

- startup self-interrogation is PM-ratified before route/model gates advance;
- material intake is drafted by an authorized worker from a PM-authored
  `NODE_PACKET`, sufficiency-approved by the human-like reviewer, and
  interpreted by the project manager before product or route decisions;
- route advancement, heartbeat-resume runway selection, PM stop signals,
  repair strategy, route mutation, and completion require project-manager
  approval;
- development-process models must be authored, run, interpreted, and approved
  or blocked by the process FlowGuard officer;
- product-function models must be authored, run, interpreted, and approved or
  blocked by the product FlowGuard officer;
- human-like observation, pass/block inspection, and same-class recheck require
  the human-like reviewer;
- worker A and worker B can only produce bounded sidecar reports. They cannot
  approve gates, mutate routes, advance nodes, checkpoint, or complete a route;
- if a reviewer or FlowGuard officer blocks a gate, the project manager cannot
  ignore the block. The PM must run repair-strategy interrogation and select a
  route mutation, blocker, or corrected rework path.

The project manager owns reviewer timing. Before worker or officer work that
will later need review, the PM writes a review hold instruction naming the
expected gate and saying the reviewer waits. After authorized output,
verification, and anti-rough-finish evidence are ready, the PM writes a review
release order naming the gate, evidence paths, scope, and required
inspections. Reviewer work before that release is precheck only: it may note
risks for PM, but it cannot open, close, or block the gate.

If the required approver is unavailable, heartbeat recovery restores or
replaces that role before work continues. If restoration fails, the current
gate is blocked with evidence; it is not self-approved by the controller.

Approval records must not park unresolved risks as acceptable residuals. A
real risk triggers repair, route mutation, return to QA, request for more
evidence, correct-role waiver, or PM stop. A non-risk is renamed to a scope
note. A host/environment exception is allowed only with required-role approval
and proof that the frozen contract is not lowered.

## Universal Adversarial Approval Baseline

Every PM, reviewer, and FlowGuard officer approval is an independent
adversarial validation event. Completion reports, worker summaries, screenshots,
smoke logs, model-result snippets, and PM summaries are evidence pointers only.
They cannot be the approval basis by themselves.

Every approval record must include an `independent_validation` block, or a
separate role-approval record referenced from the gate. The block must record:

- `completion_report_only: false`;
- `report_inputs_used_as_pointers`: worker reports, completion reports,
  screenshots, smoke logs, or summaries consulted;
- `direct_sources_checked`: source files, material files, route/frontier/ledger
  files, screenshots, logs, model files, or state records personally opened by
  the approving role;
- `state_fields_checked`: exact `.flowpilot` fields, model state fields, or
  runtime state fields that were compared;
- `commands_or_probes_run`: manual operations, local commands, browser/UI
  probes, model checks, replay commands, or sampling probes run by the approving
  role;
- `adversarial_hypotheses_tested`: concrete ways the gate could be wrong, stale,
  incomplete, misleading, unreachable, incorrectly waived, or report-only;
- `concrete_evidence_references`: file paths, screenshot paths, command
  outputs, state fields, model labels, counterexample ids, or ledger entries
  that support the decision;
- `risk_or_blindspot_triage`: every risk-like item classified as `blocking`,
  `test_gap`, `evidence_gap`, `route_gap`, `resolved_issue`,
  `non_risk_scope_note`, `explicit_exception_with_required_approval`, or
  `false_positive`;
- `decision`: `approved`, `blocked`, `request_more_evidence`, `mutate_route`,
  or `pm_stop`.

Role-specific minimums:

- Project manager approvals must attack the decision surface, not rerun all
  worker labor. The PM checks the current route/frontier/ledger, stale and
  superseded evidence, unresolved counts, waiver authority, blocker handling,
  downstream consequences, and consistency with the frozen user goal before any
  route, repair, runway, startup, or completion approval.
- Human-like reviewer approvals must personally inspect the relevant artifact,
  behavior, source material, UI surface, log, output, or delivered product. The
  reviewer records neutral observation, probes failure and edge cases, and
  classifies findings before pass/block.
- FlowGuard officer approvals must personally own the model boundary, model
  files, command execution or explicitly valid reuse, state/edge counts,
  invariant results, missing labels, counterexample inspection, and model
  blindspots. A controller summary of a passing model is not an officer
  approval.

An approval without this independent validation evidence is `pending` or
`blocked`, even if all implementation or completion evidence exists. A later PM
approval cannot launder a report-only reviewer/officer approval; the stale gate
must be rechecked by the correct role.

## PM-Owned Child-Skill Gate Manifests

FlowPilot keeps child skills intact, but it cannot outsource route planning or
approval responsibility to a vague "use this skill" note. When a formal route
will likely invoke child skills, the project manager owns a child-skill gate
manifest before route modeling starts.

The manifest is built from the frozen contract, capability manifest, loaded
child-skill `SKILL.md` files, and relevant child-skill references. It records:

- source skill name and source files loaded;
- relevant references loaded, and skipped references with reasons;
- key child-skill stages and visible mini-route milestones;
- required checks, hard gates, completion standards, and loop-closure
  conditions;
- evidence required for each gate and where that evidence will be stored;
- `draft_owner`, `execution_owner`, `required_approver`,
  `forbidden_approvers`, approval status, and approval evidence path for each
  gate;
- whether the gate is process/conformance, product/function, human/visual/UX,
  route-inclusion, route-mutation, or parent-return scope.

Approver defaults:

- process/conformance child-skill gates: process FlowGuard officer;
- product/function behavior gates: product FlowGuard officer;
- visual, UX, interaction, real-use, output-quality, and strict human-review
  judgements: human-like reviewer;
- route inclusion, route mutation, parent return, and child-to-parent closure:
  project manager.

Worker agents may draft evidence, run ordinary tools, or implement the current
chunk only within their PM-authored packet and reviewer-approved dispatch. The
controller may only relay their evidence and cannot approve a child-skill gate.
If a child-skill gate has draft evidence but lacks its required approver, the
gate is pending or blocked. It is not complete.

The initial manifest feeds FlowGuard route modeling, the execution frontier,
and the PM completion runway. At node entry, the project manager refines the
same manifest for the current node context before implementation, sidecar
work, or child-skill execution starts. If the current node reveals new
child-skill stages, new standards, new checks, or changed complexity, the PM
classifies the change as local refinement, downstream node addition, route
mutation, or blocker, then asks the matching FlowGuard officer to recheck the
affected process/product model.

Parent return requires all current child-skill gates to show assigned-role
approval or explicit blocker/waiver evidence. A child skill's local checklist
pass is an input to this gate, not parent-node closure by itself.

## Strict Gate Obligation Review

Reviewer approval is a strict closure decision, not a place to park current
requirements for later. Before any human-like, child-skill, visual, or
completion reviewer can pass a gate, the reviewer must classify every finding
and caveat as one of:

- `current_gate_required`: required by the active gate's contract, child-skill
  standard, evidence checklist, visual/functional check, or acceptance matrix;
- `future_gate_required`: not required by the active gate and explicitly mapped
  to a named downstream gate or node in the execution frontier;
- `nonblocking_note`: useful context after all current-gate requirements are
  already satisfied.

A `current_gate_required` caveat cannot pass as "do later", "pass with
condition", "acceptable but check later", or "continue and remember". It is a
blocking review. The reviewer writes the block, the finding is grilled until it
names missing evidence, affected scope, severity, repair target, and recheck
condition, and the project manager must run repair-strategy interrogation
before choosing reset, sibling insertion, split children, subtree rebuild,
parent impact bubbling, or a real blocker. The route then invalidates affected
evidence and parent rollups, rewrites the frontier to the repair gate, reruns
process/product models for that repair, and requires same-inspector recheck
before parent closure.

The project manager cannot override this by accepting the caveat. PM approval
can close a gate only when the reviewer report shows all current-gate
obligations clear, any future-gate obligations are named in downstream route
state, and nonblocking notes are separated from blockers.

## Self-Interrogation

Self-interrogation must be visible to the user, not only hidden in JSON
evidence. At startup, expose the question set or a concise transcript in the
chat, then persist the structured evidence under `.flowpilot/runs/<run-id>/capabilities/`.

FlowPilot does not require changing the standalone `grill-me` skill. The
standalone skill remains a one-question-at-a-time user interview. Inside a
formal FlowPilot route, FlowPilot owns the formal invocation policy: it may use
the `grill-me` decision-tree discipline for visible self-questioning, and in
`full-auto`/autonomous contexts it may answer those questions itself when user
input is not required.

FlowPilot uses three self-interrogation depths. Use the smallest depth that
matches the boundary, and record the scope id so the same scope is not grilled
again unless evidence went stale, the route mutated, or impact bubbled up from
a changed child.

Full grill-me is for formal boundaries only: startup product-function
architecture and contract freeze, formal route mutation or standard expansion,
and completion review. Startup does not run separate post-freeze interviews
for improvement, richness, and validation; the startup full round drafts the
floor, seeds the improvement candidate pool, seeds the initial validation
direction, and feeds the PM product-function architecture before the contract
is frozen. A full round must first derive a task-specific layer matrix. Do not
hard-code exactly eight layers. The active layer count comes from the current
route, parent node, child-skill gates, risk surface, UI or backend scope,
delivery target, and known gaps. Each active layer must contain at least 100
questions. A 100-question total spread across many layers does not satisfy a
full FlowPilot gate.

Focused grill-me is for entry into a bounded scope: a phase, group, module,
leaf node, or child-skill boundary. It asks 20-40 questions by default and may
go up to 50 for complex module boundaries, risky child-skill use, or unclear
source-of-truth/state contracts. Focused rounds do not claim the full
100-per-layer formal gate; they identify local ambiguity, child-skill
requirements, validation needs, and route adjustments for the current scope.

Lightweight self-check is for continuation micro-steps and tiny reversible
decisions. It asks 5-10 targeted questions. It is a continuity guard, not a
formal grill-me gate.

The evidence must record:

- depth tier and scope id;
- layer names and why each one is active for full rounds;
- question count per layer and total question count;
- representative question/answer transcript or compact numbered batches;
- draft owner, required approver, approval status, and project-manager
  ratification evidence when this is a formal startup, route mutation, or
  completion gate;
- baseline risk families covered or explicitly waived with reasons;
- residual unknowns and route changes created by the interrogation.

Baseline risk families are not a fixed layer list. They are coverage checks
that must be addressed by the dynamic matrix or explicitly waived:

- acceptance floor and completion standard;
- functional capability and feature completeness;
- data, state, persistence, idempotency, and source of truth;
- implementation strategy, architecture, dependencies, and toolchain;
- UI/UX, interaction, visual quality, accessibility, and localization when
  there is a user-facing surface;
- validation, tests, screenshots, model checks, and manual QA;
- recovery, heartbeat, retries, route updates, and blocked exits;
- delivery/showcase quality, packaging, README/demo evidence, public boundary,
  and final presentation level.

A UI-heavy full round may not spend the whole round only on visuals. A
backend-heavy full round may not skip presentation and validation. Focused
node-level rounds emphasize the active node's domain, but they still record
which cross-layer impacts are unchanged, which require local checks, and which
require parent impact bubbling.

At major route nodes, rerun focused node-level grill-me before defining the
next chunk. "Raise the standard" is a fixed branch inside the quality package,
not a separate interview station repeated after every gate.

Improvement candidates are handled as typed route data:

- small improvement: fold into the current node;
- medium improvement: add to a later node;
- large improvement: trigger a route mutation and rerun FlowGuard checks;
- not doing: record the reason.

The only formal raise-standard trigger points are startup full grill-me,
parent/module review, node checkpoint review, and final completion review.

## User Flow Diagram / Temporary Chat Cockpit

FlowPilot has one user-facing realtime route sign for both chat and the
Cockpit UI. Startup asks the user which surface to use. If the user chose
Cockpit, open the Cockpit UI as soon as startup route/frontier state is ready
and use it as the primary display surface. If the user chose chat, or Cockpit
is unavailable, closed, or not proven visible, show the simplified English
Mermaid route sign at
startup, every new major `flow.json` route-node entry, parent/module or leaf
route-node entry, PM current-node work brief, legacy key node change, route
mutation, review or validation failure returns, completion review, or explicit
user request. Do not refresh or repost it on every heartbeat or internal
subnode/micro-step.

The route sign is a projection of existing canonical route/frontier state; it
is not a separate execution path and it must not invent a new route. The graph
should stay at 6-8 major FlowPilot stages or route nodes, highlight where the
current `active_route` and `active_node` sit, and show a visible
`returns for repair` edge whenever review, validation, or route mutation sends
the route backward. Chat and UI use the same generated Mermaid source at
`.flowpilot/runs/<run-id>/diagrams/user-flow-diagram.mmd`.

When Cockpit UI is not open, the chat Mermaid block is a hard gate. The
assistant must paste the chat-ready FlowPilot Route Sign before starting work
for the new major node, route mutation, repair return, completion review, or
user-requested progress explanation. A generated file, Markdown preview, or
display packet alone does not satisfy the gate, and `chat_displayed_in_chat`
may be marked true only after the exact Mermaid block appeared in the assistant
message.

Raw FlowGuard Mermaid exports are diagnostic state graphs. They are disabled by
default, generated only on explicit request, and must not replace the user flow
diagram in chat or UI.

The human-like reviewer must check the visible display, not just the generated
file. In closed-Cockpit cases the reviewer must verify that the Mermaid block
appeared in chat, that it names and highlights the current active route/node,
and that any repair/backtrack target is visible. Node advance, PM approval, and
completion are blocked until `.flowpilot/runs/<run-id>/diagrams/user-flow-diagram-review.json`
records a pass or equivalent reviewer evidence.

When `scripts/flowpilot_user_flow_diagram.py` is available in the project, use
it as the route-sign hook: generate chat Markdown with
`--markdown --trigger <trigger> --write` (`major_node_entry` is the preferred
trigger for ordinary route-node entry; `key_node_change` is a legacy alias),
paste that exact block into chat when required, then record the reviewer gate with
`--reviewer-check --mark-chat-displayed --write`. If the script is unavailable,
manually compose the same English Mermaid from the active route/frontier and
record equivalent reviewer evidence.

Each user flow diagram display must include:

- active route id, active node, status, and selected mode;
- the highlighted current stage in the 6-8 stage FlowPilot process;
- the current PM completion runway, with the next one to three jumps named in
  nearby text;
- checks that must pass before the next jump;
- fallback or blocked exits when they matter now;
- heartbeat or automation state;
- current acceptance delta: what is still missing relative to the frozen floor
  and any later raised standards.

Do not treat `.flowpilot/` files alone as sufficient user-facing progress
evidence. If the UI is not open, the user flow diagram, node jumps, planned
checks, route returns, and verification results must be visible in the
conversation.

When the Cockpit UI is available, keep the same hierarchy: user flow diagram
first, current node details and next checks second, archived/superseded route
history third.

## FlowGuard Role

FlowGuard is both process designer and checker. For new project-control flows,
capability routing, recovery branches, heartbeat behavior, and
stateful/idempotent target behavior:

- model the process before implementation;
- use counterexamples to revise the route before editing dependent code;
- rerun relevant checks after major route or capability changes;
- keep the model detailed enough to represent real gates, retries, recovery,
  heartbeat continuation, and completion conditions.

Do not treat FlowGuard as a final rubber stamp after the route is already
decided.

## Dual-Layer Product And Process Models

Every meaningful FlowPilot scope has two model gates:

- a development-process model: how FlowPilot should complete the scope, write
  evidence, recover, mutate the route, verify, and advance;
- a product-function model: how the product, workflow, UI, backend behavior,
  state, data, and user-visible result should behave.

This applies at root project scope, parent scope, leaf node scope, repair node
scope, child-skill capability scope, and final completion scope. The process
model alone is not enough: a route can be procedurally correct while the
delivered product is still visually weak, functionally thin, duplicated,
unclear, or unlike the concept target.

Before entering a parent node's children, FlowPilot reruns the current parent
development-process model and the parent product-function model. Before a leaf
node implements behavior, FlowPilot checks the leaf development-process model
and product-function model and derives tests or manual experiments from the
product model.

The matching FlowGuard officer owns the model end to end. The process
FlowGuard officer authors, runs, interprets, and approves or blocks
development-process models. The product FlowGuard officer authors, runs,
interprets, and approves or blocks product-function models. The controller may
provide context and receive the officer report, but it must not author or run
the FlowGuard model files on the officer's behalf. A model file, passing
command output, or controller summary is not approval unless the matching
officer personally checked the model boundary, ran the model or recorded valid
unchanged reuse, inspected counterexamples or missing-label output, cited model
files, state fields, commands, state/edge counts, and blindspots, and wrote an
approval or blocking report. A blocking officer report follows the same repair
route as inspection failure: issue grill, PM repair-strategy interrogation, PM
route decision, stale-evidence invalidation, frontier rewrite, repair model,
repair evidence, and same-class recheck.

FlowGuard model gates run as officer-owned asynchronous gates when live
background roles are available. The PM creates the modeling request, dispatches
it to the matching process/product officer, and records the output root under
`.flowpilot/runs/<run-id>/officer_runs/<request-id>/`. While the officer runs
the model, the controller may continue only non-dependent coordination:
read-only status reconciliation, dependency inventory routing, and relaying
already-authorized packets that cannot satisfy or bypass the pending model
gate. Implementation, route freeze, checkpoint closure, completion closure, or
any gate protected by that model remains blocked until the officer report is
approved.

Every officer report must contain execution provenance:
`model_author_role`, `model_runner_role`, `model_interpreter_role`,
`approved_by_role`, `commands_run_by_officer`, `model_files_written_by_officer`,
`input_snapshot_paths`, state/edge counts, invariant/missing-label results,
counterexamples inspected, PM risk-tier extraction, model-derived review
agenda, toolchain/model improvement suggestions, confidence boundary,
blindspots, and whether unchanged reuse was valid.
If the environment cannot let a live officer run tools directly, FlowPilot must
record the fallback explicitly as single-agent role continuity and cannot claim
parallel officer execution speedup. Controller command output can be a
pointer, but not `commands_run_by_officer`.

## PM-Initiated FlowGuard Modeling

FlowGuard is also a PM-invoked modeling laboratory. When the project manager
must choose a route, repair strategy, feature direction, product behavior, file
format hypothesis, external protocol interpretation, or unknown object model
and cannot choose confidently from existing evidence, the PM may create a
structured FlowGuard modeling request instead of guessing.

The PM may assign the request to:

- the process FlowGuard officer, for "how should FlowPilot do this?" questions:
  route alternatives, node splits, rollback paths, stuck paths, verification
  order, or whether a current node is too large;
- the product FlowGuard officer, for "what is the target itself?" questions:
  product functions, target software behavior, file or protocol structures,
  UI/user states, data/state transitions, missing features, or experiments
  needed to learn the object;
- both officers, when a route decision depends on target-object uncertainty.

A PM modeling request is valid only when it names the decision to be made, the
uncertainty, known evidence sources, candidate options or an explicit request
to generate candidates, assigned officer scope, answer shape needed for PM
action, officer output root, and the controller's non-dependent coordination
boundary while the request is pending. Use `flowguard_modeling_request.template.json`
for persistent evidence. The assigned officer first performs a modelability
check. If the request lacks evidence, the route gains an evidence-collection
node. If the request is too broad, the route gains split modeling requests. Only
a modelable request may produce a decision report.

The officer report must include coverage, blindspots, failure paths,
PM-facing risk tiers, model-derived review agenda, toolchain or model
improvement suggestions, human walkthrough recommendations, recommendation,
confidence, next smallest executable action, and any route mutation candidate.
Use `flowguard_modeling_report.template.json`. The report must not claim
absolute "no risk"; it states what the model did and did not prove, then gives
the PM decision options. The PM then synthesizes the report and records one of:
continue current route, mutate the route, add evidence work, split the
request, repair before advance, or block with a concrete reason. An officer
report is advisory; PM synthesis is the route decision.

FlowGuard does not judge aesthetics directly. It enforces the route
consequences of inspection results: if the AI/human-like inspector reports a
blocking defect, FlowPilot cannot complete, checkpoint, or silently continue.
It must turn that defect into a specific issue, mutate the route, create a
repair node, check the repair's process and product models, write repair
evidence, and recheck with the same inspector class.

For UI concepts, app icons, product-facing visual assets, and rendered UI
screenshots, the human-like reviewer must also write an aesthetic judgement
after the neutral observation and before the pass/block decision. Record
`aesthetic_verdict` as `pass`, `weak`, or `fail`, with concrete reasons tied
to the shared visual direction, product audience, concept target, and visible
evidence. Reasons may cover palette, typography, spacing rhythm, material
treatment, icon or asset style, hierarchy, density, composition, polish,
distinctiveness, and whether the result looks template-like, cheap,
incoherent, cluttered, or disconnected from the product. `fail` blocks
implementation, checkpoint, package polish, and completion until the same
surface is repaired or regenerated and re-reviewed. `weak` can pass only with
a recorded reason why it is acceptable for the current gate or with a specific
follow-up repair target.

## Human-Like Inspection Loop

After implementation and declared verification, FlowPilot runs human-like
inspection before checkpoint or completion closure. The inspector receives the
frozen contract, current route, product-function model, relevant child-skill
evidence, screenshots/logs/output, and parent acceptance context. It must do
real product-style inspection: operate the app or workflow when the gate is
interactive, compare concept to rendered output for UI work, inspect functional
behavior, look for duplicate or conflicting controls, check
localization/content coverage, and ask whether the result is a complete product
rather than a running artifact. Worker screenshots, automated interaction logs,
or PM summaries are pointers only. For UI, browser, desktop, click, hover,
visual, or localization gates, a reviewer pass is invalid unless the
human-like reviewer personally performs the walkthrough or records a concrete
blocker explaining why the surface cannot be operated.

UI interaction review must record the reviewer-owned walkthrough: surfaces
opened, viewport/window sizes, clicks or keyboard paths exercised, tabs and
settings visited, language/support/tray or other route-specific controls
checked, unreachable controls, text overlap or clipping, layout density,
excessive whitespace, crowded areas, hierarchy/readability, and responsive fit.
The report must also include concrete repair or enhancement suggestions, or
state that no current-gate design repair is needed. A report that only says a
worker captured screenshots or ran an interaction smoke test is
`worker_report_only` evidence and cannot approve a human-review gate.

Before judgement, every human-like inspection writes a neutral observation
record. The inspector first describes what the artifact, screenshot, output, or
exercised feature actually appears to be, without deciding pass/fail yet. For
UI and visual gates, this includes visible layout, window/screen artifacts,
taskbar or browser chrome, old-route names, interaction affordances, and
whether the image looks like an independent concept, a screenshot, or a variant
of existing evidence. For functional gates, this includes what was operated,
what response occurred, and which required behavior was not observable. The
final inspection decision must reference this observation; if the observation
contradicts the claimed evidence type, the gate fails or requests more
evidence.

Inspectors may pass, request more evidence, produce non-blocking notes, or
raise blocking issues. A blocking issue must be grilled until it is repairable:
evidence, expected result, actual result, severity, affected node, affected
parent rollups, affected product model, repair target, and recheck condition.
Vague "not good enough" feedback is not a closed issue.

When inspection fails:

```text
inspection failure -> grill issue -> grill PM repair strategy
-> PM repair route decision -> route mutation -> repair node
-> repair process model -> repair product model -> repair evidence
-> same-inspector recheck -> resume original route or parent rollup
```

The failure decision is strict. FlowPilot must not continue with "accepted with
constraints" when the review blocks the gate. It immediately marks the current
child or subnode as `failed`, `stale`, or `superseded`, invalidates affected
evidence and parent rollups, then grills the project manager before any route
mutation is written. The PM repair-strategy interrogation must ask which level
failed, whether the original child can cover the failure, whether to reset the
child, insert an adjacent repair/regeneration sibling such as
`concept-regeneration-v2`, split responsibilities into several child nodes,
rebuild the child subtree, or bubble impact to a parent. It also records stale
evidence, repair target, execution plan, and same-inspector recheck condition.
Only after that interrogation may the project manager record the repair route
decision, increment the route version, rewrite the execution frontier, and
move the next executable gate to a repair target. Each reset or new child
re-enters the normal loop: focused interrogation, development-process model,
product-function model, execution, neutral observation, inspection, and
parent/composite recheck.

Backward inspection also runs at every parent/composite scope, not only at
final completion. Do not infer "important" parent nodes from high-risk,
integration, feature, or downstream-dependency labels. The trigger is purely
structural: every effective route node with children must run a local parent
backward replay before that parent closes. A parent node does not close merely
because each child passed locally. After all children under the parent pass
their local checks, FlowPilot replays child evidence against the parent
product-function model, runs a human-like backward review from the
parent-level delivered result back through the child rollup, and requires a PM
segment decision. The same rule repeats upward: child nodes close into their
immediate parent, parents close into larger phase nodes, and phases close into
the root route.

If a parent backward replay fails, FlowPilot must classify the structural
impact before continuing:

- affected existing child: invalidate that child and the affected parent
  rollups, jump back to that child node, rerun its process/product models,
  implementation, evidence, local inspection, and then rerun the parent
  backward review;
- missing adjacent sibling: insert a new sibling child node near the
  insufficient child, check the new node's process/product models, execute and
  inspect it, then rerun the parent backward review;
- subtree mismatch: invalidate the child subtree, rerun the parent model,
  regenerate or reshape the children, execute the affected subtree, then rerun
  the parent backward review.

These are route mutations, not local notes. They update the route version,
execution frontier, visible plan projection, affected evidence status, and
parent impact bubbling. A parent backward replay failure cannot be waived by
saying that all children passed individually. Before writing the structural
route mutation, grill the project manager on the repair strategy: affected
child versus missing sibling versus subtree rebuild, whether impact bubbles to
the parent, which evidence becomes stale, what the next executable target is,
and how the same parent review will be rerun.

## Recursive Route Tree Planning

The first route is not an unverified plan. FlowPilot first generates a
candidate route tree, then uses FlowGuard to simulate the root route before
freezing the checked candidate as `route v1`.

The execution unit is hierarchical:

```text
route -> phase -> group -> leaf node -> continuation micro-step
```

Before entering a parent node's children, FlowPilot must reload the current
child subtree, emit the visible subtree map, run focused parent-scope
grill-me, have the process FlowGuard officer author/run/interpret the parent
process model, have the product FlowGuard officer author/run/interpret the
parent product-function model, and only then enter the next child. This applies
at route, phase, and group levels. The existing child nodes are model input,
not a promise to execute them blindly.

If the parent model finds that the child subtree is wrong, missing work, too
coarse, or stale, route the change through a formal route mutation node. Create
a new route version, recheck the changed subtree, write a transition record,
and rerun the same parent review before entering children.

If a product-function model or human-like inspection finds that the planned
product behavior is wrong, incomplete, visually incoherent, or no longer
matches the acceptance floor, treat that as the same class of route mutation:
create a repair node, invalidate affected rollups/evidence, recheck the route,
and resume only after same-inspector recheck passes.

Use local re-simulation plus impact bubbling:

```text
changed node -> direct parent re-simulates -> impact stops or bubbles upward
```

Only rerun the whole route tree when the impact reaches the root or when the
acceptance floor, delivery target, source of truth, major implementation
strategy, or cross-phase dependency changes.

Continuation starts with a host capability probe. If the host can create real
wakeups or automations, heartbeat is the transition mechanism, but route
position is persisted outside the heartbeat prompt. If the host cannot create
real wakeups, FlowPilot records `manual-resume` mode and uses the same
`.flowpilot/` state, frontier, crew ledger, role memory packets, PM runway, and
checkpoint evidence when a user or agent returns manually. Unsupported hosts
must not create heartbeat automation and must not claim unattended recovery.

Every automated heartbeat must resolve `.flowpilot/current.json`, then load the
active run's `state.json`, active `flow.json`, `execution_frontier.json`,
`crew_ledger.json`, `crew_memory/`, latest heartbeat/manual-resume evidence,
and the packet ledger. `.flowpilot/current.json` to
`.flowpilot/runs/<run-id>/` is authoritative; top-level legacy state is import
or quarantine evidence only and must not override the active run. The heartbeat
prompt is a stable launcher, not a route-specific work prompt, and ordinary
route changes must not rewrite it.

After loading state, heartbeat/manual resume rehydrates the fixed six-agent
crew: restore every role identity and work memory, resume known agent ids when
possible, and if live agents are unavailable, record the block and ask before
replacing roles from memory packets. Only after live startup or explicit
fallback authorization is recorded may it write the crew rehydration report.
Then the controller asks the project manager for the current `PM_DECISION`
from the persisted frontier and packet ledger. The PM decision must include
`controller_reminder`; if it is missing, the controller asks PM for a corrected
decision and does not dispatch work. If PM issues or reissues a `NODE_PACKET`,
the controller sends it to the human-like reviewer for dispatch approval with
`ROLE_REMINDER` before any worker receives it. If a worker result is already
persisted, the controller sends that `NODE_RESULT` to the reviewer; it does
not re-execute or finish the worker's packet. If packet holder, worker
identity, reviewer dispatch, or worker-result state is ambiguous, the
controller blocks and asks PM for recovery, reissue, reassignment, quarantine,
or route mutation rather than guessing the next worker action.

The PM runway must include the current gate, downstream steps, role approvals,
hard-stop conditions, checkpoint cadence, any PM stop signal, and the current
packet recovery state. The controller immediately replaces the current visible
Codex plan projection with that runway and continues the internal packet loop
until the PM stop signal, a hard gate, a blocker, route mutation, or real
environment/tool limit stops progress. If the current node is unfinished after
an interruption, the next automated heartbeat or manual resume resumes that
same node under PM/reviewer packet control. It may not advance to the next
node until validation and evidence for the current node are written.
Concretely, `unfinished_current_node: true` or
`current_node_completion.advance_allowed: false` means the continuation turn
must keep working on `active_node` and must ignore `next_node` as an execution
target.
`next_node` is only a planned jump after the completion guard is satisfied.
The PM runway must include the persisted `current_subnode`, `next_gate`, and
packet recovery state for that unfinished node, but it must not stop at that
single gate. The automated heartbeat or manual-resume turn must continue the
packet loop when it is executable: PM decision -> reviewer dispatch -> worker
packet or worker result -> reviewer result -> PM decision. It may not end by
only writing a future-facing decision such as "continue to icon generation" or
"next do X" while the packet loop remains executable. Continuation evidence
must name the host kind (`codex_heartbeat_automation`,
`windows_scheduled_task`, `manual_resume`, or `blocked_unsupported`), the exact
host evidence source, the PM runway, the selected gate, packet recovery state,
crew rehydration report, actions attempted, results, checkpoint writes, and
the updated completion guard.

## Controlled Nonterminal Stop Notice

Every controlled stop must classify the route as complete or not complete.
This applies in automated heartbeat mode and in `manual-resume` mode.

If the route is complete, FlowPilot emits a terminal completion notice and does
not ask the user to continue:

```text
FlowPilot task complete.
```

If the route is not complete and the agent still has a chance to respond, it
must write a resume notice into `.flowpilot/` state/frontier evidence and show
a concise chat notice. Automated continuation may mention the heartbeat;
manual-resume mode must not imply that unattended recovery exists.

Automated continuation notice:

```text
FlowPilot is not complete yet, and the checkpoint has been saved. You can wait
for the configured heartbeat to wake this thread, or type "continue FlowPilot"
to resume manually.
```

Manual-resume notice:

```text
FlowPilot is not complete yet, and the checkpoint has been saved. This host
does not support heartbeat or scheduled wakeups; type "continue FlowPilot" in
this thread to resume manually.
```

If the stop is caused by a blocker or hard gate, the notice must name the
blocking condition and the next required user or environment action before the
resume sentence. An abrupt host kill, process crash, or forced stop that gives
the agent no final response opportunity cannot guarantee this chat notice, so
FlowPilot should keep the persisted resume packet current at each checkpoint
and before risky/long operations.

The visible plan projection is a host-facing execution control, not just a
JSON note. When a native plan tool exists, the controller must call it after
each PM runway decision and after any route mutation that changes the runway.
The plan must contain the current executable gate plus downstream runway items
toward completion. Do not leave the native plan as a one-step list, and do not
stop just because the first item is complete while the PM runway still has
executable downstream work. If the host has no native plan tool, record the
fallback projection method in `.flowpilot/runs/<run-id>/execution_frontier.json` and show the
runway in chat, but do not claim that the native Codex plan was synced.

When the route mutates, update and recheck the route, rewrite the execution
frontier, then sync the visible Codex plan. Do not rewrite the stable heartbeat
launcher unless the host automation itself is missing or broken.

Automated continuation is heartbeat-only lifecycle state. The project/route
heartbeat cadence is fixed at one minute: create route heartbeats with
`rrule: FREQ=MINUTELY;INTERVAL=1` and record
`route_heartbeat_interval_minutes: 1` plus the rrule in route/frontier
evidence. Whenever FlowPilot creates or updates real heartbeat continuation
for a formal long-running route, it records the heartbeat id, cadence, active
state, host kind, exact official host automation source, and fallback. If the
heartbeat cannot be created or verified, roll back to `manual-resume` before
route execution or record a concrete blocker.

Pause, restart, and terminal closure use one unified lifecycle reconciliation
gate. Before claiming any of those states, FlowPilot scans Codex app heartbeat
automations, `.flowpilot/current.json`, `.flowpilot/runs/<run-id>/state.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`, and latest heartbeat or
manual-resume evidence. Use `scripts/flowpilot_lifecycle.py` as the read-only
inventory helper and then perform required Codex automation changes through
the official Codex app automation interface.

For any controlled nonterminal pause, FlowPilot also writes
`.flowpilot/runs/<run-id>/pause_snapshot.json`. The snapshot names the current
route/node/gate, open blockers, fixed-pending-recheck defects, invalid or
fixture-only evidence caveats, heartbeat and agent lifecycle state, artifacts
safe to delete, lessons to preserve, and artifacts that must not be reused in a
fresh run. A pause without this snapshot is not reconciled.

At terminal closure, write terminal/inactive route state, write the
stopped/inactive lifecycle state back to `.flowpilot/runs/<run-id>/state.json`,
`.flowpilot/runs/<run-id>/execution_frontier.json`, and lifecycle evidence,
then stop or delete the heartbeat automation. Manual-resume routes record that
no heartbeat automation exists to stop. This is a final writeback gate, not a
requirement to poll additional supervisors during ordinary route progress.
Ordinary route progress, checkpoint writes, node changes, plan syncs, and user
flow diagram refreshes must not recreate, re-register, start, restart, or
re-enable heartbeat automation unless they are explicitly in the lifecycle
setup/repair gate.

## Quality Package

FlowPilot keeps the main route simple by reusing one quality package instead of
adding separate stations for feature richness, standard raises, child-skill
visibility, and validation.

At each parent/module or leaf-node entry, use this sequence:

```text
enter parent or node -> refresh and visibly display FlowPilot Route Sign
-> focused grill-me -> quality package
-> FlowGuard or route check -> execute chunk -> verify -> checkpoint
```

The quality package must answer and record:

- is the current scope too thin;
- is there a low-risk, high-value improvement;
- are the invoked child-skill key milestones visible as a mini-route;
- is the validation matrix strong enough for this node;
- is there a rough-finish risk before checkpoint.

Do not keep asking the same "can we improve this" question at multiple nearby
gates. Record candidates once, classify them as small, medium, large, or not
doing, and route them accordingly. A medium or large improvement changes the
route and must be rechecked; a small improvement may be folded into the
current node; a rejected candidate needs a reason.

Before each checkpoint, run an anti-rough-finish review. If the verified chunk
is still thin, missing states, weakly evidenced, or visibly rushed, do bounded
rework before writing the checkpoint. Do not treat "verification command
passed" as sufficient when the node is obviously underbuilt.

After anti-rough-finish review, run the human-like inspection loop for the
current node. A checkpoint is allowed only when the node has product-model
context, manual or product-style inspection evidence, and an explicit pass or
closed repair issue. Technical verification, screenshots, or build success are
inputs to inspection, not substitutes for inspection.

Before writing the checkpoint, record the lightweight FlowPilot skill
improvement check for the node. Append an observation only when a role noticed
a FlowPilot protocol, template, model, script, review-standard, or code-pointer
issue. This check never asks the current project to stop while the root
FlowPilot skill is repaired.

## `.flowpilot/` Source Of Truth

Canonical state is machine-readable:

- `state.json`: current route, node, status, heartbeat, checkpoint, next action.
- `execution_frontier.json`: route version, active node, current mainline, next
  jump, fallback, current-node completion guard, latest PM completion runway,
  checks before advance, and visible Codex plan projection. For terminal
  states it also records the final heartbeat lifecycle snapshot so
  stale `active: true` values cannot survive after closure.
- `startup_review/latest.json`: the human-like reviewer's factual startup
  report. It must cite direct fact checks rather than worker assertions.
- `startup_pm_gate/latest.json`: the project manager's startup decision. This
  is the only startup opening record that may set
  `work_beyond_startup_allowed: true`.
- `human_reviews/*.json`: reviewer-owned inspection reports for node,
  child-skill, visual, interaction, parent, and final review gates. UI and
  interaction reports must include `reviewer_personal_walkthrough_done: true`,
  `worker_report_only: false`, reachability checks, layout/overlap/density
  checks, aesthetic verdicts where visual quality matters, and reviewer design
  recommendations before they can close a gate.
- `mode.json`: selected run mode and hard-gate policy.
- `contract.md`: frozen acceptance contract and explicit later approvals.
- `capabilities.json`: required and conditional capability gates.
- `routes/<route-id>/flow.json`: route nodes, transitions, gates, invariants.
- `routes/<route-id>/flow.md`: human-readable summary derived from `flow.json`.
- `routes/<route-id>/nodes/<node-id>/node.json`: chunk intent and verification.
- `heartbeats/*.json`: current position, decision, lifecycle state, and next
  chunk.
- scheduled continuation record: host wakeup/automation probe result,
  automated continuation evidence when supported, or `manual-resume` fallback
  evidence when unsupported.
- `checkpoints/*.json`: verified milestone evidence.
- `inspections/*.json` or node-local inspection evidence: human-like review
  context, experiments, findings, blocking issues, repair targets, and
  same-inspector recheck results.
- `research/<research-package-id>/research_package.json`: PM-owned package for
  material, mechanism, source, validation, reconciliation, or experiment gaps.
- `research/<research-package-id>/worker_report.json`: worker search,
  inspection, reconciliation, or experiment output with raw evidence pointers
  and confidence boundaries.
- `research/<research-package-id>/reviewer_report.json`: reviewer-owned direct
  source or experiment-output check before PM may use the research result.
- `experiments/*/experiment.json`: bounded experiment evidence.
- `flowpilot_skill_improvement_observations.jsonl`: append-only notes about
  FlowPilot skill issues or improvement opportunities observed during nodes,
  reviews, repairs, or terminal closure. These notes are for later manual
  FlowPilot root-repo maintenance and are not current-project blockers.
- `flowpilot_skill_improvement_report.json`: PM-owned terminal summary of the
  observation log. It is written before completion even when it says no obvious
  skill improvement was observed.
- `task-models/`: task-local development-process and product-function
  FlowGuard models when the route or delivered behavior needs model-first
  validation.

Markdown files are review views. JSON and executable model files are the source
of truth.

## Real Heartbeat Continuation

Heartbeat JSON is not enough to claim unattended continuation for a formal
long-horizon FlowPilot route. Before creating heartbeat automation, probe the
host environment for real reminders, monitors, wakeups, cron jobs, or
automation tools. Record the probe result in
`.flowpilot/heartbeats/` or equivalent route evidence.

If the host supports real continuation, create or update the automated
continuation before long-running work starts: stable one-minute heartbeat
launcher. Record the continuation ID, cadence, next wakeup condition, heartbeat
evidence, and fallback.

If the host does not support real continuation, record `manual-resume` mode and
do not create heartbeat automation. The route
continues to use `.flowpilot/` state, PM runways, checkpoints, FlowGuard
models, and evidence, but it must not claim unattended recovery.

In Codex Desktop, use the available automation/update capability when the user
requests heartbeat continuation or the formal route depends on long-running
autopilot. Prefer a cadence that checks after the previous chunk is no longer
running, such as a short wakeup interval when supported by the host. Do not
interrupt active work only to satisfy a heartbeat tick.

The heartbeat automation should be a stable launcher when it exists: it tells
FlowPilot to load the current `.flowpilot` state, active route, execution
frontier, lifecycle evidence, crew ledger, role memory packets, and latest
heartbeat or manual-resume evidence. It then rehydrates the six-agent crew by
resuming or replacing roles from memory and asks the project manager for the
latest completion-oriented runway. Route changes,
next-node changes, PM runway changes, and Codex plan changes are written to
persisted files, not embedded into a freshly rewritten heartbeat prompt.
Checkpoints and node transitions preserve the recorded lifecycle state instead
of re-entering heartbeat setup.

Stable heartbeat or manual resume does not mean passive status reporting. When
the loaded frontier says the current node is unfinished, the first work unit is
the project-manager-selected persisted `current_subnode` or `next_gate`, not the
future `next_node`, but the PM decision must still be a long runway toward
completion. The heartbeat or manual-resume turn must restore/load the crew,
ask the project manager for that runway, sync it into the visible plan, verify
the selected gate's authority record, execute at least one bounded gate when
possible, then keep advancing through downstream runway steps until a PM stop
signal, hard gate, blocker, route mutation, or real environment/tool limit
stops progress. If a gate requires a role-specific approver, the controller
cannot advance from its own draft; it must obtain the required role's approval
or record a blocker. Writing only "continue to X" is invalid no-progress
continuation evidence.

## Capability Routing

Specialized skills are invoked through explicit gates and evidence files.

Child-skill fidelity is a hard gate, not a courtesy prompt. Whenever FlowPilot
invokes another skill through `source_skill`, it must preserve that skill's own
workflow instead of collapsing it into a weaker FlowPilot shortcut.

The source skill name and source files are part of the gate. A similar concept,
ad hoc local workflow, prototype, screenshot, or summary cannot satisfy the
gate unless the source skill itself permits that substitute or an explicit
waiver/blocker is recorded. For general-purpose child skills whose standalone
behavior should remain lightweight, such as `grill-me`, FlowPilot owns the
formal invocation policy and must record that policy in the route evidence.

Before route modeling and again before using a child skill in a node:

- have the project manager discover likely invoked child skills from the
  PM child-skill selection manifest, not from raw local skill availability;
- read the child skill's `SKILL.md`;
- read only the relevant reference files that the child skill requires for the
  current task, or record why a referenced file is irrelevant or unavailable;
- write or refine the PM-owned child-skill gate manifest;
- map the child skill's required workflow steps, hard gates, and completion
  standard into the active route gates;
- map any FlowPilot-owned formal invocation policy that applies to that skill;
- project the child skill into a visible mini-route of key milestones, without
  copying the child skill's detailed prompt rules into FlowPilot;
- assign each child-skill gate a required approver and forbidden approvers;
- write an evidence checklist that names the source skill, loaded files,
  mapped steps, required outputs, skipped steps with reasons, and completion
  evidence paths;
- build or update a child-skill conformance model when the child skill
  materially affects the active node;
- define domain-quality checks that compare the child skill's output to the
  parent node's goal, not only to the existence of evidence;
- stop or update the route when the child skill conflicts with the frozen
  contract, a hard gate, or FlowPilot's completion floor.

During and after child-skill work:

- do every required child-skill step unless there is an explicit recorded
  waiver, blocker, or task-irrelevant reason;
- do not replace the child skill's process with a one-sentence summary such as
  "use UI skill" or "use FlowGuard";
- collect evidence for each mapped child-skill step;
- audit that evidence against the actual output;
- run a domain-quality review against the parent route node;
- if evidence is missing, stale, mismatched, or low quality, return to the
  child-skill loop rather than advancing the parent node;
- close the child-skill iteration loop before parent-node completion;
- do not mark the capability complete until the source skill's own completion
  standard is met, the evidence checklist is synced, and every current
  child-skill gate has the assigned role approval or a recorded blocker/waiver.

This gate has three layers: prompt protocol, persisted evidence, and
FlowGuard-checkable state. A claim that a child skill was used is insufficient
without evidence that its own instructions were followed carefully.

The generic child-skill conformance loop is:

```text
select skill -> load instructions -> map workflow -> write evidence checklist
-> assign required approvers -> show child-skill mini-route -> model/check conformance
-> execute child workflow -> collect evidence -> audit evidence/output match
-> domain-quality review -> strict obligation classification
-> iteration closure -> assigned role approvals -> verify child completion
-> resume parent node
```

For UI child skills, expose only key milestones such as:

```text
concept target -> implementation -> screenshot QA -> divergence review
-> iteration closure
```

Do not expand every sentence of the UI skill into FlowPilot nodes. FlowPilot
shows the child-skill rhythm and evidence gates; the UI skill owns the visual
execution details.

If the child-skill reviewer finds a current-gate caveat, the parent node does
not resume. The caveat becomes a blocking route event and follows strict
gate-obligation repair.

## Prompt Layer Boundary

FlowPilot owns orchestration: route state, gates, evidence, ordering,
verification, recovery, heartbeat, and completion closure.

Child skills own domain execution details. FlowPilot should not duplicate or
override detailed UI, visual design, screenshot, icon, FlowGuard modeling, or
implementation-style prompts that live in the invoked child skill. When a
domain rule is needed, route to the right child skill through the fidelity gate
and persist the evidence that the child skill's own completion standard was
met.

When FlowPilot records a domain capability, prefer evidence names and
completion checks over detailed prompt text. If the source skill changes, the
child skill is authoritative for its domain unless it conflicts with the
frozen contract or a FlowPilot hard gate.

Required early gate:

- showcase-grade floor before contract freeze;
- visible self-interrogation before contract freeze;
- Material Intake Packet, reviewer material-sufficiency approval, and PM
  material understanding memo before product-function architecture, contract
  freeze, route generation, or capability routing;
- PM-owned product-function architecture before contract freeze, including
  feature decisions, display rationale, missing-feature review, negative
  scope, product officer modelability approval, and reviewer usefulness
  challenge;
- user flow diagram before route execution and at each major node;
- host continuation capability probe before route execution;
- if the host supports real wakeups, the automated continuation before route
  execution: stable one-minute route heartbeat schedule
  (`FREQ=MINUTELY;INTERVAL=1`) with lifecycle evidence;
- if the host does not support real wakeups, `manual-resume` evidence before
  route execution and no heartbeat automation created;
- PM-owned startup opening from a clean factual reviewer report before child
  skills, imagegen, implementation, formal route chunks, or completion work;
- FlowGuard process design before route execution.
- candidate route-tree generation and root FlowGuard freeze before `route v1`;
- strict gate-obligation review model before reviewer-closable gates advance;
- parent-subtree FlowGuard review before entering child nodes.

Conditional UI gates:

- detect that the route has a user-facing UI or visual-delivery surface;
- invoke `autonomous-concept-ui-redesign` through the child-skill fidelity gate
  for UI redesign, UI implementation, UI polish, layout, responsiveness,
  accessibility, visual iteration, and UI QA routes. The experimental
  orchestrator owns the concept-led front half internally, then composes
  `frontend-design` implementation, `design-iterator` refinement,
  `design-implementation-reviewer` deviation review, and geometry/screenshot
  QA. Do not require the old `concept-led-ui-redesign` skill;
- when FlowPilot invokes the autonomous UI child skill and the user has not set
  a different iteration count, record the UI refinement budget as 10
  `design-iterator` rounds by default with a maximum of 20 rounds;
- before generated concept targets, record the UI child skill's shared visual
  direction source and reuse that direction for concept image, implementation,
  app icon/assets, and QA;
- before UI implementation, record the child skill's concept-target decision
  and show the chosen target, authoritative reference, or explicit waiver;
- when the concept target is generated, record a separate authenticity
  decision: a file produced by `imagegen` is not sufficient if the content is
  an existing screenshot, existing-image variant, desktop capture,
  taskbar-inclusive capture, old route UI, or prior failed UI evidence with
  cosmetic changes. The concept must be an independent design target. If
  authenticity fails, mutate the route back to a clean concept regeneration
  child gate; do not accept it with implementation constraints;
- before the authenticity decision, record a neutral visual observation of the
  candidate image: what it visibly depicts, whether it contains desktop/window
  artifacts, whether it resembles prior route evidence, and whether it appears
  to be an independent design concept or a captured/modified implementation;
- after neutral observation, record an aesthetic verdict and concrete reasons
  for generated concept targets before implementation planning. A concept that
  is authentic but ugly, weak, incoherent, template-like, or disconnected from
  the shared visual direction routes back to concept repair or regeneration;
- when product-facing visual assets are created, record an aesthetic verdict
  and concrete reasons before UI implementation or package polish. A failed
  app icon or asset blocks completion until regenerated or repaired;
- when an app/software icon is in scope for a desktop, mobile, packaged web,
  browser-extension, or branded software artifact, record a real application
  identity binding gate from `autonomous-concept-ui-redesign`. An icon shown
  only inside the UI, a concept image, or a report is not enough. Evidence must
  show whether the selected icon source is bound to the runtime window/app
  icon, taskbar/dock/shelf identity, tray/menu-bar icon when present, and
  package/shortcut/installer manifest when packaging is in scope. If the host
  still shows a runtime icon such as Python/Electron/browser, record that as a
  partial/blocking gap instead of treating the in-UI mark as the final app icon;
- after rendered screenshot QA, record a rendered-UI aesthetic verdict and
  concrete reasons before divergence closure. A visually weak implementation
  cannot be closed only because screenshots exist or tests pass;
- after rendered screenshot QA, require a reviewer-owned personal walkthrough
  before visual or interaction closure. The walkthrough must cover pointer or
  keyboard reachability for current controls, actual click/toggle/tab paths,
  language and support/settings paths when present, text overlap/clipping,
  whitespace and density, crowded or underfilled regions, hierarchy,
  readability, and responsive/window-size fit;
- reviewer UI reports must include repair suggestions when the reviewer sees a
  weakness, such as what to add to large empty regions, what to simplify in
  crowded regions, which hierarchy or spacing should change, or which
  interaction path is not discoverable. The PM uses those suggestions as route
  mutation, local repair, follow-up, waiver, or stop input;
- after UI implementation, record rendered-QA evidence and the child skill's
  concept/implementation loop-closure decision;
- when product-facing visual assets are created, record whether they are in
  scope and persist the UI child-skill evidence that they were reviewed with
  the same visual system.

## Visual Example Particle

Visual examples are generated per route and must not be reused as design seeds
for a later UI route. When a repository contains historical visual examples,
FlowPilot treats them as old evidence unless the user explicitly designates one
as an authoritative reference for the current route.

When the user asks to see current FlowPilot progress, prefer a fresh route-local
progress surface or a documented fallback QA surface in `.flowpilot/`; do not
silently inherit a previous visual example.

## UI And Visual Evidence

For UI, desktop UI, dashboard, icon, or visual showcase routes, FlowPilot does
not restate design rules. It requires evidence that the relevant UI child
skills ran carefully and closed their own loops.

FlowPilot only enforces the process boundary:

- pre-implementation concept-target decision exists when required by the child
  skill;
- generated concept targets pass both source and authenticity gates. Source
  proves `imagegen` or an authoritative user reference; authenticity proves
  the target is an independent concept rather than a reused screenshot,
  screenshot variant, old route UI, desktop/taskbar capture, or prior failed
  UI evidence. Authenticity failure blocks implementation and routes back to
  concept regeneration;
- generated concept targets include a pre-judgement visual observation record
  that describes what the image appears to be before accepting or rejecting it;
- generated concept targets include an aesthetic verdict with concrete
  reviewer reasons before UI implementation planning;
- post-implementation rendered QA exists when required by the child skill;
- post-implementation rendered QA includes an aesthetic verdict with concrete
  reviewer reasons before divergence or loop closure;
- post-implementation rendered QA includes reviewer-owned personal walkthrough
  evidence. The reviewer, not only the controller or worker, must operate
  the rendered surface where the gate is interactive and record reachable and
  unreachable controls, text overlap/clipping, layout density, excessive
  whitespace, crowded areas, and concrete design recommendations;
- material concept/implementation differences are resolved or accepted through
  the child skill's divergence process;
- product-facing visual assets are included in the same UI evidence when they
  are in scope;
- product-facing visual assets include an aesthetic verdict with concrete
  reviewer reasons before UI or package completion;
- rendered QA evidence must not be relabeled as pre-implementation concept
  evidence unless the child skill or user explicitly waived the concept target.
- HTML/CSS prototypes, browser screenshots, WebView screenshots, or desktop
  render captures cannot satisfy an image-generation concept target when the
  UI child skill requires `imagegen`; they are implementation prototypes or
  post-implementation QA evidence unless the user supplied them as an
  authoritative reference before implementation.

Worker sidecar lifecycle:

```text
project-manager node decision
-> child-node sidecar scan
-> no need, reuse worker A/B if idle, or spawn/replace only when a worker slot is unavailable
-> bounded/disjoint sidecar task
-> sidecar report returned
-> authorized integration/review packet
-> worker returns to idle crew slot
```

Run the sidecar scan at child-node entry, not as a parent/module gate.
Worker agents handle bounded helper tasks inside the current child node. They
must not own the child node, route advancement, frozen acceptance floor,
checkpoint, or completion decision. The project manager may assign bounded
sidecar work, but an authorized integration worker or required reviewer must
merge/verify the result before dependent work proceeds. The controller only
relays the result, review request, and PM decision.

Reuse worker A or worker B before spawning or replacing capacity. Spawn or
replace only when no fixed worker slot is available or recoverable and the
sidecar task is worth the coordination cost.

Worker returned is not complete. The controller must route the result to the
required verifier/reviewer and then ask the project manager whether the current
node can proceed.

## Final Route-Wide Gate Ledger

Before terminal completion, the project manager must rebuild
`.flowpilot/runs/<run-id>/final_route_wide_gate_ledger.json` from the current route and
execution frontier. This is not the startup checklist and not the first route
plan. It is a dynamic ledger of the route that is actually effective after
repairs, inserted nodes, waived gates, superseded nodes, stale-evidence
invalidation, and child-skill loop closures.

The PM-owned ledger records:

- active route id and route version used to build the ledger;
- all effective nodes and gates on the current route;
- superseded nodes, their replacement or waiver reason, and why they no longer
  close current obligations;
- child-skill gates and completion standards collected from the current
  manifest and current-node refinements;
- human-like node, parent, final, strict-obligation, and same-inspector recheck
  gates;
- product-function and development-process model gates;
- root acceptance contract obligations, standard scenario replay obligations,
  and node acceptance plans for all effective nodes;
- generated-resource lineage for concept images, product-facing visual assets,
  screenshots, route diagrams, model reports, and other generated artifacts,
  with each item resolved to `consumed_by_implementation`,
  `included_in_final_output`, `qa_evidence`, `flowguard_evidence`,
  `user_flow_diagram`, `superseded`, `quarantined`, or
  `discarded_with_reason` with reason;
- stale, invalidated, missing, waived, blocked, and unresolved evidence;
- residual risk triage, with zero unresolved residual risks;
- `unresolved_count`.

After the PM ledger is clean, the project manager must build
`.flowpilot/runs/<run-id>/terminal_human_backward_replay_map.json`. This map
orders a terminal human backward replay from the delivered product to root
acceptance, parent/module nodes, and every effective leaf node. The reviewer
must personally inspect or operate the current product for each segment and
compare it with the frozen contract, parent goal, node acceptance plan,
standard scenarios, and node-risk scenarios. Ledger entries, worker reports,
screenshots, and model summaries are pointers only.

After each replay segment, the project manager records a segment decision:
continue, repair, route mutation, correct-role exception, or PM stop. The PM
cannot accept a segment reviewed only from reports. A real reviewer finding is
not parked as residual risk: the PM routes it to the appropriate repair target,
marks affected downstream nodes and evidence stale, mutates or repairs the
route, then rebuilds the final ledger and replay map. The default after any
terminal replay repair is to restart final review from the delivered product.
A narrower restart from an impacted ancestor is allowed only with a concrete PM
reason proving earlier segments cannot be affected.

Completion is blocked unless the PM ledger is built from the current route,
`unresolved_count` is zero, terminal human backward replay passes through all
root, parent, and leaf-node segments, every replay segment has a PM decision,
the repair/restart policy is recorded, and the project manager records a
ledger-specific completion approval with independent adversarial ledger audit
evidence. That PM audit must cite the current route/frontier, effective
entries, stale or superseded evidence checks, waiver authority, unresolved
counts, reviewer replay path, scenario replay, node acceptance plan coverage,
and risk triage. If the ledger or terminal replay finds a missing, stale,
blocked, wrongly superseded, untriaged, or unresolved risk item, the project
manager decides repair, route mutation, explicit waiver by the correct role, or
PM stop; after repair or mutation, the ledger is rebuilt from scratch and
replayed again.

Completion reports must not carry unresolved residual risks. The ledger may
include resolved issues, non-risk scope notes, and explicit exceptions approved
by the correct role. It may not declare completion while any `blocking`,
`test_gap`, `evidence_gap`, or `route_gap` risk remains.

## Chunk Rule

No formal chunk starts without:

- a PM-authored `NODE_PACKET` for exactly the current node;
- reviewer dispatch approval for that packet, with `can_pm_advance` or
  `dispatch_allowed` true for the current packet only;
- a packet holder/status entry showing whether the packet is with PM,
  reviewer, worker, controller, or user;
- explicit role-origin authority for every artifact that the chunk may use to
  close gates;
- PM-owned startup activation recorded in state and execution frontier from a
  current clean factual reviewer report;
- current route checked by FlowGuard;
- English summary synced from canonical machine-readable state;
- execution frontier written for the active route version;
- PM completion runway recorded with current gate, downstream steps, hard-stop
  conditions, and checkpoint cadence;
- visible Codex plan synced from that PM runway, including native
  `update_plan` or equivalent host-plan-tool evidence when available, fallback
  method when unavailable, and enough downstream runway depth to avoid a
  one-step projection;
- current-node completion guard loaded and showing that advance is allowed, or
  else the heartbeat must resume the unfinished active node;
- continuation readiness checked: automated heartbeat health when supported, or
  manual-resume state/frontier/crew-memory readiness when no real wakeup exists;
- user flow diagram or node roadmap emitted in chat;
- focused parent-scope grill-me completed for the active parent boundary;
- current parent subtree reviewed through FlowGuard;
- current parent product-function model checked;
- unfinished-current-node recovery checked;
- focused node-level grill-me completed for the active leaf node;
- active leaf product-function model checked;
- current-node high-standard recheck completed by the PM against the strongest
  feasible product target, unacceptable-result bar, and semantic-fidelity
  policy;
- current node acceptance plan approved, with inherited root high-risk
  requirements mapped, node-local experiments declared, selected standard
  scenarios recorded, and required experiments passed or triaged;
- lightweight heartbeat self-check completed for the current micro-step;
- quality package completed for feature thinness, improvement classification,
  child-skill mini-route visibility, validation strength, and rough-finish
  risk;
- required child-skill conformance gates completed or explicitly not in scope;
- strict gate-obligation review applied to reviewer-closable gates, with no
  current-gate caveat left open;
- chunk-level verification declared;
- no pending hard safety gate;
- no pending or returned sidecar subagent dependency.

Each formal chunk must declare:

- packet id and node id;
- assigned role or worker identity;
- intent;
- owned paths or owned responsibility;
- expected artifacts;
- verification commands or manual checks;
- allowed exits;
- recovery route if verification fails.
- anti-rough-finish checkpoint review before the node is marked complete.
- human-like product inspection before checkpoint, with repair route mutation
  and same-inspector recheck for any blocking issue.
- parent backward replay before any effective route node with children is
  marked complete, including structural parent-node enumeration, child-evidence
  replay, parent product-model comparison, human-like parent review, PM segment
  decision, and a structural route mutation if the children do not compose into
  the parent goal.

If the next step is uncertain, run a bounded experiment instead of a formal
chunk. Experiments answer one question and either resume the route, update the
route, or block with evidence.

For packet-gated runs, a chunk ends when the authorized worker returns
`NODE_RESULT`. The controller must relay that result to the reviewer and must
not execute the next chunk itself. If reviewer passes and PM issues the next
packet with `stop_for_user: false`, the controller continues the internal loop
by dispatching the next packet after reviewer dispatch approval. If reviewer
blocks, the PM must issue a repair packet or stop for the user; the controller
may not silently continue.

## Residual Risk Triage Gate

FlowPilot does not treat residual risks as an acceptable completion payload.
Whenever the PM, reviewer, officer, quality package, final ledger, or
completion self-interrogation identifies a risk-like item, the PM must triage
it before completion can proceed:

- `blocking`: route back to the affected node, create a repair node, or stop;
- `test_gap`: route back to QA or node acceptance planning and run the missing
  experiment;
- `evidence_gap`: collect or regenerate evidence, then rerun the affected
  approval;
- `route_gap`: mutate the route and rerun affected FlowGuard checks;
- `resolved_issue`: keep as history with repair and recheck evidence;
- `non_risk_scope_note`: rename as a scope note, not a residual risk;
- `explicit_exception_with_required_approval`: allowed only with correct-role
  approval and proof that the frozen contract is not lowered;
- `false_positive`: remove from unresolved counts with reason.

Final completion requires `unresolved_residual_risk_count == 0`. If a report
contains a section named residual risks, every item in it must be resolved,
renamed, explicitly excepted, or removed before the final report can be the
terminal completion report.

## Terminal Closure Suite

After final ledger approval and before final report, FlowPilot runs a terminal
closure suite recorded at
`.flowpilot/runs/<run-id>/terminal_closure_suite.json`. The suite is a hard
gate and runs in this order:

1. confirm the defect ledger has zero open blockers and zero
   fixed-pending-recheck defects;
2. reconcile the evidence ledger so invalid, stale, superseded, fixture-only,
   synthetic, historical, and generated-concept evidence is accounted for and
   no invalid item closes a current gate;
3. confirm residual risk triage has zero unresolved items;
4. synchronize terminal state across `state.json`,
   `execution_frontier.json`, active `flow.json`, `run.json`,
   `.flowpilot/current.json`, and `.flowpilot/index.json`;
5. refresh terminal-state evidence such as screenshots, scenario replay
   outputs, and final acceptance rechecks;
6. rebuild the final ledger if evidence changed;
7. run lifecycle reconciliation across Codex heartbeat automations, local
   state, frontier, and heartbeat/manual-resume evidence;
8. pause/delete route heartbeat when automated continuation was used, or record
   manual-resume no-automation evidence;
9. archive role memory and crew status;
10. write the PM-owned FlowPilot skill improvement report for future manual
   root-repo maintenance;
11. write the final report only when required lifecycle actions are zero.

The final report is therefore a terminal output, not the thing that performs
cleanup. If cleanup changes state, evidence, screenshots, or the ledger, the
affected final checks rerun before completion is claimed.

The skill improvement report is different from product risk triage. Its
observations never require root-repo fixes before the current project can
complete. They are preserved so the user can later inspect what FlowPilot
itself should improve.

## Route Updates

Create a new route version when the structure changes. Keep old routes.

Update the model and rerun checks when:

- real verification exposes a model gap;
- a new failure branch appears;
- the implementation path changes;
- a rollback or alternate route is needed.
- completion self-interrogation finds obvious high-value work.
- parent-subtree review finds missing, stale, oversized, misplaced, or
  unnecessary child nodes.
- child-skill conformance review finds that a required child-skill step,
  evidence item, or quality loop was skipped and the parent route structure
  must change.
- the quality package classifies an improvement as medium or large rather than
  a small current-node addition.
- human-like inspection or backward review finds a blocking product,
  interaction, visual, localization, conflict, or completion-quality issue.
- composite backward review finds that the right fix is to return to an
  existing child, insert a sibling child, rebuild a child subtree, or bubble the
  impact to a higher parent.

Do not create a new route for ordinary progress updates inside the same route.
Use heartbeats, node reports, and checkpoints for that.

When a route structure changes, do not encode the new next jump in the
heartbeat automation prompt. Create or update the route version, rerun the
affected FlowGuard checks, rewrite `.flowpilot/runs/<run-id>/execution_frontier.json`, sync
the visible Codex plan list from that frontier, and then refresh the user flow
diagram.

Changing how the route is displayed in chat or Cockpit is not, by itself, a
route-structure change. The display should read from `state.json`, active
`flow.json`, heartbeats, node reports, and checkpoints rather than creating a
new route merely to make progress visible.

## Hard Gates

Stop and ask the user before:

- changing the frozen acceptance contract;
- publishing, releasing, deploying, or pushing external changes;
- destructive or irreversible filesystem actions;
- major technology-stack changes;
- handling secrets or private account data;
- lowering completion standards.

Record the request and result in `.flowpilot/heartbeats/` or the active node
report.

## Automatic Tool Installation

FlowPilot may install missing tools and libraries automatically when the
installation is project-local, reversible, non-secret, and needed to run the
declared checks or implementation. Examples include ordinary package-manager
dependencies, test tooling, linters, formatters, local scripts, and small helper
CLIs.

Do not batch-install every dependency that might be useful later. Startup should
record a dependency plan, install only the minimum tools needed to run FlowPilot
and the current checks, and defer the rest until an active route node, chunk, or
verification command requires them.

Before installing, record:

- what is missing;
- why it is needed;
- the planned command;
- the verification that will prove it works.

After installing, record the command result and rerun the relevant checks.

Stop for user approval before heavy, global, paid, private-account, destructive,
or system-wide installations. Even after approval, heavy/system-wide
installations should be demand-driven: run them when the active node needs that
tool, not merely because a later route might prefer it. A dependency install is
not a hard gate merely because it is an install.

## Completion

Complete only when:

- frozen contract remains intact;
- route checks pass;
- required capability evidence exists;
- sidecar subagent work is merged and verified by an authorized
  integration/review packet;
- final verification passes;
- anti-rough-finish review has passed;
- every completed node has product-function model evidence, human-like
  inspection evidence, and any blocking issue closed through same-inspector
  recheck;
- every completed reviewer-closable gate has strict obligation evidence
  showing that no current-gate requirement was deferred as a caveat;
- final product-function model replay and final human-like inspection pass;
- final feature matrix review, acceptance matrix review, and quality-candidate
  review are complete;
- completion self-interrogation finds no obvious high-value work remaining;
- PM-owned final route-wide gate ledger is rebuilt from the current route,
  every effective node and child-skill gate is accounted for, root acceptance
  obligations and node acceptance plans are accounted for, standard scenarios
  are replayed where selected, stale evidence and superseded nodes are
  checked, `unresolved_count` is zero, `unresolved_residual_risk_count` is
  zero, the terminal human backward replay map is built, the human-like
  reviewer has replayed from the delivered product through root, parent, and
  leaf-node obligations, every replay segment has a PM decision, repair/restart
  policy is recorded, and the project manager has approved the clean ledger;
- terminal closure suite has synchronized terminal state files, refreshed
  terminal evidence, rerun affected checks, reconciled lifecycle authorities,
  and found zero required cleanup actions;
- final report is written after terminal closure;
- host continuation mode has been reconciled: automated routes stop automated
  heartbeat state; manual-resume routes record that no heartbeat automation was
  created;
- lifecycle reconciliation has scanned Codex heartbeat automations, local
  state, execution frontier, and heartbeat/manual-resume evidence;
- the persistent crew ledger and role memory packets are archived with final
  role statuses after lifecycle reconciliation;
- terminal continuation state has been written back to
  `.flowpilot/runs/<run-id>/state.json`,
  `.flowpilot/runs/<run-id>/execution_frontier.json`, lifecycle evidence,
  heartbeat evidence, or explicit manual-resume no-automation evidence.

The final response should cite the current route, checkpoints, verification
commands, skipped checks with reasons, resolved issues, non-risk scope notes,
and explicit exceptions if any. It must not list unresolved residual risks on a
completed route. Do not claim a skipped check passed. If the route is complete,
the final response states that the FlowPilot task is complete. If the route is
not complete and this is a controlled stop, the final response includes the
appropriate automated or manual-resume notice.

## References

- `references/protocol.md`: compact operator protocol.
- `references/packet_control_plane.md`: packet-gated controller/PM/reviewer/worker
  loop and role-origin evidence rule.
- `references/installation_contract.md`: dependency and self-check contract.
- `references/failure_modes.md`: failures the FlowGuard models must keep
  guarding against.
- `assets/README.md`: local asset map for templates and model starters.
- `assets/templates/startup_banner.md`: approved startup banner for visible
  FlowPilot launch.
