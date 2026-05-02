# FlowPilot Protocol

FlowPilot is the project controller. FlowGuard is the executable modeling layer
used to design and validate the controller route, capability routing, recovery
branches, heartbeat behavior, and any task-local behavior models.

## Startup

1. Enable FlowPilot by default when invoked or when `.flowpilot/` exists.
2. Create or load `.flowpilot/`.
3. Emit the fenced `FlowPilot` ASCII startup banner in chat before mode
   selection or other heavy startup work.
4. Offer run mode left-to-right from loosest to strictest: `full-auto`,
   `autonomous`, `guided`, `strict-gated`.
5. Record the selected mode, or record why `full-auto` was used as fallback.
6. Commit the showcase-grade long-horizon floor.
7. Run visible full grill-me style self-interrogation. In the same startup
   round, draft the intended floor, seed the improvement candidate pool, seed
   the initial validation direction, and surface product-function questions.
   Do not freeze the contract yet.
8. Create or restore the fixed six-agent crew and write
   `.flowpilot/crew_ledger.json` plus one compact role memory packet under
   `.flowpilot/crew_memory/` for project manager, human-like reviewer, process
   FlowGuard officer, product FlowGuard officer, worker A, and worker B.
9. Ask the project manager to ratify the startup self-interrogation and own
   material understanding, product-function architecture, route,
   heartbeat-resume, repair, and completion decisions from this point forward.
10. Before PM product-function synthesis or route decisions, require the main
    executor to write `.flowpilot/material_intake_packet.json`: inventory,
    source summaries, source authority/freshness/contradiction classification,
    coverage map, and unread or deferred materials.
11. The human-like reviewer approves or blocks material sufficiency. The packet
    is PM-ready only when obvious sources are not missing, large materials are
    sampled or scoped honestly, summaries are specific, contradictions and
    uncertainty are visible, and PM route design would not be misled.
12. The project manager writes `.flowpilot/pm_material_understanding.json` from
    the reviewed packet and user intent. It records source-claim matrix, open
    questions, material complexity (`simple`, `normal`, or `messy/raw`), and
    whether materials require a formal discovery, cleanup, modeling,
    validation, or research subtree before implementation.
13. Require the project manager to write
    `.flowpilot/product_function_architecture.json` before contract freeze.
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
17. Ask the project manager to discover likely child skills from the frozen
    contract and capability manifest, load each likely child skill's
    `SKILL.md` and relevant references, and extract a child-skill gate
    manifest with key stages, required checks, standards, evidence needs,
    skipped references with reasons, visible mini-route milestones, and
    required approver roles.
18. Have the human-like reviewer, process FlowGuard officer, and product
    FlowGuard officer review their slices of the manifest. The project manager
    then approves or blocks manifest inclusion in route modeling, the
    execution frontier, and the PM runway. The main executor, worker A, and
    worker B are forbidden approvers for child-skill gates.
19. Verify FlowGuard and required dependency skills.
20. Inspect dependency/tool needs and write a dependency plan.
21. Install only the minimum dependencies needed for FlowPilot itself and the
    current route/model checks.
22. Defer future route, chunk, or native-build dependencies until the node or
    check that actually needs them.
23. Probe host continuation capability before creating heartbeat, watchdog, or
    global-supervisor automation. Record whether real wakeups are supported,
    unsupported, or blocked.
24. If the host supports real wakeups, create the all-or-none automated
    continuation bundle: stable heartbeat launcher, paired external watchdog,
    and singleton global watchdog supervisor. The launcher loads persisted
    route/frontier state rather than carrying route-specific next-jump
    instructions in its prompt. On wakeup it loads role memory, resumes or
    replaces each role from memory, then asks the project manager for a
    completion-oriented runway from the current position to project completion.
25. If the host does not support real wakeups, record `manual-resume` mode and
    do not create heartbeat, watchdog, or global-supervisor automation.
26. Ask the project manager for the initial route-design decision.
27. Ask the process FlowGuard officer to use FlowGuard as process designer for
    the active route.
28. Generate a candidate route tree from the approved product-function
    architecture, contract, and PM-approved child-skill gate manifest.
29. The process FlowGuard officer authors, runs, interprets, and approves or
    blocks the root development-process model against the candidate tree.
30. The product FlowGuard officer authors, runs, interprets, and approves or
    blocks the root product-function model for the target product or workflow
    behavior, using the approved product-function architecture as a source
    artifact.
31. The matching officers inspect counterexamples for both model scopes and
    write approve/block reports.
32. Freeze the checked candidate as route `flow.json` and generate English
    `flow.md`.
33. Write `.flowpilot/execution_frontier.json` from the checked route, active
    node, current subnode/gate when applicable, next node, current mainline,
    fallback, checks before advance, and the current-node completion guard.
    While a node is unfinished, the frontier must name the concrete
    `current_subnode` or `next_gate` that the next heartbeat should execute.
    It must also name the actor authority for that gate: draft owner,
    execution owner, required approver, forbidden approvers, approval status,
    approval evidence path, and blocked reason if applicable. It also records
    the latest PM completion runway, including downstream steps, hard-stop
    conditions, checkpoint cadence, and any PM stop signal.
34. Sync the visible Codex plan list from the latest PM completion runway,
    replacing the current plan projection while preserving older PM decisions
    and checkpoints as history. If the host exposes a native visible plan/task
    list tool, such as Codex `update_plan`, call that tool immediately with
    the PM runway before executing work. Persisted `.flowpilot` evidence alone
    is not enough when the native tool exists.
35. Emit the visible route map in chat: active route, active node, simulated
    path, next jumps, checks, fallback branches, heartbeat state, and
    acceptance delta.
36. Start the first bounded chunk only after continuation mode is known.
    Automated routes use heartbeat restore; manual-resume routes load the same
    state/frontier/crew-memory inputs in the active turn. In both modes the project
    manager issues a completion-oriented runway, the main executor syncs that
    runway into the visible plan, and continuation health/manual freshness,
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
started.

## Material Intake And PM Handoff

Material intake is a first-class startup gate between PM ratification of
self-interrogation and PM product-function architecture. The main executor
does the descriptive work first: it inventories materials, reads or samples
enough to say what each source is for, records source quality and uncertainty,
and writes `.flowpilot/material_intake_packet.json`.

The human-like reviewer then approves or blocks sufficiency. Approval means the
packet is clear enough for PM planning: obvious sources are not missing, large
sources are scoped honestly, contradictions are visible, and uncertainty is not
hidden. A reviewer block returns to intake; the PM cannot override a current
material sufficiency gap.

After reviewer approval, the project manager writes
`.flowpilot/pm_material_understanding.json`. This is interpretive, not merely a
second inventory: it maps claims to sources, lists open questions, classifies
material complexity, and decides whether the next route can proceed directly or
must insert discovery, cleanup, spreadsheet analysis, data modeling, research,
validation, or reconciliation nodes. Messy/raw materials make material
understanding part of the formal route, not a hidden pre-step.

## Product Function Architecture

The product-function architecture gate is the missing design layer between
startup self-interrogation, reviewed material handoff, and contract freeze. It
is owned by the project manager, not by the main executor, and it must exist
before route generation or implementation.

The canonical artifact is `.flowpilot/product_function_architecture.json`.
It records:

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
be modeled and checked. The human-like reviewer challenges usefulness and
completeness before the contract freezes: unnecessary features, unnecessary
visible text, missing workflow support, bad defaults, failure-state gaps, and
weak user-task coverage. A product-function model later in the route validates
the design; it does not replace this pre-contract PM synthesis gate.

## Actor Authority

FlowPilot's six-agent crew is an authority system, not a decorative report
list. Every formal gate records who may draft it, who executes it, who must
approve it, and who is forbidden to approve it. The main executor can create
draft non-model evidence, run ordinary implementation commands, edit files,
integrate sidecar reports, and enforce hard gates, but cannot self-approve
route, model, inspection, repair, or completion gates. For FlowGuard model
gates, the matching FlowGuard officer must author, run, interpret, and approve
or block the model.

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
child-to-parent closure. The main executor and workers may draft evidence or
implementation output, but their self-approval is invalid.

If a required authority blocks a gate, FlowPilot does not advance on evidence
existence. It records the block, grills the issue when needed, asks the project
manager for repair-strategy interrogation, mutates or blocks the route, and
rewrites the execution frontier. If a required authority is missing on
heartbeat resume, FlowPilot restores or replaces that role before work
continues; if it cannot, the gate blocks rather than falling back to
main-executor self-approval.

The six agents are persistent roles, not guaranteed live processes. Live
subagent continuity is best effort; role continuity is mandatory. The
authoritative recovery state is `.flowpilot/crew_ledger.json` plus compact
role memory packets under `.flowpilot/crew_memory/`. Each role memory packet
stores the role charter, authority boundary, frozen contract pointer, current
route position, latest decisions, open obligations, blockers, evidence paths,
and "do not redo" notes. On heartbeat or manual resume, FlowPilot may try to
resume a stored agent id, but if that fails it must replace the role from the
latest memory packet. A replacement role started only from a generic prompt is
not recovered and cannot approve gates.

Crew identity uses three separate fields. `role_key` is the stable authority
and routing id. `display_name` is the user-facing chat/UI label. `agent_id` is
only a diagnostic/recovery handle and must not be shown as the primary label or
used as the authority key.

## Mode Selection

The mode-selection prompt is the first user-facing startup gate unless the user
already selected a mode. Show modes left-to-right from loosest to strictest:
`full-auto`, `autonomous`, `guided`, `strict-gated`. For new formal routes,
`full-auto` is the default unless the user chooses otherwise. If the host
cannot pause or the user says to continue without choosing, record `full-auto`
as the fallback and continue.

Run modes change autonomy and gate behavior, not quality tier. Every formal
FlowPilot mode keeps the same showcase-grade completion floor.

## Self-Interrogation And Heartbeat

Startup self-interrogation must be visible in chat and persisted as structured
evidence. FlowPilot uses three depths instead of repeating a full grill-me at
every scope:

- full grill-me at formal boundaries: startup, route mutation or standard
  expansion, and completion review;
- focused grill-me at bounded boundaries: phase, group, module, leaf node, and
  child-skill entry;
- lightweight self-check at heartbeat micro-steps and tiny reversible choices.

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
the next chunk. Each heartbeat micro-step should run a lightweight self-check
before execution when it starts new work.

Until the desktop Cockpit is available, chat is the temporary cockpit. At
startup, every route update, and each node or heartbeat transition that begins
new work, emit a visible route map with the active route/node, simulated path,
PM completion runway, next jumps, checks, fallback exits, heartbeat state, and acceptance delta. Do
not hide route progress only in `.flowpilot/`.

The visible route map is a display of the existing route state, not a new
execution path. Show the current active route and active node as the primary
surface. Keep superseded or paused routes in history with their replacement
reason and checkpoint/failure evidence, but do not mix old routes into the
main current-route map.

When FlowGuard or the current route model can emit Mermaid, FlowPilot opts into
that optional route-map output. `.flowpilot/diagrams/current-route-map.mmd` is
the canonical chat fallback and future UI source. Route mutation invalidates
the old diagram; recheck the route and refresh the Mermaid artifact before
showing it as current progress.

Heartbeat records alone are not enough to claim unattended recovery. FlowPilot
first probes whether the host supports real wakeups or automations. When the
host supports them, FlowPilot creates a real continuation schedule or wakeup,
checks that heartbeat before each node, and repairs it through the official
host interface if it is missing. When the host does not support them, FlowPilot
records `manual-resume` mode and uses `.flowpilot/` state, PM runways, and
checkpoints for handoff/resume without creating heartbeat, watchdog, or
global-supervisor automation.

The real continuation, when available, should be a stable launcher. It tells
FlowPilot to load `state.json`, the active `flow.json`,
`.flowpilot/execution_frontier.json`, `.flowpilot/crew_ledger.json`,
`.flowpilot/crew_memory/`, watchdog evidence, and latest heartbeat. It then
rehydrates the fixed crew by resuming stored agent ids when possible or
replacing unavailable roles from their memory packets, records the rehydration
status, and asks the project manager for the next completion-oriented runway.
Route mutations, next-node changes, PM runway changes, and current-mainline
plan updates are persisted in files and then reflected in chat/plan output;
ordinary route changes should not rewrite the heartbeat automation prompt.
The heartbeat or manual-resume turn also loads the current gate's authority
record. If a gate has draft evidence but lacks the required approver, it
requests that approval or records a blocker; it does not treat the draft as
complete.

The frontier has a current-node completion guard. If
`unfinished_current_node` is true or
`current_node_completion.advance_allowed` is false, the heartbeat or
manual-resume turn resumes `active_node` and treats `next_node` only as a
planned future jump. The jump is legal only after node status, required gates,
declared verification, node evidence, and continuation/checkpoint evidence are
written.

On heartbeat or manual resume, "continue later" is not progress. FlowPilot asks
the project manager for a completion-oriented runway only after the crew memory
rehydration gate passes. It syncs that runway into the visible plan, then loads
the persisted `current_subnode` or `next_gate` for the unfinished active node.
It must execute at least that gate in the current turn when executable, then
continue along the PM runway until a PM stop signal, hard gate, blocker, route
mutation, or real environment/tool limit stops progress. Continuation evidence
must name the PM runway, selected gate, role-memory rehydration result, actions
attempted, results, checkpoint writes, and updated completion guard. It may not
end by only writing a future-facing decision such as "continue to X" while the
gate remains executable.

The visible plan sync is a host-facing control gate. When a native plan tool is
available, the main executor must call it, not only update `.flowpilot` files.
The synced projection must contain the current executable gate and downstream
runway items toward completion; a one-step projection is stale-plan evidence.
If no native plan tool exists, record the fallback projection method and show
the runway in chat, but do not claim that the native Codex plan was synced.

If the host exposes reminders, monitors, wakeups, or automation tools, the
route records the continuation ID, cadence, wakeup condition, watchdog/global
supervisor evidence, and fallback in `.flowpilot/heartbeats/`. If the host
lacks real continuation support, that limitation is recorded as
`manual-resume`; plain heartbeat files do not count as a passed
real-continuation gate for multi-hour formal work.

For long-running routes on hosts with real wakeups, an external watchdog can run outside the Codex thread.
The bundled watchdog reads `.flowpilot/state.json`, the active route, the
latest heartbeat, `.flowpilot/busy_lease.json`, and host automation metadata.
Codex heartbeats do not interrupt an already-running turn, so bounded long
operations that may outlive the stale threshold must write a busy lease before
starting and clear or refresh it afterward. If the heartbeat is stale for N
minutes but a matching non-expired busy lease is active for the current
route/node, the watchdog writes `busy_not_stale` evidence and does not request
a reset. If the busy lease was just cleared, the watchdog writes
`post_busy_grace` and waits a bounded grace window before requesting reset,
because the next heartbeat can only arrive after the active turn yields back
to the host scheduler. The default stale threshold is 10 minutes. The default
grace window is 10x the heartbeat interval;
with a one-minute heartbeat, this is 10 minutes. If the heartbeat is stale and
no valid lease or post-busy grace exists, it writes
`.flowpilot/watchdog/latest.json` and event evidence that FlowPilot must use
the official Codex app automation interface to set the active heartbeat
automation to `PAUSED`, then back to `ACTIVE`. It does not edit
`automation.toml` directly. The reset is a recovery action, not completion
proof; the proof is a later heartbeat with a newer timestamp.

The bundled watchdog also writes a compact user-level global record unless
disabled for an explicit test. The default global directory is
`$CODEX_HOME/flowpilot/watchdog`, or `$FLOWPILOT_GLOBAL_RECORD_DIR` when set.
Project-local `.flowpilot/watchdog/latest.json` remains the source of truth;
the global registry is only an index that lets a user-level supervisor find
projects whose local watchdog evidence needs revalidation.

Watchdog reset decisions trust only `.flowpilot/state.json`, latest heartbeat
evidence, and `.flowpilot/busy_lease.json`. `execution_frontier.json`,
`lifecycle/latest.json`, host automation metadata, and global records are
diagnostic drift signals only. Live subagent busy state is not inspected. Each
watchdog record includes `source_status` with trusted sources, diagnostic
sources, source timestamps, drift warnings, and
`live_subagent_state_used: false`.

Heartbeat, watchdog, and global supervisor evidence are managed as one
lifecycle bundle. Whenever FlowPilot creates or repairs a real heartbeat
continuation, it also creates or verifies the watchdog automation and verifies
a quiet singleton global-supervisor path, then writes lifecycle evidence with
the heartbeat id, watchdog id/task name, active state, and stop order. If no
quiet singleton exists, FlowPilot records setup-required/on-demand supervisor
evidence instead of silently creating cron. Legacy cron requires explicit user
opt-in. When an automated route reaches `complete` or terminal shutdown,
FlowPilot stops or deletes the watchdog first and records
`stopped_before_heartbeat`, then writes the inactive lifecycle snapshot back to
`state.json`, `.flowpilot/execution_frontier.json`, lifecycle evidence, and
watchdog evidence before stopping the heartbeat automation. Manual-resume
routes record that no heartbeat/watchdog/global-supervisor automation exists
to stop.
Pause, restart, and terminal closure all use the same lifecycle reconciliation
gate: scan Codex app automations, the global supervisor/registry, Windows
scheduled tasks, `.flowpilot/state.json`, `.flowpilot/execution_frontier.json`,
and latest watchdog evidence before writing a new lifecycle state. Disabled
Windows FlowPilot scheduled tasks are still residual objects unless they are
unregistered or explicitly waived. Use `scripts/flowpilot_lifecycle.py` for
the read-only inventory; use the official Codex app automation interface for
Codex automation changes.
This pairing is lifecycle state. Ordinary checkpoint writes, node transitions,
route-map refreshes, and visible plan syncs must only read existing watchdog
evidence and must not recreate, re-register, start, restart, or re-enable the
watchdog automation. A visible Windows console window during normal node
advance indicates a lifecycle reset or task configuration bug; real scheduled
tasks should run hidden/noninteractively. Prefer
`scripts/register_windows_watchdog_task.ps1` or equivalent setup, using
`pythonw.exe` when available or a hidden `powershell.exe -NoProfile
-NonInteractive -WindowStyle Hidden` wrapper. The watchdog evidence should
record `hidden_noninteractive: true` and `visible_window_risk: false`.

The user-level global supervisor is singleton Codex-side infrastructure, not a
Windows scheduled task, and exists only when the host supports Codex
automation. Create or verify it through the Codex app automation interface
using `templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md` as
the prompt source. Default to a quiet thread-bound `heartbeat` singleton so
repeated checks stay in one thread. Startup first inspects existing Codex
automations by id, kind, name, and prompt. Reuse one active quiet singleton; if
an active legacy `cron` singleton exists, pause or replace it when conversation
hygiene matters. If no quiet singleton exists, record setup-required/on-demand
evidence. Create or reactivate a legacy cron only after explicit user opt-in
that accepts new-conversation noise. The supervisor reads the global registry,
rereads the project-local state and watchdog evidence, expires terminal or
manually stopped routes, supersedes old route generations, deduplicates
repeated stale events, and only then uses the official Codex app automation
interface to reset the project heartbeat automation. A local route, project, or
chat may unregister its own
project record, but must not disable or delete the user-level global
supervisor.

Busy leases are node-scoped work markers, not heartbeat or completion records.
They must include route id, node id, operation, start time, and a bounded
expiry. Recently cleared matching leases suppress reset only during the
post-busy grace window. Missing, expired, old-cleared, mismatched, or malformed
leases do not suppress a watchdog reset requirement.

The main executor must start a bounded lease, or use
`scripts/flowpilot_run_with_busy_lease.py`, around commands and waits that may
outlive the stale threshold. Before checkpoint, route advancement, pause, or
completion, it verifies that no active lease remains unless the same bounded
operation is still running and refreshed with a new expiry.

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
approves or blocks product model coverage. The main executor may provide
context and receive the report, but it must not author or run FlowGuard model
files on the officer's behalf. If an officer blocks, the route follows the
same repair/mutation path as a human-like inspection block.

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

Every non-leaf parent/module/group also has a V-model style backward review
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
No formal chunk may start until host continuation mode is known, automated
heartbeat health or manual-resume freshness has been checked, focused
parent-scope grill-me, parent-subtree FlowGuard review, focused node-level
grill-me, and the lightweight continuation self-check are complete. No formal
chunk may start until the active route map and current node roadmap have been
shown in chat.
No formal chunk may start until `.flowpilot/execution_frontier.json` matches
the active route version and the visible Codex plan has been synced from that
frontier.
No next-node jump may occur while the frontier current-node completion guard
still says the active node is unfinished.

No formal chunk may start until the current parent subtree has been reviewed by
FlowGuard and any unfinished-current-node recovery check confirms that the
route is not skipping an incomplete leaf. If the current node was interrupted
before validation and evidence, the next heartbeat resumes that node instead of
advancing.
No formal chunk may start until the current parent product-function model and
active leaf product-function model have been checked.

Before formal execution, run the reusable quality package:

```text
enter parent or node -> focused grill-me -> quality package
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

Before closing any non-leaf checkpoint, run composite backward review. Replay
child evidence against the parent product model, inspect whether the children
compose into the parent goal, and mutate the route if the repair requires an
existing-child rework, an adjacent sibling child, a child-subtree rebuild, or
parent impact bubbling.

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
hard input to the route. The project manager must read the child skill, map
its workflow and completion standard into the current gates, write an evidence
checklist, assign required approvers, and complete or explicitly justify each
required step.

This is stricter than a prompt reminder. The route should not continue into
implementation or completion until the child-skill contract is loaded, its
requirements are mapped, the PM-owned gate manifest exists, approver roles are
assigned, the evidence plan exists, and final evidence shows the child skill's
own completion standard was met or explicitly waived by the correct role.
FlowPilot must also project key child-skill milestones into the visible route
as a mini-route, without copying the child skill's detailed prompt text.

FlowPilot must not compress child skills into vague shortcuts. For example,
`concept-led-ui-redesign` means the concept-led workflow and comparison loop;
`model-first-function-flow` means the real FlowGuard applicability decision,
model, checks, counterexample review, and adoption note where required.

Child-skill use has its own conformance loop:

```text
select skill -> load instructions -> extract PM gate manifest
-> assign required approvers -> map workflow -> write evidence checklist
-> show child-skill mini-route -> model/check conformance
-> execute child workflow -> collect evidence -> audit evidence/output match
-> domain-quality review -> strict obligation classification
-> iteration closure -> assigned role approvals -> verify child completion
-> resume parent node
```

For UI skills, the visible mini-route should stay at milestone level, such as
`concept target -> implementation -> screenshot QA -> divergence review ->
iteration closure`. The UI child skills own the visual execution details.

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
- `concept-led-ui-redesign` was invoked when concept-led visual work is in
  scope;
- `frontend-design` was invoked when product UI polish or implementation
  guidance is in scope;
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
- rendered QA evidence includes a rendered-UI aesthetic verdict with concrete
  reviewer reasons before divergence or loop closure;
- material concept/implementation differences have a child-skill loop-closure
  decision;
- product-facing visual assets, when created, are included in the same UI
  child-skill evidence;
- product-facing visual assets include an aesthetic verdict with concrete
  reviewer reasons before UI or package completion;
- post-implementation screenshots are not relabeled as pre-implementation
  concept evidence unless the child skill or user explicitly waived the concept
  target.

## Final Route-Wide Gate Ledger

Before terminal completion, the project manager rebuilds
`.flowpilot/final_route_wide_gate_ledger.json` from the current active route,
not from the initial plan. The ledger is dynamic: it reads `state.json`,
`execution_frontier.json`, the active `flow.json`, capability evidence, node
reports, repair records, child-skill manifests, reviewer reports, model
reports, waivers, and superseded-node history.

The ledger must resolve:

- which route version is current;
- which nodes and gates are effective after route mutation;
- which nodes or gates are superseded, and why;
- every child-skill gate and child-skill completion standard still relevant to
  the current route;
- every human-like inspection, parent backward review, strict-obligation, and
  same-inspector recheck gate;
- every product-function and development-process model gate;
- stale, invalidated, missing, waived, blocked, and unresolved evidence.

The final human-like reviewer then checks the delivered product backward
through the PM-built ledger. PM completion approval is valid only after that
reviewer replay passes and the ledger's `unresolved_count` is zero. If any
entry is missing, stale, blocked, unapproved, or wrongly superseded, the PM
chooses repair, route mutation, correct-role waiver, or PM stop. After repair
or route mutation, the final ledger is rebuilt and replayed again before
completion can continue.

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
- every non-leaf parent/module/group has composite backward review evidence,
  including structural route mutation and rerun evidence for any failed parent
  rollup;
- final product-function model replay and final human-like inspection passed;
- final feature matrix, acceptance matrix, and quality-candidate reviews
  completed;
- completion self-interrogation found no obvious high-value work remaining;
- PM-owned final route-wide gate ledger rebuilt from the current route, with
  effective nodes resolved, child-skill gates collected, stale evidence
  checked, superseded nodes explained, zero unresolved items, human-like
  backward replay passed, and PM ledger approval recorded;
- host continuation mode reconciled: paired watchdog stopped or deleted before
  heartbeat shutdown when automated continuation was used, or manual-resume
  no-automation evidence written when unsupported;
- lifecycle reconciliation scanned Codex automations, global supervisor
  records, Windows scheduled tasks, local state, frontier, and watchdog
  evidence;
- terminal continuation lifecycle state written back to local
  state/frontier/lifecycle/heartbeat/watchdog or manual-resume evidence;
- crew ledger and role memory packets archived with final role statuses;
- completion report emitted.
