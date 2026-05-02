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
heartbeat/watchdog language, or the presence of `.flowpilot/`.

If a project already contains `.flowpilot/`, treat it only as resume or
continuity state after explicit invocation. The directory is not a trigger by
itself.

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

## Three-Question Startup Gate

Before the banner, route creation, child skills, image generation,
implementation, or model-backed work, FlowPilot must ask exactly these startup
questions and stop until all three have explicit answers:

1. Run mode: `full-auto`, `autonomous`, `guided`, or `strict-gated`.
2. Background agents: allow the standard six live background subagents, or use
   single-agent six-role continuity for this run.
3. Scheduled continuation: allow heartbeat/automation jobs, or use manual
   resume only for this run.

The user may answer in one compact sentence, such as
`FlowPilot: full-auto, allow background agents, allow heartbeat`. That counts
as all three answers only if the answers are explicit. If any answer is
missing, ambiguous, or says to pause, FlowPilot must remain in
`startup_pending_user_answers` and ask for the missing answer. Do not infer an
answer from "use FlowPilot", from the task's importance, from current tool
availability, or from previous routes.

After asking the three questions, the assistant's response must end immediately
and control must return to the user. Do not keep planning, inspecting files,
starting tools, creating route state, launching subagents, probing heartbeat, or
showing the banner in the same response that asks the questions. Record this as
`startup_activation.startup_questions.dialog_stopped_for_user_answers: true`
before accepting a later user reply as startup-question evidence.

Only after the three startup answers are recorded from the later user reply may
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

- `.flowpilot/state.json`;
- `.flowpilot/execution_frontier.json`;
- `.flowpilot/routes/<active-route>/flow.json`;
- `.flowpilot/crew_ledger.json`;
- all six role memory packets;
- continuation evidence, either automated heartbeat/watchdog/global supervisor
  readiness or explicit `manual-resume` no-automation evidence.

The human-like reviewer must personally check facts and write
`.flowpilot/startup_review/latest.json`. This is not approval and it is not a
copy of worker claims. The report must include the actual evidence sources
checked: user answers, current state/frontier/route, crew and role memory,
old-route/old-asset cleanup boundary, real Codex automation records, Windows
scheduled watchdog tasks when on Windows, global watchdog registry/supervisor
records, and latest watchdog evidence.

The project manager reads that factual report, either sends concrete
remediation items back to the workers/main executor or writes
`.flowpilot/startup_pm_gate/latest.json` opening startup from the current clean
reviewer report.

`startup_activation.work_beyond_startup_allowed` must be true in state and
frontier before work beyond startup, and that flag may be written only by the
PM start-gate decision after a clean factual reviewer report.
`startup_activation` must include `startup_preflight_review` and
`pm_start_gate` blocks.
`startup_activation.startup_questions`
must show that the three-question prompt was asked before the banner, that the
assistant stopped to wait for the user's reply, and that explicit answers for
run mode, background agents, and scheduled continuation were later recorded
before the banner is considered valid. The reviewer report must compare user
authorization against actual state: live/single-agent role evidence,
heartbeat/watchdog/global-supervisor evidence, route/state/frontier
consistency, stale or residual route state, and any required old-route or old
asset cleanup. `startup_activation` must then agree with those answers: live
background agents only when the user allowed them, single-agent six-role
continuity only when the user selected it, and heartbeat/automation only when
the user allowed scheduled continuation. If any answer, wait-state evidence,
matching evidence, reviewer report, PM open decision, or cleanup evidence is
missing, stop at startup and route remediation back through PM and workers; do
not silently fall back. If only a route-local file, generated concept,
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
answers. It asks the three questions and stops; the next user reply may answer
all three in one compact sentence.

## Startup Workflow

1. On FlowPilot invocation, enter `startup_pending_user_answers`.
2. Ask the three startup questions: run mode, background-agent permission, and
   scheduled-continuation permission. End the assistant response immediately
   after the questions and wait for the user's reply. No plan continuation, tool
   call, route write, child-skill loading, imagegen, subagent startup, heartbeat
   probe, or banner is allowed in that question-asking response.
3. Record the explicit answer set in state/frontier startup activation
   evidence. Do not infer fallback authorization.
4. Emit the fenced startup banner in chat so the user can clearly see the
   startup-question gate has opened and the formal FlowPilot controller has
   started.
5. Enable FlowPilot, create or load `.flowpilot/`, and record the selected mode.
6. Commit the showcase-grade long-horizon floor.
7. Run visible full grill-me using FlowPilot's formal invocation policy. In
   the same startup round, draft the intended acceptance floor, seed the
   improvement candidate pool, seed the initial validation direction, and
   surface product-function questions. Do not freeze the contract yet.
8. Create or restore the fixed six-agent crew and write
   `.flowpilot/crew_ledger.json` plus one compact role memory packet under
   `.flowpilot/crew_memory/` for each role: project manager, human-like
   reviewer, process FlowGuard officer, product FlowGuard officer, worker A,
   and worker B. Persist role authority, agent ids or recovery status, latest
   report paths, memory paths, replacement rules, and role-memory freshness
   before formal route work.
9. Give the project manager the startup self-interrogation evidence, draft
   floor, current crew ledger, and current role memory packets. The project
   manager ratifies the startup interrogation. From this point the project
   manager owns route, resume, repair, and completion decisions; the main
   executor implements those decisions and enforces hard safety gates.
10. Before PM product-function synthesis or route decisions, require the main
    executor to write a `.flowpilot/material_intake_packet.json`. This packet
    inventories user-provided and repository-local materials, summarizes what
    each source is for, classifies authority/freshness/contradictions/missing
    context, and names what remains unread or uncertain.
11. The human-like reviewer must approve material sufficiency before PM route
    planning. The reviewer checks whether the packet is clear enough for the
    project manager: no obvious sources omitted, source summaries are not
    superficial, large tables/documents are sampled or scoped honestly,
    contradictions and uncertainty are visible, and the packet will not
    mislead route design. If the reviewer blocks, the main executor revises
    the intake packet before PM planning continues.
12. The project manager writes
    `.flowpilot/pm_material_understanding.json` from the reviewed packet and
    user intent. It records source-claim matrix, open questions, material
    complexity (`simple`, `normal`, or `messy/raw`), and whether materials can
    feed product/route design directly or require a formal discovery, cleanup,
    modeling, validation, or research subtree before implementation.
13. Require the project manager to synthesize
    `.flowpilot/product_function_architecture.json` before contract freeze.
    The package must include a user-task map, product capability map, feature
    necessity decisions (`must`, `should`, `optional`, `reject`), display
    rationale for every visible label/control/status/card, missing high-value
    feature review, negative scope, and a functional acceptance matrix.
14. The product FlowGuard officer approves or blocks whether the architecture
    can be modeled and checked. The human-like reviewer challenges usefulness:
    unnecessary features, unnecessary visible text, missing workflow support,
    bad defaults, weak failure states, and gaps between user tasks and product
    behavior. If either role blocks, the project manager revises the package
    before the route continues.
15. Freeze the acceptance contract as a floor, not a ceiling, from the
    approved product-function architecture and startup self-interrogation.
16. Write `capabilities.json`, including product-function architecture
    evidence.
17. Ask the project manager to discover likely child skills from the frozen
    contract and capability manifest. For each likely invoked child skill, load
    the child skill's `SKILL.md` and only the relevant references, then extract
    a child-skill gate manifest: key stages, required checks, standards,
    evidence needs, skipped references with reasons, and the visible
    mini-route. This is route-design input, not an execution-time afterthought.
18. Assign `required_approver` for every child-skill gate before route
    modeling. Product, visual, interaction, real-use, and strict-review gates
    require the human-like reviewer when they are review judgements; process
    and conformance gates require the process FlowGuard officer; product or
    functional behavior gates require the product FlowGuard officer; route
    inclusion, route mutation, and parent return require the project manager.
    The main executor, worker A, and worker B are forbidden approvers for
    child-skill gates.
19. Have the human-like reviewer, process FlowGuard officer, and product
    FlowGuard officer review their slices of the child-skill gate manifest.
    The project manager then approves or blocks manifest inclusion in the
    initial route, execution frontier, and PM completion runway.
20. Verify FlowGuard and required skills.
21. Inspect dependency/tool needs and write a dependency plan.
22. Install only the minimum dependencies needed for FlowPilot itself and the
    current route/model checks.
23. Defer future route, chunk, or native-build dependencies until the node or
    check that actually needs them.
24. Probe the host continuation capability only after the user has answered
    the scheduled-continuation startup question. If the user allowed scheduled
    continuation and setup fails or is unsupported, stop and ask for a new
    decision; do not silently switch to manual resume.
25. If the user allowed scheduled continuation and the host supports real
    wakeups or automations, create the continuation
    bundle as one lifecycle setup: stable heartbeat launcher, paired external
    watchdog, and singleton global watchdog supervisor. The heartbeat prompt
    should load persisted state, the execution frontier, crew ledger, and role
    memory packets,
    restore or replace the crew from that memory, and ask the project manager
    for a completion-oriented runway plan from the current position to project
    completion; it should not be rewritten for ordinary route or plan changes.
    The watchdog records stale threshold,
    busy-lease policy, evidence path, automation id/task name, official
    automation reset action, hidden/noninteractive execution evidence,
    user-level global record path, singleton global-supervisor status, and no
    false claim that a reset is proof of recovery before a new heartbeat
    appears.
26. If the user selected manual resume, do not create any heartbeat, paired
    watchdog, or global supervisor. Record `manual-resume` continuation mode,
    keep `.flowpilot/` state/checkpoints authoritative, and continue the formal
    route without claiming unattended recovery.
27. Ask the project manager for the initial route-design decision.
28. Ask the process FlowGuard officer to use FlowGuard as process designer for
    the control route.
29. Generate a candidate route tree from the approved product-function
    architecture, frozen contract, and PM-approved child-skill gate manifest.
30. The process FlowGuard officer authors, runs, interprets, and approves or
    blocks the root development-process model against that candidate tree.
31. The product FlowGuard officer authors, runs, interprets, and approves or
    blocks the root product-function model for what the product or workflow
    itself must do, using the approved product-function architecture as a
    source artifact.
32. The matching officers inspect counterexamples for both model scopes and
    write approve/block reports.
33. The process FlowGuard officer authors and runs the strict gate-obligation
    review model so reviewer caveats cannot close a current gate unless all
    current-scope obligations are already resolved.
34. Freeze the checked candidate as the first route version in `flow.json`.
35. Generate English `flow.md`.
36. Write `.flowpilot/execution_frontier.json` from the checked route, active
    node, current subnode/gate when applicable, next node, current mainline,
    fallback, and checks before the next jump. Include the current-node
    completion guard: whether the active node is unfinished, the concrete
    `current_subnode` or `next_gate` that must run next, what evidence is
    required before advance, and whether advance is currently allowed. Include
    the latest project-manager completion runway: current gate, downstream
    steps to completion, role/hard-stop boundaries, checkpoint cadence, and any
    PM stop signal.
37. Sync the visible Codex plan list from the latest PM completion runway, not
    only from the next local gate. Replace the current visible plan projection
    whenever the PM issues a new runway, while retaining old PM decisions and
    checkpoints as history. If the host exposes a native visible plan/task
    list tool, such as Codex `update_plan`, call that tool immediately with
    the PM runway before executing work. Writing `.flowpilot` plan evidence
    alone does not satisfy this gate when the native tool exists. Do not
    change the heartbeat automation prompt just because the route or next jump
    changed.
38. Emit the user flow diagram in chat when this is startup, a key node change,
    route mutation, completion review, or user request. Include active route,
    active node, next jumps, checks, fallback branches, continuation state, and
    current acceptance delta as nearby text.
39. Set `startup_activation` in state/frontier from the three-question prompt,
    the recorded stop-and-wait state, the three explicit startup answers,
    banner evidence, current route, execution frontier, crew ledger, role
    memory, live-subagent startup decision, continuation, and visible plan
    evidence. The human-like reviewer then writes
    `.flowpilot/startup_review/latest.json` from direct fact checks. The report
    checks user authorization against actual state, including background-agent
    count and role identity, the real route heartbeat automation at one minute,
    the external Windows watchdog task, the singleton global supervisor at
    thirty minutes, global registry registration, route/state/frontier
    consistency, residual or shadow route state, latest watchdog evidence, and
    any user-requested clean-start or old-asset cleanup. If the user allowed
    background agents, the reviewer verifies six live role-bearing subagents
    started or resumed after that user decision. If the user chose single-agent
    continuity, the reviewer verifies explicit fallback authorization and does
    not claim live subagents. The reviewer does not
    output approval and cannot open startup.
    The project manager reads the report. If it has blocking findings, the PM
    sends concrete remediation items back to the workers/main executor and
    requires another reviewer report after repair. If the report has no
    blockers, the PM writes `pm_start_gate` evidence opening startup from that
    exact factual report and sets `work_beyond_startup_allowed: true`.

    Do not run child skills, imagegen, implementation, formal route chunks, or
    completion work until the PM records
    `work_beyond_startup_allowed: true`. If the three startup answers are not
    complete, if the prompt did not stop for the user's reply, if the banner was
    emitted before the answers, if live-agent evidence conflicts with the
    background-agent answer, or if continuation evidence conflicts with the
    scheduled-continuation answer, or if old-route cleanup evidence is missing
    after a clean-start user request, the PM sends the issue back for worker
    remediation. A route-local file without matching canonical
    state/frontier/crew/continuation evidence is a shadow route and must be
    quarantined or superseded before continuing.
40. Execute the first bounded chunk only after the continuation mode is known.
    In automated mode, the heartbeat rehydrates the crew from persisted role
    memory, asks the project manager for a completion-oriented runway, and the
    main executor syncs that runway into the current visible plan projection.
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

The main executor owns the descriptive intake and writes
`.flowpilot/material_intake_packet.json`. It records:

- `user_intent`: the user request and the decision the materials must support;
- `material_inventory`: each user-provided, repository-local, generated, or
  referenced source, with path/source, format, size or scope, current status,
  and why it might matter;
- `source_summaries`: what each source appears to contain, what it is for, and
  what it does not prove;
- `source_quality`: authority, freshness, completeness, contradiction risk,
  privacy/safety concerns, and whether the source is primary evidence, context,
  or only a lead;
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
`.flowpilot/pm_material_understanding.json`. It records the PM's interpretation
of the materials, a source-claim matrix for important route assumptions, open
questions, material complexity (`simple`, `normal`, or `messy/raw`), and the
route consequence. If materials are `messy/raw`, material understanding becomes
formal work: the PM inserts discovery, cleanup, spreadsheet analysis, entity
modeling, research, validation, or reconciliation nodes before product design
or implementation nodes that depend on those materials.

## Product Function Architecture Gate

This gate sits after startup full grill-me, project-manager ratification, and
reviewer-approved material handoff, and before acceptance contract freeze,
route generation, capability routing, or implementation. It answers what the
product must functionally do before FlowPilot commits the route.

The project manager owns the synthesis and writes
`.flowpilot/product_function_architecture.json`. The package is required to
contain:

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
usefulness and completeness by comparing the PM architecture against the user
request, inspected materials, and expected workflow reality: unnecessary
features, missing high-value workflow support, confusing display choices, weak
default states, failure states, and gaps between what users need and what the
product exposes.

The acceptance contract freezes only after this package exists and both
review slices are resolved. Later product-function models refine and verify
the architecture; they do not replace this pre-contract PM product design
gate.

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

Write `.flowpilot/crew_ledger.json` and one role memory packet under
`.flowpilot/crew_memory/` before formal route work. The ledger names each role,
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
- `agent_id`: the host/runtime handle used only for best-effort resume and
  diagnostic evidence.

Do not use raw `agent_id` as the primary UI label or as the authority key.
Nickname changes, regenerated subagent display names, or replacement agents do
not change the `role_key`.

Live subagent continuity is a startup target with an explicit fallback gate.
Role continuity is mandatory. If the current user request explicitly authorizes
background agents and the host/tool policy permits them, FlowPilot spawns or
resumes live subagents for the fixed roles and may use bounded sidecar work. If
live subagents are unavailable, not authorized, or not supported by the host,
FlowPilot pauses and asks for the missing decision instead of silently
downgrading. A recorded user choice to continue without live subagents lets
FlowPilot mark affected roles as `replaced_from_memory`, `memory_recovered`,
or an equivalent memory-seeded status, load the latest role memory packets,
and continue under the same authority boundaries. A heartbeat or manual resume
may try to resume a stored `agent_id` when the host supports that operation,
but it must not assume that a live subagent still has private chat context. If
the old agent cannot be resumed, FlowPilot either starts a replacement live
agent after authorization or, after explicit fallback approval, replaces that
role with the same role charter plus the latest role memory packet. A
replacement role that starts from a generic prompt without its memory packet is
not recovered and cannot approve gates.

Heartbeat recovery loads the ledger and all required role memory packets first,
checks the memory schema/freshness, records which roles were resumed,
replaced, or blocked, and only then asks the project manager for a
completion-oriented runway from the current route position to project
completion. If any required role is missing and cannot be replaced from memory,
the current gate blocks rather than falling back to main-executor approval.

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
- live startup state, route, frontier, role memory, automation records, Windows
  scheduled task evidence, global supervisor, watchdog evidence, and cleanup
  boundary for startup;
- loaded child-skill source instructions, mapped gates, evidence plan, actual
  child-skill outputs, and output/evidence match for child-skill gates;
- actual product behavior, rendered output, logs, screenshots, interactions, or
  backend effects for implementation inspections;
- current route/frontier/ledger/evidence files and delivered product for final
  backward replay.

A reviewer decision that cites only a worker/PM summary without direct
fact-check evidence is invalid. PM decisions may rely on reviewer reports only
after those reports identify the factual sources checked and contain no current
gate blockers.

The main executor is not the project manager. It performs local edits, tool
calls, integrations, non-model verification, and hard-gate enforcement. It may
provide product context, source paths, logs, screenshots, and prior evidence to
the FlowGuard officers, but it must not author, run, interpret, or approve
FlowGuard model gates for them. If the project manager's decision conflicts
with a hard safety gate, blocking reviewer report, FlowGuard counterexample,
or user instruction, the main executor feeds that conflict back to the project
manager for a corrected route decision instead of silently overriding the
route.

## Actor Authority Matrix

Formal FlowPilot gates carry actor authority, not only evidence paths. The
main executor may draft non-model evidence, run ordinary local tools, edit
files, and integrate results, but its output remains a draft until the correct
role approves the gate. FlowGuard model gates are different: the matching
FlowGuard officer is the draft owner, execution owner, interpreter, and
required approver. Evidence existence is not approval.

Each meaningful gate in `.flowpilot/execution_frontier.json` records:

- `gate_id`;
- `draft_owner`: who may create draft evidence;
- `execution_owner`: who performs the main work or inspection;
- `required_approver`: the only role whose approval can advance the gate;
- `forbidden_approvers`: roles whose approval attempt is invalid;
- `approval_status`: `draft`, `pending`, `approved`, `blocked`, or
  `superseded`;
- `approval_evidence_path`;
- `blocked_reason` and `route_mutation_required` when blocked.

Authority rules:

- startup self-interrogation may be drafted by the main executor, but the
  project manager must ratify it before route/model gates advance;
- material intake is drafted by the main executor, sufficiency-approved by the
  human-like reviewer, and interpreted by the project manager before product or
  route decisions;
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

If the required approver is unavailable, heartbeat recovery restores or
replaces that role before work continues. If restoration fails, the current
gate is blocked with evidence; it is not self-approved by the main executor.

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

The main executor and worker agents may draft evidence, run ordinary tools, or
implement the current chunk, but they cannot approve a child-skill gate. If a
child-skill gate has draft evidence but lacks its required approver, the gate
is pending or blocked. It is not complete.

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
chat, then persist the structured evidence under `.flowpilot/capabilities/`.

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

Until the desktop Cockpit can reliably show live progress, the chat is the
temporary cockpit. FlowPilot has one user-facing flow diagram for both chat and
the Cockpit UI. Show it at startup, key node changes, route mutation,
completion review, or explicit user request. Do not refresh or repost it on
every heartbeat.

The user flow diagram is a projection of existing canonical route/frontier
state; it is not a separate execution path and it must not invent a new route.
The graph should stay at 6-8 major FlowPilot stages and highlight where the
current `active_route` and `active_node` sit. Chat and UI use the same generated
Mermaid source at `.flowpilot/diagrams/user-flow-diagram.mmd`.

Raw FlowGuard Mermaid exports are diagnostic state graphs. They are disabled by
default, generated only on explicit request, and must not replace the user flow
diagram in chat or UI.

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
evidence. If the UI is not yet available, the user flow diagram, node jumps,
planned checks, and verification results must be visible in the conversation.

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
interprets, and approves or blocks product-function models. The main executor
may provide context and receive the officer report, but it must not author or
run the FlowGuard model files on the officer's behalf. A model file, passing
command output, or main-executor summary is not approval unless the matching
officer produced it and wrote an approval or blocking report. A blocking
officer report follows the same repair route as inspection failure: issue
grill, PM repair-strategy interrogation, PM route decision, stale-evidence
invalidation, frontier rewrite, repair model, repair evidence, and same-class
recheck.

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
to generate candidates, assigned officer scope, and the answer shape needed for
PM action. Use `flowguard_modeling_request.template.json` for persistent
evidence. The assigned officer first performs a modelability check. If the
request lacks evidence, the route gains an evidence-collection node. If the
request is too broad, the route gains split modeling requests. Only a modelable
request may produce a decision report.

The officer report must include coverage, blindspots, failure paths,
recommendation, confidence, next smallest executable action, and any route
mutation candidate. Use `flowguard_modeling_report.template.json`. The PM then
synthesizes the report and records one of: continue current route, mutate the
route, add evidence work, split the request, or block with a concrete reason.
An officer report is advisory; PM synthesis is the route decision.

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
real product-style inspection: operate the app or workflow when possible,
compare concept to rendered output for UI work, inspect functional behavior,
look for duplicate or conflicting controls, check localization/content
coverage, and ask whether the result is a complete product rather than a
running artifact.

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

Backward inspection also runs at every non-leaf/composite scope, not only at
final completion. A parent node does not close merely because each child passed
locally. After all children under a parent/module/group pass their local
checks, FlowPilot replays child evidence against the parent product-function
model, runs a human-like backward review for the parent goal, and closes the
parent only after that review passes. The same rule repeats upward: child
nodes close into their immediate parent, parents close into larger phase nodes,
and phases close into the root route.

If a composite backward review fails, FlowPilot must classify the structural
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
parent impact bubbling. A composite backward review failure cannot be waived by
saying that all children passed individually. Before writing the structural
route mutation, grill the project manager on the repair strategy: affected
child versus missing sibling versus subtree rebuild, whether impact bubbles to
the parent, which evidence becomes stale, what the next executable target is,
and how the parent review will be rerun.

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
must not create heartbeat, watchdog, or global-supervisor automation and must
not claim unattended recovery.

Every automated heartbeat must load `state.json`, the active `flow.json`,
`.flowpilot/execution_frontier.json`, `.flowpilot/crew_ledger.json`, and
`.flowpilot/crew_memory/`. It then rehydrates the fixed six-agent crew:
resume known agent ids when possible, and if live agents are unavailable,
record the block and ask before replacing roles from memory packets. Only
after live startup or explicit fallback authorization is recorded may it record
the rehydration status and ask the project manager for a completion-oriented
runway from the current route position to project completion. Manual-resume
turns load the same files and ask for the same PM runway before continuing. The
runway must include the current gate, downstream
steps, role approvals, hard-stop conditions, checkpoint cadence, and any PM
stop signal. The main executor immediately replaces the current visible Codex
plan projection with that runway and continues along it until the PM stop
signal, a hard gate, a blocker, route mutation, or real environment/tool limit
stops progress. If the current node is unfinished after an interruption, the
next automated heartbeat or manual resume resumes that same node. It may not
advance to the next node until validation and evidence for the current node
are written.
Concretely, `unfinished_current_node: true` or
`current_node_completion.advance_allowed: false` means the continuation turn
must keep working on `active_node` and must ignore `next_node` as an execution
target.
`next_node` is only a planned jump after the completion guard is satisfied.
The PM runway must include the persisted `current_subnode` or `next_gate` for
that unfinished node, but it must not stop at that single gate. The automated
heartbeat or manual-resume turn must execute at least the selected gate when it
is executable, then continue along the PM runway as far as hard gates and real
execution limits allow. It may not end by only writing a future-facing
decision such as "continue to icon generation" or "next do X" while the gate is
still executable. Continuation evidence must name the PM runway, the selected
gate, actions attempted, results, checkpoint writes, and the updated
completion guard.

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
JSON note. When a native plan tool exists, the main executor must call it after
each PM runway decision and after any route mutation that changes the runway.
The plan must contain the current executable gate plus downstream runway items
toward completion. Do not leave the native plan as a one-step list, and do not
stop just because the first item is complete while the PM runway still has
executable downstream work. If the host has no native plan tool, record the
fallback projection method in `.flowpilot/execution_frontier.json` and show the
runway in chat, but do not claim that the native Codex plan was synced.

When the route mutates, update and recheck the route, rewrite the execution
frontier, then sync the visible Codex plan. Do not rewrite the stable heartbeat
launcher unless the host automation itself is missing or broken.

For multi-hour formal routes on hosts with real wakeups, FlowPilot also uses
an external watchdog as a third continuity layer. The watchdog reads
`.flowpilot/state.json`, the
active route, the latest heartbeat evidence, and `.flowpilot/busy_lease.json`.
Because Codex heartbeats do not interrupt an already-running turn, long
bounded operations must write an active busy lease before starting and clear or
refresh it after finishing. If the heartbeat is older than the configured
threshold but a matching non-expired busy lease is active for the current
route/node, the watchdog records `busy_not_stale` and must not request a reset.
If the busy lease was just cleared, the watchdog must allow a bounded
post-busy grace window before requesting reset, because the next heartbeat can
only arrive after the active turn yields back to the host scheduler. Default
the stale threshold to 10 minutes. Default the grace window to 10x the
heartbeat interval unless route evidence records a different value. With a
one-minute heartbeat, this is a 10-minute grace. If the heartbeat is older than
the configured threshold and no valid busy lease or post-busy grace exists, it
writes `.flowpilot/watchdog/latest.json` and event evidence requiring FlowPilot
to use the official Codex app automation interface to set the active heartbeat
automation to `PAUSED`, then back to `ACTIVE`. The watchdog does not edit
`automation.toml` directly. The reset is a recovery action, not proof that
Codex resumed; the proof is a later heartbeat with a newer timestamp.

The watchdog also writes a compact user-level global record unless explicitly
disabled for a test. Use `$FLOWPILOT_GLOBAL_RECORD_DIR` to override the
directory; otherwise it uses `$CODEX_HOME/flowpilot/watchdog`. Project-local
watchdog evidence remains authoritative. The global registry is only an index
for the singleton global supervisor, which must reread local state and
watchdog evidence before recording any reset requirement.

Watchdog source of truth is intentionally narrow. Reset decisions may trust
only project-local `state.json`, latest heartbeat evidence, and
`.flowpilot/busy_lease.json`. `.flowpilot/execution_frontier.json`,
`.flowpilot/lifecycle/latest.json`, host automation metadata, and global
watchdog records are diagnostic drift signals only. Live subagent busy state is
not a reliable host-provided source and must not be used by the watchdog. Each
watchdog record must include a `source_status` block naming trusted sources,
diagnostic sources, source timestamps, drift warnings, and
`live_subagent_state_used: false`.

Heartbeat, watchdog, and global supervisor lifecycle is all-or-none. The
project/route heartbeat cadence is fixed at one minute: create route
heartbeats with `rrule: FREQ=MINUTELY;INTERVAL=1` and record
`route_heartbeat_interval_minutes: 1` plus the rrule in route/frontier
evidence. This one-minute route heartbeat is separate from the user-level
global supervisor cadence and must not reuse the global supervisor's
30-minute rrule. Whenever FlowPilot creates or updates a real heartbeat
continuation for a formal long-running route, it must create or verify the
paired external watchdog and verify the singleton global supervisor in the
same setup phase. If any piece cannot be created, roll back to
`manual-resume` before route execution or record a concrete blocker. Do not
leave a half-created heartbeat without watchdog/global-supervisor evidence,
and do not create watchdog/global-supervisor automation when the host probe
found no wakeup support.

Pause, restart, and terminal closure use one unified lifecycle reconciliation
gate. Before claiming any of those states, FlowPilot scans Codex app
automations, the user-level global supervisor/registry, Windows scheduled
tasks, `.flowpilot/state.json`, `.flowpilot/execution_frontier.json`, and
latest watchdog evidence. Disabled Windows scheduled tasks still count as
residual lifecycle objects unless they are explicitly unregistered or waived
with a reason. Use `scripts/flowpilot_lifecycle.py` as the read-only inventory
helper and then perform required Codex automation changes through the official
Codex app automation interface.

At terminal closure, first write terminal/inactive route state and unregister
this project's global supervisor registration lease. Then stop or delete the
project watchdog automation and record `stopped_before_heartbeat`, write the
stopped/inactive lifecycle state back to `state.json`,
`.flowpilot/execution_frontier.json`, lifecycle evidence, and watchdog
evidence, and only then stop or delete the heartbeat automation. The
user-level global supervisor is handled after this project cleanup and is
deleted only if a locked registry reread shows no active, unexpired
registrations remain.
This is a final writeback gate, not a requirement to repeatedly poll the
watchdog during ordinary route progress.
Ordinary route progress, checkpoint writes, node changes, plan syncs, and user
flow diagram refreshes must only read existing watchdog evidence or
continuation readiness evidence.
They must not recreate, re-register, start, restart, or re-enable the paired
watchdog automation. On Windows, a visible console flash during ordinary node
advance is treated as a watchdog lifecycle bug or task configuration bug; the
task action should be hidden/noninteractive when a real scheduled task is used.
Use `scripts/register_windows_watchdog_task.ps1` or equivalent configuration
when creating Windows watchdog tasks. Do not register direct interactive
`python.exe` actions that can open a console window; prefer `pythonw.exe` or a
hidden `powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden` wrapper,
and record `hidden_noninteractive: true` in watchdog evidence.

The user-level global supervisor is not owned by any one chat or project, and
it is not a Windows scheduled task. It must be a singleton Codex app cron
automation created or verified through the Codex automation interface, using
`templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md` as the
prompt source and a fixed 30-minute cadence. FlowPilot verifies this
supervisor in the same lifecycle setup that creates or repairs the heartbeat
and paired watchdog. Each heartbeat refreshes this project's global
registration lease before work continues. It first inspects existing Codex cron
automations by id, name, and prompt. If one active singleton exists at the
fixed cadence, reuse it. If exactly one paused singleton exists and the
current route needs global protection, update that existing automation to
`ACTIVE` with the fixed cadence. Create a new automation only when no singleton
exists and at least one project registration is active. With the current Codex
app `automation_update` interface, the creation/update shape is `kind: cron`,
`rrule: FREQ=MINUTELY;INTERVAL=30`, `cwds` as a single workspace string path,
`executionEnvironment: local`, `reasoningEffort: medium`, and `status:
ACTIVE`. The supervisor expires terminal or manually stopped project records,
supersedes old route generations, deduplicates repeated stale events, and
writes both global and local supervisor evidence. A local project unregisters
or ages out only its own record. On pause, stop, or completion, unregister the
project first, stop the project heartbeat/watchdog, then reread the global
registry under the singleton lock; delete the user-level global supervisor
last only when no active, unexpired project registrations remain.

Busy leases are node-scoped work markers, not heartbeats and not completion
evidence. Use them only around bounded operations that may naturally outlive
the heartbeat stale threshold, such as installs, builds, packaging, long test
runs, screenshot capture, or external tool waits. Each lease must include the
route id, node id, operation, `started_at`, and `expires_at` or equivalent
maximum duration. Do not create open-ended leases. Clear the lease when the
operation finishes, or refresh it with a new expiry before the old one expires
if the same bounded operation is still running. A stale, mismatched, expired,
or missing lease must not suppress watchdog reset. A recently cleared matching
lease may suppress reset only during the configured post-busy grace window; an
older cleared lease must not suppress reset.

The main executor owns busy-lease coverage. Before starting a command, tool
run, install, build, packaging job, long test, screenshot/desktop QA batch, or
external wait that may outlive the stale threshold, start a bounded lease or
use `scripts/flowpilot_run_with_busy_lease.py` as the command wrapper. Before
checkpoint, route advancement, pause, or completion, verify that no active
busy lease remains for the current node unless the operation is still running
and explicitly refreshed with a new expiry.

## Quality Package

FlowPilot keeps the main route simple by reusing one quality package instead of
adding separate stations for feature richness, standard raises, child-skill
visibility, and validation.

At each parent/module or leaf-node entry, use this sequence:

```text
enter parent or node -> focused grill-me -> quality package
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

## `.flowpilot/` Source Of Truth

Canonical state is machine-readable:

- `state.json`: current route, node, status, heartbeat, checkpoint, next action.
- `execution_frontier.json`: route version, active node, current mainline, next
  jump, fallback, current-node completion guard, latest PM completion runway,
  checks before advance, and visible Codex plan projection. For terminal
  states it also records the final heartbeat/watchdog lifecycle snapshot so
  stale `active: true` values cannot survive after closure.
- `startup_review/latest.json`: the human-like reviewer's factual startup
  report. It must cite direct fact checks rather than worker assertions.
- `startup_pm_gate/latest.json`: the project manager's startup decision. This
  is the only startup opening record that may set
  `work_beyond_startup_allowed: true`.
- `mode.json`: selected run mode and hard-gate policy.
- `contract.md`: frozen acceptance contract and explicit later approvals.
- `capabilities.json`: required and conditional capability gates.
- `routes/<route-id>/flow.json`: route nodes, transitions, gates, invariants.
- `routes/<route-id>/flow.md`: human-readable summary derived from `flow.json`.
- `routes/<route-id>/nodes/<node-id>/node.json`: chunk intent and verification.
- `heartbeats/*.json`: current position, decision, and next chunk.
- `watchdog/latest.json` and `watchdog/events*.json*`: external stale-heartbeat
  checks, global-record linkage, automation reset attempts, or explicit
  `not_created` evidence when the host does not support real wakeups.
- user-level `$CODEX_HOME/flowpilot/watchdog` or `$FLOWPILOT_GLOBAL_RECORD_DIR`:
  global watchdog registry, compact project events, and singleton supervisor
  writeback when automated continuation is supported.
- scheduled continuation record: host wakeup/automation probe result,
  automated continuation evidence when supported, or `manual-resume` fallback
  evidence when unsupported.
- `checkpoints/*.json`: verified milestone evidence.
- `inspections/*.json` or node-local inspection evidence: human-like review
  context, experiments, findings, blocking issues, repair targets, and
  same-inspector recheck results.
- `experiments/*/experiment.json`: bounded experiment evidence.
- `task-models/`: task-local development-process and product-function
  FlowGuard models when the route or delivered behavior needs model-first
  validation.

Markdown files are review views. JSON and executable model files are the source
of truth.

## Real Heartbeat Continuation

Heartbeat JSON is not enough to claim unattended continuation for a formal
long-horizon FlowPilot route. Before creating heartbeat, watchdog, or global
supervisor automation, probe the host environment for real reminders,
monitors, wakeups, cron jobs, or automation tools. Record the probe result in
`.flowpilot/heartbeats/` or equivalent route evidence.

If the host supports real continuation, create or update the automated
continuation bundle before long-running work starts: stable heartbeat launcher,
paired external watchdog, and singleton global watchdog supervisor. Record the
continuation ID, cadence, next wakeup condition, watchdog/global-supervisor
evidence, and fallback.

If the host does not support real continuation, record `manual-resume` mode and
do not create heartbeat, watchdog, or global-supervisor automation. The route
continues to use `.flowpilot/` state, PM runways, checkpoints, FlowGuard
models, and evidence, but it must not claim unattended recovery or stale
heartbeat reset capability.

In Codex Desktop, use the available automation/update capability when the user
requests heartbeat continuation or the formal route depends on long-running
autopilot. Prefer a cadence that checks after the previous chunk is no longer
running, such as a short wakeup interval when supported by the host. Do not
interrupt active work only to satisfy a heartbeat tick.

The heartbeat automation should be a stable launcher when it exists: it tells
FlowPilot to load the current `.flowpilot` state, active route, execution
frontier, watchdog evidence, lifecycle evidence, crew ledger, role memory
packets, and latest heartbeat. It then rehydrates the six-agent crew by
resuming or replacing roles from memory and asks the project manager for the
latest completion-oriented runway. Route changes,
next-node changes, PM runway changes, and Codex plan changes are written to
persisted files, not embedded into a freshly rewritten heartbeat prompt. The
paired watchdog and singleton global supervisor follow the same stability
rule: once the lifecycle policy and automation pairing are recorded,
checkpoints and node transitions preserve that lifecycle state instead of
re-entering watchdog setup.

Stable heartbeat or manual resume does not mean passive status reporting. When
the loaded frontier says the current node is unfinished, the first work unit is
the project-manager-selected persisted `current_subnode` or `next_gate`, not the
future `next_node`, but the PM decision must still be a long runway toward
completion. The heartbeat or manual-resume turn must restore/load the crew,
ask the project manager for that runway, sync it into the visible plan, verify
the selected gate's authority record, execute at least one bounded gate when
possible, then keep advancing through downstream runway steps until a PM stop
signal, hard gate, blocker, route mutation, or real environment/tool limit
stops progress. If a gate requires a role-specific approver, the main executor
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
  frozen contract and capability manifest;
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
- if the host supports real wakeups, the all-or-none automated continuation
  bundle before route execution: stable one-minute route heartbeat schedule
  (`FREQ=MINUTELY;INTERVAL=1`), paired external watchdog, singleton global
  watchdog supervisor at the fixed 30-minute cadence, and
  hidden/noninteractive watchdog execution evidence when a Windows task or
  external task is used;
- if the host does not support real wakeups, `manual-resume` evidence before
  route execution and no heartbeat/watchdog/global-supervisor automation
  created;
- PM-owned startup opening from a clean factual reviewer report before child
  skills, imagegen, implementation, formal route chunks, or completion work;
- FlowGuard process design before route execution.
- candidate route-tree generation and root FlowGuard freeze before `route v1`;
- strict gate-obligation review model before reviewer-closable gates advance;
- parent-subtree FlowGuard review before entering child nodes.

Conditional UI gates:

- detect that the route has a user-facing UI or visual-delivery surface;
- invoke `concept-led-ui-redesign` through the child-skill fidelity gate when
  concept-led visual work is in scope;
- invoke `frontend-design` through the child-skill fidelity gate when product UI
  polish, layout, responsiveness, accessibility, or implementation guidance is
  in scope;
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
- after rendered screenshot QA, record a rendered-UI aesthetic verdict and
  concrete reasons before divergence closure. A visually weak implementation
  cannot be closed only because screenshots exist or tests pass;
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
-> main-agent merge and verification
-> worker returns to idle crew slot
```

Run the sidecar scan at child-node entry, not as a parent/module gate.
Worker agents handle bounded helper tasks inside the current child node. They
must not own the child node, route advancement, frozen acceptance floor,
checkpoint, or completion decision. The project manager may assign bounded
sidecar work, but the main executor still merges and verifies the result before
dependent work proceeds.

Reuse worker A or worker B before spawning or replacing capacity. Spawn or
replace only when no fixed worker slot is available or recoverable and the
sidecar task is worth the coordination cost.

Worker returned is not complete. The main executor must merge, verify, and ask
the project manager whether the current node can proceed.

## Final Route-Wide Gate Ledger

Before terminal completion, the project manager must rebuild
`.flowpilot/final_route_wide_gate_ledger.json` from the current route and
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
- generated-resource lineage for concept images, product-facing visual assets,
  screenshots, route diagrams, model reports, and other generated artifacts,
  with each item marked consumed, included in final output, used as evidence,
  superseded, quarantined, or intentionally discarded with reason;
- stale, invalidated, missing, waived, blocked, and unresolved evidence;
- `unresolved_count`.

Completion is blocked unless the PM ledger is built from the current route,
`unresolved_count` is zero, the human-like reviewer performs a backward check
from the final product through that PM-built ledger, and the project manager
records a ledger-specific completion approval. If the ledger finds a missing,
stale, blocked, or wrongly superseded item, the project manager decides repair,
route mutation, explicit waiver by the correct role, or PM stop; after repair
or mutation, the ledger is rebuilt from scratch and replayed again.

## Chunk Rule

No formal chunk starts without:

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

- intent;
- owned paths or owned responsibility;
- expected artifacts;
- verification commands or manual checks;
- allowed exits;
- recovery route if verification fails.
- anti-rough-finish checkpoint review before the node is marked complete.
- human-like product inspection before checkpoint, with repair route mutation
  and same-inspector recheck for any blocking issue.
- composite backward review before any non-leaf parent/module/group is marked
  complete, including child-evidence replay, parent product-model comparison,
  human-like parent review, and a structural route mutation if the children do
  not compose into the parent goal.

If the next step is uncertain, run a bounded experiment instead of a formal
chunk. Experiments answer one question and either resume the route, update the
route, or block with evidence.

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
affected FlowGuard checks, rewrite `.flowpilot/execution_frontier.json`, sync
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
- sidecar subagent work is merged and verified by the main agent;
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
  every effective node and child-skill gate is accounted for, stale evidence
  and superseded nodes are checked, `unresolved_count` is zero, the
  human-like reviewer has replayed it backward, and the project manager has
  approved the clean ledger;
- final report is written;
- host continuation mode has been reconciled: automated routes stop or delete
  the paired watchdog before automated heartbeat state stops; manual-resume
  routes record that no heartbeat/watchdog/global-supervisor automation was
  created;
- lifecycle reconciliation has scanned Codex automations, global supervisor
  records, Windows scheduled tasks, local state, execution frontier, and
  watchdog evidence;
- the persistent crew ledger and role memory packets are archived with final
  role statuses after lifecycle reconciliation;
- terminal continuation state has been written back to `state.json`,
  `.flowpilot/execution_frontier.json`, lifecycle evidence, heartbeat evidence,
  and watchdog evidence or explicit manual-resume no-automation evidence.

The final response should cite the current route, checkpoints, verification
commands, skipped checks with reasons, and any residual risks. Do not claim a
skipped check passed. If the route is complete, the final response states that
the FlowPilot task is complete. If the route is not complete and this is a
controlled stop, the final response includes the appropriate automated or
manual-resume notice.

## References

- `references/protocol.md`: compact operator protocol.
- `references/installation_contract.md`: dependency and self-check contract.
- `references/failure_modes.md`: failures the FlowGuard models must keep
  guarding against.
- `assets/README.md`: local asset map for templates and model starters.
- `assets/templates/startup_banner.md`: approved startup banner for visible
  FlowPilot launch.
