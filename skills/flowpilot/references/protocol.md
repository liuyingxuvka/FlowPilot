# FlowPilot Protocol Reference

This reference is the compact operator protocol for the `flowpilot` skill. The
long-form public explanation lives in `docs/protocol.md`.

## Startup

1. Enable FlowPilot by default when invoked or when `.flowpilot/` exists.
2. Create or load `.flowpilot/`.
3. Emit the fenced `FlowPilot` ASCII startup banner in chat before mode
   selection or other heavy startup work.
4. Offer run mode left-to-right from loosest to strictest: `full-auto`,
   `autonomous`, `guided`, `strict-gated`.
5. Record the selected mode, or record why `full-auto` was used as fallback.
6. Commit the showcase-grade long-horizon floor.
7. Run visible full grill-me before freezing the contract. In the same round,
   draft the intended floor, seed the improvement candidate pool, seed the
   initial validation direction, and surface product-function questions. Do
   not freeze the contract yet.
8. Create or restore the fixed six-agent crew and write
   `.flowpilot/crew_ledger.json` plus one compact role memory packet under
   `.flowpilot/crew_memory/` for project manager, human-like reviewer, process
   FlowGuard officer, product FlowGuard officer, worker A, and worker B. Each
   role record separates `role_key` for authority/routing, `display_name` for
   chat/UI labels, and diagnostic-only `agent_id` for best-effort resume.
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
    `.flowpilot/product_function_architecture.json` before contract freeze:
    user-task map, product capability map, feature necessity decisions,
    display rationale, missing high-value feature review, negative scope, and
    functional acceptance matrix.
14. Have the product FlowGuard officer approve or block modelability and
    product-function coverage, and have the human-like reviewer challenge
    usefulness, unnecessary display, missing workflow support, bad defaults,
    and failure-state gaps. If either blocks, the project manager revises the
    architecture before the route continues.
15. Freeze the acceptance contract as a floor in `.flowpilot/contract.md` from
    the approved product-function architecture and startup interrogation.
16. Write the capabilities manifest, including material handoff and
    product-function architecture evidence.
17. Ask the project manager to discover likely child skills, load each likely
    child skill's `SKILL.md` and relevant references, and extract a
    child-skill gate manifest with key stages, required checks, standards,
    evidence needs, skipped-reference reasons, visible mini-route milestones,
    and required approver roles.
18. Have the human-like reviewer, process FlowGuard officer, and product
    FlowGuard officer review their slices of the manifest. The project manager
    then approves or blocks manifest inclusion in route modeling, the
    execution frontier, and the PM runway. The main executor and workers are
    forbidden approvers for child-skill gates.
19. Verify the real `flowguard` package and required skills.
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
    replaces each role from that memory, then asks the project manager for a
    completion-oriented runway from the current position to project
    completion.
25. If the host does not support real wakeups, record `manual-resume` mode and
    do not create heartbeat, watchdog, or global-supervisor automation.
26. Record the controlled-stop notice policy: completed routes emit a
    completion notice; controlled nonterminal stops emit a resume notice that
    says whether to wait for heartbeat or type `continue FlowPilot`.
27. Ask the project manager for the initial route-design decision.
28. Ask the process FlowGuard officer to use FlowGuard as process designer for
    the active route.
29. Generate a candidate route tree from the approved product-function
    architecture, contract, and PM-approved child-skill gate manifest.
30. The process FlowGuard officer authors, runs, interprets, and approves or
    blocks the root development-process model against the candidate tree.
31. The product FlowGuard officer authors, runs, interprets, and approves or
    blocks the root product-function model for the target product or workflow
    behavior, using the approved product-function architecture as a source
    artifact.
32. The matching officers inspect failures for both model scopes and write
    approve/block reports.
33. Freeze the checked candidate as the active route JSON and write derived
    Markdown summary.
34. Write `.flowpilot/execution_frontier.json` from the checked route, active
    node, next node, current mainline, fallback, checks before advance, and the
    current-node completion guard. Include actor authority for the current
    gate: draft owner, execution owner, required approver, forbidden
    approvers, approval status, and approval evidence path. Also record the
    latest PM completion runway, including downstream steps, hard-stop
    conditions, checkpoint cadence, and any PM stop signal.
35. Sync the visible Codex plan list from the latest PM completion runway,
    replacing the current plan projection while preserving old decisions and
    checkpoints as history. If the host exposes a native visible plan/task
    list tool, such as Codex `update_plan`, call that tool immediately with
    the PM runway before executing work. Persisted `.flowpilot` evidence alone
    is not enough when the native tool exists.
36. Emit the user flow diagram in chat when this is startup, a key node change,
    route mutation, completion review, or user request. Include active route,
    active node, next jumps, checks, fallback branches, continuation state, and
    acceptance delta as nearby text.
37. Run the startup activation guard before any child-skill execution, image
    generation, implementation, formal route chunk, or completion work:

    ```powershell
    python scripts/flowpilot_startup_guard.py --root . --route-id <active-route> --record-pass --json
    ```

    The guard must verify matching active route, canonical state,
    execution frontier, current six-role crew ledger, current role memory,
    continuation readiness, and `startup_activation` records in state and
    frontier. Work beyond startup is illegal until the guard records
    `work_beyond_startup_allowed: true`. A route-local file without matching
    canonical state/frontier/crew/continuation evidence is a shadow route and
    must be quarantined or superseded before continuing.
38. Start only the first chunk whose continuation mode is known. Automated
    routes use heartbeat restore; manual-resume routes load the same
    state/frontier/crew-memory inputs in the active turn. In both modes the
    project manager issues a completion-oriented runway, the main executor syncs that
    runway into the visible plan, and focused parent grill-me, parent-subtree
    review, unfinished-current-node recovery check, focused node grill-me,
    lightweight self-check, quality package, child-skill gates when needed,
    dual-layer product/process gates, human-like inspection gates, and
    verification have been defined.

## Material Intake And PM Handoff

Before PM product-function architecture, contract freeze, route generation, or
capability routing, the main executor writes
`.flowpilot/material_intake_packet.json`. It inventories user-provided and
repository-local materials, summarizes what each source appears to contain,
classifies authority, freshness, completeness, contradictions, privacy/safety
notes, maps coverage to user intent, and names unread or deferred materials.

The human-like reviewer approves material sufficiency before the project
manager uses the packet. The reviewer blocks if obvious sources are missing,
large sources are not scoped honestly, summaries are shallow, contradictions or
uncertainty are hidden, or the packet would mislead route design.

The project manager then writes `.flowpilot/pm_material_understanding.json`.
It is an interpretive handoff: source-claim matrix, open questions, material
complexity (`simple`, `normal`, or `messy/raw`), route consequence, and whether
formal discovery, cleanup, modeling, validation, research, or reconciliation
nodes are required before implementation. Messy/raw materials cannot feed a
route decision directly without that discovery decision.

## Product Function Architecture Gate

After the material handoff and before contract freeze, the project manager
writes `.flowpilot/product_function_architecture.json`. Required contents:

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
coverage. The human-like reviewer challenges usefulness, unnecessary display,
missing workflow support, bad defaults, weak failure states, and user-task
gaps. Contract freeze, route generation, capability routing, and
implementation are blocked until both review slices are resolved.

## Execution Loop

Repeat until complete or blocked:

1. Load `state.json`, `.flowpilot/execution_frontier.json`,
   `.flowpilot/crew_ledger.json`, `.flowpilot/crew_memory/`, active route,
   active node, continuation mode, last heartbeat or manual-resume record,
   watchdog evidence when present, lifecycle evidence, and last checkpoint.
2. Rehydrate the six-agent crew before PM runway work. Try to resume stored
   agent ids when the host supports it; otherwise replace unavailable roles
   from the latest role memory packet. Record resumed, replaced, seeded,
   blocked, and unavailable roles. Live subagent continuity is best effort;
   role continuity through persisted memory is mandatory.
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
   approval, request that approval or block; do not let the main executor
   self-approve.
6. Confirm no hard gate, issue branch, or unmerged sidecar worker work is open.
7. Confirm automated heartbeat health when supported, or manual-resume
   state/checkpoint freshness when unsupported, then confirm
   unfinished-current-node recovery state.
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
Every round records its tier, scope id, question count, and evidence. Until
the Cockpit UI is available, chat is the temporary cockpit and must show user
flow diagrams, next jumps, checks, fallback exits, continuation state, and
acceptance delta.
Formal startup, route mutation, and completion self-interrogation evidence is
only draft evidence until the project manager ratifies the scope, layer
coverage, count, and decision set. The project manager's ratification path is
stored in the frontier authority record.

The user flow diagram is the single display view over canonical `.flowpilot`
state, not an alternate execution path. Chat and Cockpit UI render the same
6-8 stage graph from `.flowpilot/diagrams/user-flow-diagram.mmd`, with the
current stage highlighted and active route/node named nearby. Superseded or
paused routes stay in history with replacement reasons and checkpoint/failure
evidence.

Raw FlowGuard Mermaid exports are diagnostic only. They are disabled by
default and generated only on explicit request. Route mutation invalidates the
old user flow diagram; recheck the route and refresh the artifact before
showing it as current progress.

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
not create heartbeat, watchdog, or global-supervisor automation.

Every meaningful route scope has two FlowGuard scopes: the
development-process model and the product-function model. The process model
checks how FlowPilot completes the node; the product model checks how the
product, workflow, UI, backend behavior, data, or user-visible result should
behave. A process-only pass is not enough for implementation, checkpoint, or
completion.

Model execution is role-specific. The process FlowGuard officer authors, runs,
interprets, and approves or blocks process-model coverage. The product
FlowGuard officer authors, runs, interprets, and approves or blocks
product-model coverage. The main executor may provide context and receive the
report, but it must not author or run FlowGuard model files for the officers.
Passing command output without the matching officer's ownership and approval
is a draft, not a completed gate.

PM-initiated FlowGuard modeling is a decision-support move, not a vague
handoff. When the project manager cannot confidently choose a route, repair,
feature, target-object hypothesis, file/protocol structure, or validation path
from existing evidence, the PM may write a structured modeling request and
assign it to the process FlowGuard officer, the product FlowGuard officer, or
both. The request names the decision, uncertainty, evidence, candidate options
or option-generation need, assigned officer scope, and required answer shape.
The officer first checks modelability. Missing evidence becomes an
evidence-collection node; an over-broad question becomes split modeling
requests. A valid report includes coverage, blindspots, failure paths,
recommendation, confidence, next smallest executable action, and route mutation
candidate. The PM synthesizes the report and records the route decision.

Human-like inspection is a route mechanism, not a comment. Inspectors load the
contract, route, product model, child-skill evidence, screenshots/logs/output,
and parent context; then they operate or inspect the product like a real
reviewer. Blocking issues must be made specific through inspector grilling and
must mutate the route into repair work. A repair closes only after repair
process/product models, repair evidence, and same-inspector recheck pass.
Human-like inspection is reviewer-owned: the main executor cannot substitute a
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

Every non-leaf parent/module/group must also run a composite backward review
before it closes. Child-local passes are inputs, not sufficient closure
evidence. The parent review reloads the child evidence, replays it against the
parent product-function model, inspects whether the children compose into the
parent goal, and either passes or mutates the route. Failure strategies are:
return to an affected existing child, insert an adjacent sibling child, rebuild
the child subtree, or bubble the impact to the next parent when the parent
contract changed. The affected evidence and parent rollups become stale until
the changed child/subtree passes and the same parent backward review reruns.

Pause, restart, and terminal closure use a unified lifecycle reconciliation
gate. Before claiming any of those states, FlowPilot scans Codex app
automations, the user-level global supervisor/registry, Windows scheduled
tasks, `.flowpilot/state.json`, `.flowpilot/execution_frontier.json`, and
latest watchdog evidence. Disabled Windows FlowPilot scheduled tasks are still
residual lifecycle objects unless they are unregistered or explicitly waived.
`scripts/flowpilot_lifecycle.py` provides a read-only inventory and required
action list; actual Codex automation changes still use the official Codex app
automation interface.

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

When host automation appears active but heartbeat evidence stops advancing,
FlowPilot may use `scripts/flowpilot_watchdog.py` or an equivalent external
watchdog. The watchdog checks `.flowpilot/state.json`, the active route
heartbeat id, `.flowpilot/busy_lease.json`, and host automation metadata.
Because host heartbeats do not interrupt an already-running Codex turn,
bounded long operations must create a route/node-matched busy lease before
starting and clear or refresh it afterward. If the latest heartbeat is older
than the configured N-minute threshold but the lease is active, matching, and
non-expired, the watchdog records `busy_not_stale` and does not request reset.
If the lease was just cleared, the watchdog records `post_busy_grace` and
waits a bounded grace window before requesting reset, because the next
heartbeat can only arrive after the active turn yields back to the host
scheduler. Default the grace window to 10x the heartbeat interval unless route
evidence records a different value. Default the stale threshold to 10 minutes.
If no valid lease or post-busy grace exists, it writes `.flowpilot/watchdog/`
evidence requiring FlowPilot to call the official Codex app automation
interface and set the active heartbeat automation to `PAUSED`, then back to
`ACTIVE`. The watchdog does not mutate `automation.toml` directly. A later
heartbeat proves whether the reset worked.

The watchdog also writes a compact user-level global record by default. Use
`$FLOWPILOT_GLOBAL_RECORD_DIR` to override the directory; otherwise it uses
`$CODEX_HOME/flowpilot/watchdog`. The project-local watchdog evidence is still
authoritative. The global registry is an index that a singleton supervisor
uses to find projects whose local evidence must be reread before any reset is
requested.

Watchdog reset decisions trust only `.flowpilot/state.json`, latest heartbeat
evidence, and `.flowpilot/busy_lease.json`. `execution_frontier.json`,
`lifecycle/latest.json`, host automation metadata, and global records are
diagnostic drift signals only. Live subagent busy state is not inspected. Each
watchdog record includes `source_status` with trusted sources, diagnostic
sources, source timestamps, drift warnings, and
`live_subagent_state_used: false`.

Heartbeat, watchdog, and global supervisor are an all-or-none lifecycle bundle
when the host supports real continuation. Creating or repairing a real
heartbeat continuation for a formal long-running route also creates or verifies
the external watchdog automation, verifies the singleton global supervisor,
and records the pairing. If any piece cannot be created, roll back to
`manual-resume` before route execution or record a concrete blocker. On
terminal closure for automated routes, first write terminal/inactive route
state and unregister this project's global supervisor registration lease. Then
disable or delete the project watchdog automation, write that evidence, write
the inactive lifecycle snapshot back to `state.json`,
`.flowpilot/execution_frontier.json`, and watchdog evidence, and only then
disable or delete the heartbeat automation. Delete the user-level global
supervisor last only after a locked registry reread confirms no active,
unexpired registrations remain. For manual-resume routes, record that no
heartbeat/watchdog/global-supervisor automation exists to stop.
This lifecycle policy is not node-local. Ordinary checkpoints, node
transitions, user-flow-diagram refreshes, and Codex plan syncs must preserve the
recorded watchdog policy and automation pairing; they may read watchdog
evidence but must not recreate, re-register, start, restart, or re-enable the
paired watchdog automation.
For Windows Task Scheduler watchdogs, the pairing also includes
hidden/noninteractive execution evidence. Use the bundled
`scripts/register_windows_watchdog_task.ps1` or an equivalent task definition
that avoids direct visible `python.exe` console actions, and record
`hidden_noninteractive: true` plus `visible_window_risk: false`.

The user-level global supervisor is singleton Codex automation infrastructure,
not a Windows scheduled task, and exists only for hosts that support Codex
automation. Create or verify it through the Codex app automation interface using
`templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md` as the
prompt source and a fixed 30-minute cadence. This verification happens in
the same lifecycle setup that creates or repairs the heartbeat and paired
watchdog. Each heartbeat refreshes the current project's global registration
lease. Startup first inspects existing Codex cron automations by id, name, and
prompt. Reuse one active singleton at the fixed cadence; update one paused
singleton to `ACTIVE` when global protection is required; create only when no
singleton exists and at least one project registration is active. The validated
creation shape is `kind: cron`, `rrule: FREQ=MINUTELY;INTERVAL=30`, `cwds` as
one workspace string path, `executionEnvironment: local`, `reasoningEffort:
medium`, and `status: ACTIVE`. A local route or chat unregisters only its own
project record. On pause, stop, or completion, unregister the project first,
stop the project heartbeat/watchdog, then reread the registry under the
singleton lock; delete the user-level global supervisor last only when no
active, unexpired registrations remain. The supervisor must reread local state
and watchdog evidence, expire terminal/manual-stop routes, supersede old route
generations, and dedupe repeated stale events before it records or performs
any reset.

Busy leases are bounded active-work evidence only. They are not completion
proof and must not be open-ended. Recently cleared matching leases suppress
reset only during the post-busy grace window. Missing, expired, old-cleared,
mismatched, or malformed leases do not suppress a reset requirement.

The main executor must start a bounded lease, or use
`scripts/flowpilot_run_with_busy_lease.py`, around commands and waits that may
outlive the stale threshold. Before checkpoint, route advancement, pause, or
completion, it verifies that no active lease remains unless the same bounded
operation is still running and refreshed with a new expiry.

## Capability Gates

Required:

- mode choice offered before showcase commitment and self-interrogation;
- visible self-interrogation evidence before contract freeze;
- PM-owned product-function architecture before contract freeze, including
  feature decisions, display rationale, missing-feature review, negative
  scope, product officer modelability approval, and reviewer usefulness
  challenge;
- user flow diagram before route execution and visible node roadmap before
  formal chunks;
- continuation readiness before behavior-bearing work: real heartbeat schedule
  and heartbeat health when supported, or manual-resume packet freshness when
  unsupported;
- execution frontier and visible Codex plan sync before behavior-bearing work;
- FlowGuard dependency, process design, and model checks before
  behavior-bearing work;
- root, parent, leaf, repair, and capability product-function model checks
  whenever those scopes affect delivered behavior;
- PM-owned child-skill gate manifest before route modeling: discover likely
  child skills, read each invoked `source_skill`'s `SKILL.md`, load relevant
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
- quality package before implementation: feature thinness, improvement
  classification, child-skill mini-route visibility, validation strength, and
  rough-finish risk;
- child-skill evidence audit, evidence/output match, domain-quality review,
  iteration-loop closure, and assigned role approvals before the parent route
  node resumes;
- PM-owned final route-wide gate ledger before terminal completion. The PM
  rebuilds it from the current route and execution frontier, resolves effective
  and superseded nodes, collects child-skill, human-review, product-model, and
  process-model gates, resolves generated-resource lineage, checks stale
  evidence, records zero unresolved current obligations, obtains human-like
  backward replay, and then records PM ledger approval;
- strict obligation classification before any reviewer pass: current-gate
  obligations clear, future obligations named, and nonblocking notes separated
  from blockers;
- anti-rough-finish review before checkpoint or completion closure;
- human-like product inspection before checkpoint and final completion, with
  route mutation and same-inspector recheck for blocking issues;
- composite backward review before every non-leaf parent/module/group closure,
  with child-evidence replay, parent product-model comparison, human-like
  parent review, and structural route mutation when child composition fails;
- capability evidence sync before implementation.

Capabilities sourced from child skills may complete only after their own
completion standards are met. A route may not replace a child skill with a
weaker FlowPilot summary, and every skipped child-skill step needs an explicit
reason, waiver, blocker, or task-irrelevance note.

The parent route cannot continue on a claim that a child skill was used. It
needs the mapped child-skill steps, step evidence, output match, domain-quality
decision, iteration closure, assigned role approvals, and completion-standard
verification.

For UI skills, expose only key milestones such as `concept target ->
implementation -> screenshot QA -> divergence review -> iteration closure`.
Do not copy every UI prompt rule into FlowPilot.

Conditional:

- UI routes require child-skill-routed UI evidence, not FlowPilot-authored UI
  design prompts. Invoke `concept-led-ui-redesign` when concept-led visual work
  is in scope and `frontend-design` when product UI polish or implementation
  guidance is in scope.
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
- Sidecar reports require main-agent merge and verification before dependent
  implementation, checkpoint, route advancement, or completion.

## Terminal States

`complete` is allowed only when final verification exists, anti-rough-finish
review passed, feature/acceptance/quality-candidate reviews are complete,
product-function model replay and final human-like inspection passed,
PM-owned final route-wide gate ledger has been rebuilt from the current route,
its generated-resource lineage is resolved, its unresolved count is zero, the
human-like reviewer has replayed it backward, and the PM has approved the clean ledger,
completion self-interrogation finds no obvious high-value work remaining, and
final report evidence exists. Open inspection issues, unrechecked repairs, or
missing same-inspector recheck evidence block completion. For routes with paired
heartbeat/watchdog continuation,
completion closure stops or deletes the watchdog and writes terminal lifecycle
state back to local state/frontier/watchdog evidence before stopping the
heartbeat.
`blocked` is required when a hard gate is denied, the model
cannot be stabilized, experiments are exhausted, or dependencies cannot be
connected.
