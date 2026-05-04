# FlowPilot Meta-Process Preflight Findings

Date: 2026-04-30

## Superseding Note: Heartbeat-Only Continuation

As of 2026-05-03, the active FlowPilot protocol no longer includes the
external stale-heartbeat recovery loop or the user-level supervisor. Historical
sections below document earlier model work, but current source, templates,
runtime helpers, and lifecycle checks use only stable heartbeat continuation
or explicit manual resume.

## 2026-05-04 Follow-Up - PM Research Package Loop

Trigger: the user clarified that FlowPilot should not merely note insufficient
materials. When the project manager finds a material, mechanism, source,
validation, reconciliation, or experiment gap, that gap should become a formal
research/evidence package assigned to a worker, then independently checked by
the human-like reviewer before PM uses the result.

Decision: `use_flowguard`.

Modeled risk:

- product architecture or route design starts while a required material
  research package is unresolved;
- a worker research report directly closes a material gap;
- reviewer approval happens without direct source or experiment-output checks;
- reviewer rework findings are bypassed without worker rework and reviewer
  recheck;
- missing web/browser capability is treated as completed external research.

Protocol and template changes:

- added PM-owned `research_package.template.json`;
- added `research_worker_report.template.json` and
  `research_reviewer_report.template.json`;
- updated material intake, PM material understanding, execution frontier, state,
  node acceptance, experiment, route, schema, and protocol documents to carry
  the research package loop;
- meta and capability models now include labels for PM research-package
  decision, worker report, reviewer direct-source check, reviewer rework,
  worker rework, reviewer recheck, reviewer sufficiency pass, PM absorption or
  route mutation, and material-gap closure.

Validation:

```powershell
python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py
python scripts\check_install.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results:

- meta model states: 539167;
- meta model edges: 559339;
- capability model states: 522749;
- capability model edges: 548209;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0;
- nonterminating components: 0.

## Scope

This preflight modeled the project-control workflow for the planned `flowpilot`
skill before implementing the skill itself.

The model boundary covers:

- acceptance contract freezing;
- route creation and FlowGuard checking;
- Markdown summary synchronization from canonical machine state;
- chunk-level verification before execution;
- checkpoint writing after verified chunks;
- model-gap recovery through route updates;
- implementation failure recovery;
- bounded experiments;
- hard safety gates;
- optional subagent spawn, return, and merge;
- demand-driven dependency planning before route execution;
- child-skill fidelity gates before capability work and completion closure;
- recursive candidate route-tree generation before route freeze;
- root-route FlowGuard checks before canonical `flow.json` route creation;
- parent-subtree FlowGuard review before entering child nodes;
- unfinished-current-node heartbeat recovery before advancing;
- child-skill contract conformance modeling, evidence audit,
  output-matching, domain-quality review, and iteration closure;
- prompt-layer boundary cleanup so FlowPilot keeps orchestration gates while
  child skills own domain execution details;
- UI concept target generation or authoritative design reference capture before
  substantial UI implementation;
- iterative UI concept/rendered-screenshot convergence before UI completion;
- visual asset/app-icon style review when UI routes create product-facing
  imagery;
- tiered self-interrogation: full 100-per-active-layer grill-me at formal
  boundaries, focused 20-50 question grill-me at bounded parent/node/child-skill
  boundaries, and lightweight 5-10 question self-checks at heartbeat
  micro-steps;
- baseline risk-family coverage across acceptance, functional capability,
  data/state, implementation strategy, UI/UX, validation, recovery/heartbeat,
  and delivery/showcase quality;
- visible chat route maps and node roadmaps while Cockpit UI is unavailable;
- visible UI concept target display before implementation;
- completion and blocked terminal states.

## Findings From Simulation

The initial model exposed two real workflow gaps:

1. A high-risk gate could be requested after a formal chunk had already been
   prepared, which allowed a pending safety gate and active chunk state to
   overlap. The model now allows high-risk gates only when no chunk is active.

2. Completion was possible after a subagent returned but before the main agent
   merged and verified the result. The completion gate now rejects both
   `pending` and `returned` subagent states.

## Final Check Result

`python simulations/run_meta_checks.py` passed.

Current explored graph after the tiered grill-me policy revision:

- states: 5239
- edges: 5836
- invariant failures: 0
- missing required labels: 0
- progress findings: 0
- stuck states: 0
- non-terminating components: 0

## Global Reset Supervisor Singleton Simulation

Date: 2026-05-01

The user identified an additional global heartbeat design risk: multiple
projects, FlowPilot routes, or heartbeat-skill users must not create multiple
global reset checkers, and no individual chat or project route should be able
to shut down the user-level checker.

Required contract:

- exactly one user-level global reset supervisor may be active;
- startup first looks up the singleton and creates it only when absent;
- a duplicate startup request exits or reuses the singleton and does not create
  another active checker;
- individual chats and project routes may unregister only their own project
  registration;
- individual chats and project routes cannot disable the user-level singleton;
- global events are only an index into project-local watchdog evidence;
- reset eligibility is decided after rereading project-local route status,
  manual-stop state, route/heartbeat generation, duplicate cooldown key, and
  local watchdog latest evidence;
- reset writes back to both global and local evidence;
- a later heartbeat is required before recovery is claimed.

Commands:

```powershell
python -m py_compile .flowpilot/task-models/global-reset-supervisor/model.py .flowpilot/task-models/global-reset-supervisor/run_checks.py
python .flowpilot/task-models/global-reset-supervisor/run_checks.py
```

Results:

- naive model: 124 states, 150 edges, conflicts reproduced;
- guarded model: 64 states, 90 edges, 0 invariant failures;
- required guarded labels include `global_supervisor_singleton_claimed`,
  `duplicate_global_supervisor_create_rejected`, and
  `local_chat_stop_unregisters_project_only`.

## Watchdog Node Retrigger Guard

Date: 2026-05-01

The user observed a visible Windows console flash whenever another FlowPilot
route entered a new node. Because the real heartbeat and watchdog were paired
one-to-one, the likely failure class was not route execution itself but a
lifecycle reset that reopened the watchdog scheduled task.

A targeted FlowGuard model in
`.flowpilot/task-models/watchdog-node-retrigger/` reproduced the bug:

- buggy checkpoint reset graph: 14 states, 13 edges;
- reachable counterexample: `policy=False` while `task=True` after checkpoint;
- next step label: `watchdog_task_retriggered_by_policy_reset`;
- fixed lifecycle graph: 12 states, 11 edges, 0 invariant failures.

The main meta model had the same shape: checkpoint, anti-rough-finish rework,
and completion-standard expansion reset `external_watchdog_policy_recorded`
while the external watchdog automation stayed active. The repair preserves the
policy gate as lifecycle state and adds an invariant that rejects any running
state with active watchdog automation but missing watchdog policy.

Regression checks:

```powershell
python .flowpilot/task-models/watchdog-node-retrigger/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Results:

- meta model states: 24397
- meta model edges: 27961
- capability model states: 1679
- capability model edges: 1762
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

## PM Completion-Oriented Resume Runway

Date: 2026-05-01

The user observed that first-round FlowPilot work starts with a long plan and
can progress for a long time, but later heartbeat/resume turns often collapse
into one tiny step. A targeted model in
`.flowpilot/task-models/pm-completion-runway/` now treats that as a regression:
PM resume decisions must produce a completion-oriented runway, and the main
executor must replace the visible plan projection from that runway before
starting work.

The model reproduces three unsafe variants:

- PM records only the current gate and the run stalls after one gate;
- the main executor starts from a stale short plan without syncing the PM
  runway into the visible plan;
- a long runway bypasses a required role or hard gate.

The fixed variant records the current gate, downstream steps to completion,
hard-stop conditions, checkpoint cadence, and then continues past the first
gate while still respecting role approvals. A separate PM stop-signal branch is
valid and terminal.

Commands:

```powershell
python .flowpilot/task-models/pm-completion-runway/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Results after integration:

- PM runway fixed model states: 12
- PM runway fixed model edges: 11
- old single-gate bug reproduced: yes
- stale-plan bug reproduced: yes
- hard-gate bypass bug reproduced: yes
- meta model states: 35190
- meta model edges: 37460
- capability model states: 21630
- capability model edges: 22434
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

## Native Visible Plan Tool Sync

Date: 2026-05-01

The user later observed the same failure class in a real Codex Desktop run:
the PM runway could exist in FlowPilot evidence while the desktop application's
visible plan list stayed short or stale. That made the controller repeatedly
sleep, wake, execute one tiny gate, and sleep again.

The targeted PM runway model now distinguishes three different states:

- PM runway evidence exists in `.flowpilot`;
- the host native visible plan/task-list tool exists;
- that native tool, such as Codex `update_plan`, was actually called with a
  downstream runway projection.

The model reproduces the new hazard:

- the host has a native plan tool;
- the main executor writes only `.flowpilot` plan evidence;
- work starts anyway;
- the native desktop plan remains stale even though FlowPilot claims visible
  plan sync.

The fixed path requires the main executor to call the native plan tool when it
exists. If no native plan tool exists, a chat and `.flowpilot` fallback is
valid, but FlowPilot must not claim native Codex plan sync. The visible
projection must include the current executable gate plus downstream runway
items toward completion; a one-step projection is invalid except for true PM
stop or one-gate terminal cases.

Commands:

```powershell
python .flowpilot/task-models/pm-completion-runway/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Results:

- PM runway model reproduced single-gate, stale-plan, native-plan-not-called,
  and hard-gate-bypass hazards.
- Fixed native-plan path passed.
- No-native-plan fallback path passed.
- Meta model states: 71514
- Meta model edges: 76054
- Capability model states: 42852
- Capability model edges: 45388
- Invariant failures: 0

The smoke run also exposed a stale UI visual-asset evidence issue: capability
structural repair or concept reset could invalidate the UI concept target while
leaving old visual-asset style review evidence alive. The capability model now
invalidates downstream frontend-plan and visual-asset evidence whenever concept
target evidence is reset.

## Global Supervisor Autocreate Gate

Date: 2026-05-01

The user required FlowPilot to verify or create the singleton Codex global
watchdog supervisor when heartbeat/watchdog continuity is established. As of
2026-05-02, the global supervisor uses a fixed 30-minute cadence and is tied to
active project registration leases: reuse one active automation, update one
paused singleton to `ACTIVE` when global protection is required, and create
only when no singleton exists and at least one active registration exists.

The validated Codex automation creation shape is:

- `kind`: `cron`
- `rrule`: `FREQ=MINUTELY;INTERVAL=30`
- `cwds`: one workspace string path in the `automation_update` call
- `executionEnvironment`: `local`
- `reasoningEffort`: `medium`
- `status`: `ACTIVE`

FlowGuard initially caught a placement bug: the first revision verified the
global supervisor after activating the external watchdog. The model rejected
that transient active-watchdog state. The final protocol verifies the singleton
before the external watchdog is treated as fully active for formal work.

Commands:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts/flowpilot_global_supervisor.py simulations/meta_model.py simulations/run_meta_checks.py simulations/capability_model.py simulations/run_capability_checks.py .flowpilot/task-models/global-reset-supervisor/model.py .flowpilot/task-models/global-reset-supervisor/run_checks.py
python .flowpilot/task-models/global-reset-supervisor/run_checks.py
python .flowpilot/task-models/external-watchdog-loop/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Runtime action:

- Earlier runs created Codex automation `flowpilot-global-watchdog-supervisor`
  at a 10-minute cadence; the 2026-05-02 lifecycle update supersedes that
  cadence with `FREQ=MINUTELY;INTERVAL=30`.
- `python scripts/flowpilot_global_supervisor.py --status --json` reports the
  registry active-registration count and recommends create, update, reuse, or
  delete based on that count.

Results:

- global supervisor guarded states: 64
- global supervisor guarded edges: 90
- external watchdog states: 25
- external watchdog edges: 24
- meta model states: 24398
- meta model edges: 27962
- capability model states: 1681
- capability model edges: 1764
- invariant failures: 0
- missing required labels: 0
- non-terminating components: 0

## Composite Backward Structural Review

Date: 2026-05-01

The user identified a V-model style hierarchy gap: a parent/module/group should
not close merely because every child passed locally. The correct structure is:
all children pass, then the parent reruns a backward human-like review against
the parent product-function model; after all parents pass, the phase/root runs
the same upward review.

A targeted model in
`.flowpilot/task-models/composite-backward-structure-loop/` now covers the
structural failure cases:

- parent review fails and returns to an affected existing child;
- parent review finds that an adjacent sibling child must be inserted;
- parent review finds that the child subtree must be rebuilt;
- each structural mutation invalidates stale rollups/frontier evidence, returns
  to child work, then reruns parent backward review before parent closure.

Commands:

```powershell
python .flowpilot/task-models/composite-backward-structure-loop/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Results after integration:

- composite structural model states: 72
- composite structural model edges: 71
- meta model states: 27024
- meta model edges: 29294
- capability model states: 16481
- capability model edges: 17285
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

FlowGuard caught one implementation-model bug during integration: a capability
structural repair initially left old implementation evidence marked valid while
the route had already been invalidated. The final model resets old
implementation and child-skill evidence before the changed route can resume.

## Watchdog Hidden Noninteractive Guard

Date: 2026-05-01

The user confirmed that a residual Windows watchdog kept flashing after the
route-014 agent was stopped. Local inspection found `FlowPilot Route 014
Watchdog` still enabled, not hidden, and using a direct interactive
`python.exe` action. The task was disabled, rebuilt as a hidden `pythonw.exe`
scheduled task with the same name, then left disabled. Watchdog evidence now
records `active: false`, `hidden_noninteractive: true`, and
`visible_window_risk: false`.

The FlowGuard task model now treats visible console risk as its own bug class:

- policy reset bug: repeated scheduled-task starts after checkpoint;
- visible action bug: one scheduled-task start can still flash if the action is
  direct interactive `python.exe`;
- fixed path: stable policy, one task start, hidden/noninteractive action.

Regression checks:

```powershell
python .flowpilot/task-models/watchdog-node-retrigger/run_checks.py
python .flowpilot/task-models/external-watchdog-loop/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Results:

- visible-action bug reproduced: 12 states, 11 edges, visible-window invariant
  failure;
- fixed watchdog model: 12 states, 11 edges, 0 invariant failures;
- external watchdog loop: 18 states, 17 edges, 0 invariant failures;
- meta model states: 24397;
- capability model states: 1679;
- invariant failures: 0.

## Quality Package Flow Update

Date: 2026-05-01

The user clarified the simplified final FlowPilot flow:

- startup full grill-me defines the frozen floor, seeds the improvement
  candidate pool, and seeds initial validation direction in one round;
- parent/module and node entry use one reusable quality package instead of
  separate repeated stations for improvement, feature richness, and validation;
- child skills are shown as visible mini-routes of key milestones, while the
  child skill keeps ownership of detailed domain prompts;
- checkpoint and completion closure include anti-rough-finish and final matrix
  reviews so "verification passed" is not treated as enough when the result is
  thin.

The meta model now includes startup candidate/validation seeds, quality package
branches, bounded route raises, anti-rough-finish rework, and final
feature/acceptance/quality-candidate reviews. The capability model now requires
child-skill mini-route projection, quality package completion before
implementation, anti-rough-finish before child-skill completion closure, and
final matrix reviews before terminal completion.

The check runners now build the full finite reachable graph first, then run
invariant, progress, and loop/stuck checks over that complete graph. This keeps
the executable check exact for the model while avoiding depth-search timeouts
after the quality package added route-raise and rework branches.

Commands:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile simulations/meta_model.py simulations/run_meta_checks.py simulations/capability_model.py simulations/run_capability_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
JSON/JSONL parse checks for .flowpilot, .flowguard, and templates/flowpilot
```

Results:

- FlowGuard schema version: 1.0
- meta model states: 25421
- meta model edges: 28985
- capability model states: 1679
- capability model edges: 1762
- JSON files parsed: 267
- JSONL files parsed: 7
- invariant failures: 0
- missing required labels: 0
- nonterminal states without terminal path: 0
- stuck states: 0
- non-terminating components: 0

## Stable Heartbeat And Execution Frontier

Route-012 heartbeat debugging exposed a control-flow design gap: the heartbeat
automation was doing too much if every route or next-jump change required a
prompt rewrite. The new model separates the stable wakeup launcher from the
mutable route frontier.

The task-local model exposed three implementation-shaping issues:

1. Route version could change while the previous execution frontier and plan
   stayed active, creating a stale next jump.
2. Unbounded abstract route mutation could expand the state graph without
   proving the intended property.
3. Terminal shutdown could be externally correct while local frontier/watchdog
   evidence still claimed the watchdog was active.

The revised model requires:

- stable heartbeat launcher recorded;
- checked route version;
- `execution_frontier.json` written for that route version;
- current-node completion guard blocks `next_node` jumps until active-node
  validation and evidence are written;
- visible Codex plan synced from the execution frontier;
- route mutation rechecks before rewriting the frontier and resuming work;
- terminal watchdog inactive and heartbeat lifecycle state written back to the
  execution frontier before completion closes.

Commands:

```powershell
python .flowpilot/task-models/stable-heartbeat-plan-frontier/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Current task-local result:

- stable heartbeat/frontier states: 28
- stable heartbeat/frontier edges: 27
- invariant failures: 0
- missing required labels: 0
- progress findings: 0
- stuck states: 0
- non-terminating components: 0
- latest meta states: 5368
- latest meta edges: 5965
- latest capability states: 358
- latest capability edges: 369

## Implementation Guidance

The project can move into implementation if the new skill preserves these
model-backed rules:

- Do not execute a formal chunk until the active route is checked, the English
  summary is synced, and chunk-level verification is declared.
- Do not front-load future dependencies at startup. Record the dependency plan
  and defer route, chunk, or native-build installs until the active node/check
  needs them.
- Do not open high-risk gates while a formal chunk is active.
- Do not complete while subagent work is pending or returned but unmerged.
- Treat model gaps as route-update triggers, then re-run FlowGuard checks and
  resync summaries before continuing.
- Let repeated unrecoverable model gaps, failed experiments, or denied safety
  gates end in a blocked state with evidence instead of looping.
- Commit a showcase-grade long-horizon floor before freezing the contract.
- Make startup, route-expansion, and completion full grill-me visible and
  persistent. Derive task-specific layers, ask at least 100 questions per
  active layer, and cover or explicitly waive the baseline risk families.
- Use focused grill-me for parent-scope, node-scope, module, and child-skill
  entry boundaries. Record the scope id, ask 20-40 questions by default, and
  go up to 50 only for complex boundaries.
- Use lightweight 5-10 question self-checks for heartbeat micro-steps. Do not
  treat a lightweight check as a full or focused grill-me gate.
- Emit visible route maps and node roadmaps in chat until the Cockpit UI can
  show live progress.
- Create real heartbeat continuation when the host supports it and check
  heartbeat health before formal nodes.
- Use FlowGuard as process designer before implementation, not only as a final
  checker.
- Treat the first route tree as a candidate until a root-route FlowGuard check
  freezes it into the canonical route.
- Before entering a child node, review the current parent subtree with
  FlowGuard and emit a visible node roadmap.
- On heartbeat resume, check whether the current leaf is unfinished and resume
  it before advancing.
- When routes mutate, regenerate/recheck the affected candidate tree and do not
  reuse stale child or route evidence.
- If completion self-interrogation finds obvious high-value work, raise the
  standard, update the route, rerun FlowGuard checks, and rework/reverify.

## Capability Routing Preflight

After adding child-skill routing to the design, a second FlowGuard model checked
the capability layer:

- `grill-me` style self-interrogation before contract freezing;
- real FlowGuard and `model-first-function-flow` dependency checks before
  implementation;
- a capabilities manifest and evidence sync before route execution;
- child-skill contract loading, requirement mapping, evidence planning,
  conformance model checks, execution evidence audit, evidence-output matching,
  domain-quality review, iteration closure, and completion-standard
  verification before dependent capability work can close;
- prompt-layer separation: FlowPilot records child-skill evidence and ordering,
  but does not duplicate detailed UI, visual asset, screenshot, or modeling
  prompt rules owned by child skills;
- demand-driven dependency planning before meta-route/capability-route checks
  and implementation;
- conditional UI gates for substantial user-facing UI work;
- explicit concept-target gates before UI implementation, with rendered
  screenshots restricted to post-implementation QA evidence;
- iterative divergence handling after screenshot QA, including fix-UI,
  revise-concept, and accepted-difference branches;
- conditional visual asset/app-icon style review for UI routes that create
  product-facing imagery;
- optional subagent paths with scope checks, return, and merge.

Command:

```powershell
python simulations/run_capability_checks.py
```

Current explored graph after the exact child-skill and per-layer
self-interrogation policy revision:

- states: 316
- edges: 327
- invariant failures: 0
- missing required labels: 0
- progress findings: 0
- stuck states: 0
- non-terminating components: 0

The first capability-routing model exposed two implementation-shaping issues:

1. Completion-time checks must evaluate the historical gates, not only a
   `running`-state readiness helper. Otherwise complete states can be falsely
   treated as missing prerequisites.

2. Subagent scope checking must be a distinct node from the actual
   spawn-or-skip decision. If the scope check and spawn choice are collapsed,
   the spawn branch can become unreachable or a self-loop.

Additional capability-routing rules:

- FlowPilot is opt-in only. It is enabled only after the user explicitly invokes
  FlowPilot or the `flowpilot` skill; an existing `.flowpilot/` directory is
  continuity state after invocation, not a trigger by itself.
- Run-mode choice is one part of the three-question startup gate and must be
  answered explicitly before self-interrogation. Show options from loose to
  strict: `full-auto`, `autonomous`, `guided`, `strict-gated`. Do not infer a
  fallback mode from host pause limits, invocation text, existing `.flowpilot/`
  state, or prior routes.
- Formal FlowPilot routes have no lower default tier: they start at
  showcase-grade scope.
- Capability routes require visible self-interrogation, heartbeat schedule,
  heartbeat health, and FlowGuard process design before implementation.
- Completion-time high-value review may force a capability-route expansion; in
  that branch, old implementation and verification evidence must not be reused
  as if the raised standard had already passed.
- Non-UI routes must not invoke UI-only gates.
- Capability routes and implementation cannot start until the dependency plan is
  recorded and future installs are explicitly deferred.
- Capability routes cannot rely on another skill name alone. Before capability
  work, the source skill's `SKILL.md` and relevant references must be loaded or
  explicitly skipped with reasons, the child workflow and completion standard
  must be mapped into route gates, and an evidence checklist must exist.
- Capability routes must verify the exact source skill and reject ad hoc
  substitutes before mapping requirements. FlowPilot-owned formal invocation
  policy may wrap a general-purpose child skill such as `grill-me` without
  changing that child skill's standalone behavior.
- Child-skill use cannot close on instruction loading alone. FlowPilot must
  check a child-skill conformance model, audit execution evidence, confirm the
  evidence matches actual outputs, run a domain-quality review, and close the
  child-skill iteration loop before parent-node resume.
- Completion closure cannot start until invoked child skills are verified
  against their own completion standards or explicit waivers/blockers.
- FlowPilot is an orchestration skill. It should preserve evidence gates such
  as concept-target decisions, rendered QA, visual asset scope, and loop
  closure, while the detailed UI design, screenshot comparison, icon generation,
  and modeling instructions remain owned by the invoked child skills.
- When completion self-interrogation raises the standard and expands the route,
  child-skill fidelity, FlowGuard dependency, dependency planning, heartbeat,
  process design, and meta-route checks are rerun instead of reusing stale
  route evidence.
- UI routes cannot implement until the current UI is inspected, a
  concept-led UI gate runs, an image concept target is generated or an
  authoritative user design reference is recorded, that target/reference is
  visibly shown and recorded, and the modern UI implementation plan is
  recorded.
- Capability routes emit a visible route map before heartbeat health and
  implementation work.
- Completion review emits a visible completion route map, derives dynamic
  layers, and uses at least 100 self-interrogation questions per active layer.
- Rendered browser, Edge, Playwright, WebView, or desktop screenshots are
  post-implementation QA evidence only; they cannot satisfy the UI concept
  target gate unless the user supplied them as the authoritative design
  reference before implementation.
- UI routes cannot complete after a one-shot concept and one screenshot review.
  The divergence review must classify material differences as accepted, UI
  defects to fix, or concept problems to revise. If UI or concept evidence
  changes, screenshot QA and comparison run again before loop closure.
- UI routes that create app icons, desktop icons, logos, splash screens, README
  hero images, or similar product-facing imagery must decide whether visual
  assets are in scope and run style review before implementation/completion.
- UI routes cannot complete until rendered screenshot QA, concept-vs-real
  divergence review, and concept/UI iteration loop closure pass.
- Subagent work may run only after a non-blocking/disjoint scope check, and
  returned work must be merged by the main agent before dependent implementation
  or completion.

## Route-006 Protocol Repair

Route-005 exposed a new process gap: the protocol text asked for concept
targets and visible self-interrogation, but the executable models did not yet
enforce a 100-question floor or visible chat route maps. Route-006 updates both
models so these gates are part of the reachable workflow, not optional prose.

Route-007 further closes the gap where a round could satisfy the count while
over-focusing on UI. The models now also require layered self-interrogation
coverage.

Route-009 integrates the later hierarchical-heartbeat, route-mutation,
recursive-route-planning, and child-skill-contract-conformance models into the
main FlowPilot meta and capability checks. This adds candidate route trees,
root-route checks, parent-subtree review, unfinished-node recovery, and
child-skill evidence/domain-quality gates to the executable controller models.

Route-010 repairs the child-skill boundary exposed during route-009 UI
redesign attempts:

- `grill-me` remains a lightweight standalone one-question-at-a-time user
  interview skill. FlowPilot owns the formal self-interrogation invocation
  policy when it uses `grill-me` inside a formal route.
- Formal FlowPilot self-interrogation no longer accepts 100 questions total
  across many topics. It derives task-specific layers and requires at least
  100 questions per active layer.
- FlowPilot capability routing now verifies exact child-skill source loading,
  substitute rejection, and FlowPilot-owned invocation-policy mapping before
  dependent work can proceed.
- The UI concept route now treats HTML/CSS/browser/desktop screenshots as
  prototypes or rendered QA evidence, not as substitutes for an `imagegen`
  concept target unless they were supplied by the user as an authoritative
  pre-implementation reference.
- A task-local FlowGuard model,
  `.flowpilot/task-models/exact-child-skill-profile-gates/`, checks that
  standalone child-skill use is not forced into the formal FlowPilot floor
  while formal FlowPilot routes reject HTML substitute concept targets.

Commands:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python .flowpilot/task-models/exact-child-skill-profile-gates/run_checks.py
```

Results:

- meta model states: 4430
- meta model edges: 5027
- capability model states: 316
- capability model edges: 327
- exact child-skill profile gate states: 24
- exact child-skill profile gate edges: 23
- invariant failures: 0
- missing required labels: 0
- progress findings: 0
- stuck states: 0
- non-terminating components: 0

## Tiered Grill-Me Policy Update

Date: 2026-05-01

The user clarified that FlowPilot should not run the full 100-questions-per-layer
grill-me at every scope. The executable policy is now:

- full grill-me at formal boundaries: startup contract freeze, root
  route/process-design freeze, route mutation or standard expansion, and
  completion review;
- focused grill-me at bounded parent, module, leaf-node, and child-skill
  boundaries: 20-40 questions by default, up to 50 for complex boundaries;
- lightweight self-check at heartbeat micro-steps: 5-10 targeted questions.

The main meta model now requires focused parent-scope grill-me before
parent-subtree FlowGuard review, focused node-level grill-me before chunk
definition, and lightweight self-check before formal chunk execution. The
capability model now requires focused child-skill grill-me before child-skill
contract loading and conformance gates. This keeps FlowPilot as the process
orchestrator while child skills keep their own detailed execution rules.

Commands:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Results:

- meta model states: 5239
- meta model edges: 5836
- capability model states: 328
- capability model edges: 339
- invariant failures: 0
- missing required labels: 0
- progress findings: 0
- stuck states: 0
- non-terminating components: 0

## Global Watchdog Recording Implementation

Date: 2026-05-01

The user approved implementing two related changes:

- the project-local watchdog writes compact user-level global records in
  addition to `.flowpilot/watchdog/` evidence;
- FlowPilot ships a Codex automation prompt template for the singleton global
  watchdog supervisor.

The control boundary is:

- project-local `.flowpilot/state.json` and `.flowpilot/watchdog/latest.json`
  remain authoritative;
- the global registry is an index, not a reset authority;
- the global supervisor must be singleton at the user/environment level;
- duplicate supervisor creation attempts reuse or reject the existing
  singleton;
- a local project or chat may unregister its own project record but must not
  disable the global supervisor;
- the global supervisor rereads local evidence, expires terminal/manual-stop
  routes, supersedes old route generations, and dedupes repeated stale events
  before recording a reset requirement.

Commands:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts/flowpilot_watchdog.py scripts/flowpilot_global_supervisor.py .flowpilot/task-models/external-watchdog-loop/model.py .flowpilot/task-models/external-watchdog-loop/run_checks.py .flowpilot/task-models/global-reset-supervisor/model.py .flowpilot/task-models/global-reset-supervisor/run_checks.py
python .flowpilot/task-models/external-watchdog-loop/run_checks.py
python .flowpilot/task-models/global-reset-supervisor/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Runtime checks also covered:

- current paused project dry-run returned `inactive_terminal_route`;
- global supervisor `--status` on a temp directory returned `status_only`;
- Codex global supervisor prompt template is present and Windows global helper
  support has been removed;
- temporary running-project integration returned
  `stale_official_reset_required`, wrote local `global_record`, created one
  global registry project, and the supervisor returned
  `reset_required_revalidated` with controller action kind
  `codex_app_automation_update` and heartbeat automation id `fixture-heartbeat`.
- JSON/JSONL parse checks covered `.flowpilot`, `.flowguard`, and
  `templates/flowpilot`.

Results:

- external watchdog model states: 25
- external watchdog model edges: 24
- global supervisor guarded states: 64
- global supervisor guarded edges: 90
- meta model states: 24397
- meta model edges: 27961
- capability model states: 1679
- capability model edges: 1762
- JSON files parsed: 267
- JSONL files parsed: 7
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

## Watchdog Stale Threshold Default

Date: 2026-05-01

The user requested changing the watchdog default stale threshold from 5 minutes
to 10 minutes. This aligns the default stale line with the default one-minute
heartbeat plus the existing 10-minute post-busy grace window.

Commands:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts/flowpilot_watchdog.py .flowpilot/task-models/external-watchdog-loop/model.py .flowpilot/task-models/external-watchdog-loop/run_checks.py
python .flowpilot/task-models/external-watchdog-loop/run_checks.py
python scripts/flowpilot_watchdog.py --root . --dry-run --json
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Findings:

- `scripts/flowpilot_watchdog.py` now defaults
  `FLOWPILOT_WATCHDOG_STALE_MINUTES` to 10.
- `templates/flowpilot/watchdog/watchdog.template.json` now declares
  `threshold_minutes` 10.
- User-facing docs and skill references now describe the 10-minute default.
- Historical adoption logs that explicitly ran `--stale-minutes 5` were left as
  historical evidence.

Results:

- external watchdog model states: 25
- external watchdog model edges: 24
- dry-run threshold minutes: 10.0
- dry-run decision on the paused current route: `inactive_terminal_route`
- meta model states: 24397
- meta model edges: 27961
- capability model states: 1679
- capability model edges: 1762
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

## Concept Authenticity And Heartbeat Gate Execution

Date: 2026-05-01

Route-016 exposed three execution-layer gaps that were not covered by the earlier
abstract models:

- an image can be produced by `imagegen` but still be an existing screenshot,
  existing-image variant, desktop capture, taskbar-inclusive capture, old route
  UI, or prior failed UI evidence with cosmetic changes rather than a clean
  independent concept target;
- human-like review can jump straight to a conclusion without first recording
  what the image, output, or exercised feature actually appears to be;
- a heartbeat can resume an unfinished node, write a "continue to next gate"
  decision, and stop without executing the next gate or recording a real
  blocker.

A targeted model in
`.flowpilot/task-models/concept-authenticity-heartbeat-execution/` now checks
the repaired control behavior:

- concept gates require both source validation and authenticity validation;
- authenticity and human-like inspection judgements require a neutral
  pre-judgement observation record;
- contaminated concept candidates fail, are grilled into a specific blocking
  issue, mutate the route back to clean concept regeneration, and only then
  rerun the concept gate;
- heartbeats that resume unfinished nodes must select and execute the persisted
  `current_subnode` or `next_gate`, or record a concrete blocker;
- parent review cannot pass before the current heartbeat gate is complete.

Command:

```powershell
python .flowpilot/task-models/concept-authenticity-heartbeat-execution/run_checks.py
```

Results:

- targeted model states: 16
- targeted model edges: 15
- invariant failures: 0
- missing required labels: 0
- hazard probes caught source-only concept passes, existing-variant concept
  passes, authenticity review without neutral observation, regeneration
  without route mutation, heartbeat no-op decisions, and parent review before
  current gate completion.

## Strict Review Route Mutation And Lifecycle Reconciliation

Date: 2026-05-01

Follow-up route-016 review exposed two further control-flow risks:

- failed reviews could still be treated as "evidence exists" instead of a
  strict route mutation;
- pause, restart, and terminal cleanup could leave lifecycle authorities out
  of sync across Codex automations, global supervisor records, Windows
  scheduled tasks, local state, execution frontier, and watchdog evidence.

A targeted model in
`.flowpilot/task-models/strict-review-route-mutation-lifecycle/` now checks
the repaired behavior:

- a failed review writes a neutral observation, records a blocking decision,
  grills the issue, marks old child evidence stale/superseded, mutates the
  route, and rewrites the frontier to a reset or new repair child;
- the repair child reruns process model, product model, work, neutral
  observation, review, and then parent review;
- lifecycle writeback scans Codex automations, global supervisor records,
  Windows scheduled tasks, local state, execution frontier, and watchdog
  evidence before pause/restart/terminal closure;
- disabled residual Windows FlowPilot tasks block lifecycle closure until
  resolved or explicitly waived.

Command:

```powershell
python .flowpilot/task-models/strict-review-route-mutation-lifecycle/run_checks.py
```

Results:

- targeted model states: 62
- targeted model edges: 61
- invariant failures: 0
- missing required labels: 0
- hazard probes caught review failure without route mutation, repair pass
  without models, parent review before repair pass, lifecycle writeback without
  full scan, and lifecycle closure with residual Windows task.

Main model rechecks also passed after adding lifecycle reconciliation:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

## Six-Agent Crew And Project-Manager Heartbeat Recovery

Date: 2026-05-01

The user promoted the route-017 persistent observer experiment into a permanent
FlowPilot control architecture. Formal FlowPilot routes now create or restore a
fixed six-agent crew before formal route work:

- project manager;
- human-like reviewer;
- process FlowGuard officer;
- product FlowGuard officer;
- worker A;
- worker B.

The project manager owns route, heartbeat-resume completion runways, PM stop
signals, repair, and completion decisions. The main executor implements the
decision and enforces hard safety gates; it does not decide route movement
directly from the frontier. Heartbeat recovery loads
state/frontier/lifecycle evidence, restores or replaces the crew, asks the
project manager for a completion-oriented runway, syncs that runway into the
visible plan, executes at least the current gate when executable, and then
continues until a PM stop signal, hard gate, blocker, route mutation, or real
execution limit stops progress.

A targeted model in
`.flowpilot/task-models/six-agent-crew-architecture/` checks:

- six-role crew ledger before formal work;
- project-manager authority for route, resume, repair, and completion;
- heartbeat crew restoration before PM resume decision;
- neutral observation before reviewer judgement;
- blocking reviewer reports force PM-owned route mutation, stale evidence
  invalidation, repair modeling, and same-class recheck;
- process and product FlowGuard officers both check root, node, repair, and
  closure scopes;
- worker agents are bounded sidecars only;
- terminal closure reconciles lifecycle and archives the crew ledger.

The first model run exposed a real design issue: a repair path reset
`reviewer_decision` for the next inspection and lost the fact that a prior
review had blocked the route. The model was corrected by adding persistent
block evidence (`review_block_recorded`) so route mutation and completion can
still trace why the route changed.

Follow-up review found another protocol gap: after a reviewer block, the
failed inspection issue was grilled and the project manager repair decision was
recorded, but the project manager was not itself forced through a repair
strategy interrogation. The model now inserts
`pm_repair_decision_interrogated` between issue grilling and PM repair route
decision. Hazard probes reject a PM repair decision without that interrogation.

Commands:

```powershell
python .flowpilot/task-models/six-agent-crew-architecture/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Results after integration:

- six-agent task model states: 72
- six-agent task model edges: 71
- meta model states: 34107
- meta model edges: 36377
- capability model states: 19951
- capability model edges: 20755
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

## Crew Role Memory Rehydration

Date: 2026-05-02

The user observed that after heartbeat sleep/wake, the six FlowPilot subagents
appeared to be gone or freshly recreated, with prompts repeated and no obvious
continuity. The repaired protocol distinguishes live subagent continuity from
durable role continuity: live subagent handles are best effort, while compact
role memory packets are mandatory.

A targeted model in `.flowpilot/task-models/crew-memory-rehydration/` checks:

- all six role memory packets are written before PM ratification;
- heartbeat loads local state, execution frontier, crew ledger, and role
  memory before asking the project manager for a runway;
- replacement role agents are seeded from their latest role memory packet;
- raw chat transcripts are not accepted as authoritative role memory;
- role memory is refreshed after meaningful work before checkpoint or final
  verification;
- terminal closure archives role memory before the crew ledger.

The targeted model reproduced four unsafe variants: live-agent assumption,
replacement without memory seed, raw transcript accepted as memory, and missing
memory refresh after work. The fixed variant passed.

Commands:

```powershell
python .flowpilot\task-models\crew-memory-rehydration\run_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results after integration:

- targeted fixed model states: 31
- targeted fixed model edges: 30
- meta model states: 76203
- meta model edges: 80743
- capability model states: 44973
- capability model edges: 47509
- invariant failures: 0
- missing required labels: 0
- stuck states: 0

## Material Intake And PM Handoff

Date: 2026-05-02

The user identified a startup route-design gap: for simple UI work the project
manager can often infer enough context, but data-heavy, table-heavy, raw,
contradictory, or partially structured materials can make material
understanding a real phase of the work. FlowPilot now treats material intake as
a first-class gate before PM product-function architecture, contract freeze,
route generation, or capability routing.

The repaired flow is:

- main executor writes a descriptive Material Intake Packet;
- human-like reviewer approves or blocks material sufficiency;
- project manager writes a material understanding memo and source-claim matrix;
- project manager classifies material complexity and records whether materials
  can feed route design directly or require a formal discovery/cleanup/modeling
  subtree.

A targeted model in `.flowpilot/task-models/material-intake-pm-handoff/`
reproduced four unsafe variants:

- shallow packet lists files before source summaries and quality classification;
- reviewer accepts the packet without sufficiency review;
- PM records a route decision before reviewed material handoff;
- messy/raw materials proceed without a formal discovery subtree.

Commands:

```powershell
python .flowpilot\task-models\material-intake-pm-handoff\run_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results after integration:

- targeted normal-material fixed path: 15 states, 14 edges, 0 invariant failures;
- targeted messy-material fixed path: 16 states, 15 edges, 0 invariant failures;
- all four hazard variants reproduced;
- meta model states: 87356;
- meta model edges: 91896;
- capability model states: 72792;
- capability model edges: 78034;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0.

## Resource Output Lineage

Date: 2026-05-02

The user asked to rerun FlowPilot through FlowGuard with a specific waste
question: which steps do real work but never reach final output, for example
image generation that is not later used.

The existing models already covered concept authenticity, stale visual
evidence, rendered screenshot QA, and final route-wide gate ledgers. The gap
was narrower: generated resources were not first-class ledger entries. A
route could prove that a concept/source/aesthetic gate happened without proving
where the generated artifact went afterward.

The repaired flow is:

- before expensive/user-facing generation, record the output contract and
  resource budget;
- generated concept images, visual assets, screenshots, route diagrams, model
  reports, and similar artifacts each receive a disposition;
- allowed dispositions are consumed by implementation/QA, included in final
  output, used as route/model evidence, superseded, quarantined, or discarded
  with reason;
- route mutation or regeneration must invalidate stale generated resources;
- final route-wide gate ledgers must resolve generated-resource lineage before
  claiming zero unresolved items.

A targeted model in `.flowpilot/task-models/resource-output-lineage/`
reproduced eight unsafe variants:

- concept image generated but never consumed by implementation, divergence
  review, final output, or quarantine;
- visual asset generated without exported final-output path or quarantine;
- screenshot generated without QA/final-review consumption;
- route diagram generated without visible route-map consumption;
- model report generated without being attached to a FlowGuard gate;
- backend-only route generates UI visual resources;
- ledger claims zero unresolved resources before dispositions are recorded;
- route mutation quarantines a resource without stale-resource invalidation.

Commands:

```powershell
python .flowpilot\task-models\resource-output-lineage\run_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\check_install.py
python scripts\smoke_autopilot.py
```

Results after integration:

- targeted model states: 29;
- targeted model edges: 28;
- all eight resource-waste hazards reproduced;
- meta model states: 92192;
- meta model edges: 96732;
- capability model states: 86302;
- capability model edges: 91544;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0.

## Final Route-Wide Gate Ledger

Date: 2026-05-02

The user identified a terminal closeout gap: a child-skill, node, or temporary
repair gate can pass locally, but a later route mutation may make a static
startup checklist incomplete. FlowPilot now requires a PM-owned final
route-wide gate ledger before terminal completion.

The repaired flow is:

- PM rebuilds `.flowpilot/final_route_wide_gate_ledger.json` from the current
  route and execution frontier, not from the initial route snapshot;
- PM resolves effective nodes after route mutations and superseded branches;
- PM collects child-skill, human-review, product/process, verification,
  lifecycle, and completion gates;
- PM checks stale evidence, superseded-node explanations, waivers, and blocked
  items;
- completion requires `unresolved_count` to be zero;
- human-like reviewer runs a backward replay through the PM-built ledger;
- PM can approve terminal completion only after that reviewer replay passes.

A targeted model in `.flowpilot/task-models/final-route-wide-gate-ledger/`
reproduced seven unsafe variants:

- final ledger built from the initial route snapshot;
- child-skill gates omitted from final closeout;
- stale evidence accepted without recheck;
- superseded nodes omitted without explanation;
- unresolved items accepted;
- reviewer backward check run before the PM ledger exists;
- PM completion approval before reviewer backward replay.

Commands:

```powershell
python .flowpilot\task-models\final-route-wide-gate-ledger\run_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results after integration:

- targeted fixed path: 14 states, 13 edges, 0 invariant failures;
- all seven hazard variants reproduced;
- meta model states: 90876;
- meta model edges: 95416;
- capability model states: 84804;
- capability model edges: 90046;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0.

## Optional Heartbeat Manual Resume Notices

Date: 2026-05-02

The user clarified that real heartbeat or scheduled wakeup support is optional.
On hosts without that support, FlowPilot must continue from manual user
resume using `.flowpilot/` state, execution frontier, crew memory, and PM
runway evidence. It must not treat missing heartbeat/watchdog/global-supervisor
automation as a blocker in `manual-resume` mode.

The repaired flow is:

- automated hosts check real heartbeat health and may tell the user to wait for
  heartbeat wakeup or type `continue FlowPilot`;
- unsupported hosts check manual-resume state/frontier/crew-memory readiness
  and tell the user to type `continue FlowPilot`;
- controlled nonterminal blocked exits record a resume notice;
- terminal completed exits record a completion notice instead of a resume
  prompt.

Commands:

```powershell
python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\check_install.py
python scripts\smoke_autopilot.py
```

Results after integration:

- meta model states: 92192;
- meta model edges: 96732;
- capability model states: 86302;
- capability model edges: 91544;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0.

## 2026-05-02 - Startup Activation Hard Gate

Trigger: a formal FlowPilot route could produce route-local artifacts while
canonical state, execution frontier, crew ledger, role memory, and continuation
evidence still described an older completed route. This allowed child-skill or
imagegen work to appear as if FlowPilot startup had happened when the core
activation transaction had not completed.

Decision: `use_flowguard`.

Modeled risk:

- route file written without canonical active state;
- imagegen or implementation before execution frontier and crew activation;
- startup guard recorded before continuation readiness;
- route execution before a guard pass;
- shadow route artifacts accepted as startup evidence.

Model and protocol changes:

- added `scripts/flowpilot_startup_guard.py`;
- added `simulations/startup_guard_model.py` and
  `simulations/run_startup_guard_checks.py`;
- added `startup_activation_guard_passed` to the meta and capability models;
- added `startup_activation` to state/frontier templates and route/node gates;
- documented shadow routes as invalid startup evidence.

Validation:

```powershell
python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\run_startup_guard_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py
python scripts\check_install.py
python simulations\run_startup_guard_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\flowpilot_startup_guard.py --root . --route-id route-021 --json
```

Results after integration:

- startup guard safe path: 12 states, 11 edges, 0 invariant failures;
- all five startup-bypass hazard states detected;
- meta model states: 92194;
- meta model edges: 96734;
- capability model states: 86306;
- capability model edges: 91548;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0;
- current ignored route-021 runtime correctly fails the startup guard because it
  is terminal, archived, lacks `startup_activation`, and has deleted
  continuation automation.

## 2026-05-02 - Live Subagent Startup Decision Gate

Trigger: the user clarified that FlowPilot must not silently fall back to a
single main executor when six real background agents are unavailable. It should
pause, ask whether to start the six live background agents, and use
memory-seeded single-agent six-role continuity only after explicit fallback
approval.

Decision: `use_flowguard`.

Modeled risk:

- startup guard passed without a live-subagent startup decision;
- single-agent role continuity authorized without a recorded user decision;
- startup hard gate treated role memory as an automatic substitute for live
  background agents;
- meta/capability execution advanced before live startup resolution.

Model and protocol changes:

- added `startup_activation.live_subagent_startup` to state and frontier
  templates;
- updated `scripts/flowpilot_startup_guard.py` to require either six live
  background agents or explicit single-agent fallback authorization;
- updated startup guard, meta, and capability simulations with live-subagent
  decision labels before startup guard pass;
- updated public invocation, protocol, schema, README, templates, and handoff
  language to state that fallback requires an explicit user decision.

Validation:

```powershell
python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\run_startup_guard_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py
python scripts\check_install.py
python simulations\run_startup_guard_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results after integration:

- startup guard safe path: 21 states, 20 edges, 0 invariant failures;
- all seven startup-bypass hazard states detected;
- meta model states: 92198;
- meta model edges: 96738;
- capability model states: 86314;
- capability model edges: 91556;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0.

## 2026-05-02 - FlowPilot Installer And Release Tooling

Trigger: FlowPilot needs a GitHub-friendly installation and public release
preflight path that installs/checks FlowPilot and dependencies without uploading
private runtime state or publishing companion skills.

Decision: `use_flowguard`.

Modeled risks:

- installer overwrites an existing local skill without explicit force;
- release preparation skips dependency source checks, privacy scan, or
  validation;
- release is allowed while companion skill GitHub sources are missing;
- tracked private runtime state is included in the public repository;
- release tooling packages or publishes companion skill repositories;
- image generation is hard-coded as a universal `imagegen` skill instead of a
  host-specific capability mapping.

Model and tooling changes:

- added `flowpilot.dependencies.json`;
- added `scripts/install_flowpilot.py`;
- added `scripts/check_public_release.py`;
- added `simulations/release_tooling_model.py` and
  `simulations/run_release_tooling_checks.py`;
- updated install checks, smoke checks, README, dependency docs, verification
  docs, and installation contract.

Validation:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts\install_flowpilot.py scripts\check_public_release.py scripts\check_install.py scripts\smoke_autopilot.py simulations\release_tooling_model.py simulations\run_release_tooling_checks.py
python simulations\run_release_tooling_checks.py
python scripts\install_flowpilot.py --check --json
python scripts\check_install.py
python scripts\smoke_autopilot.py
python scripts\check_public_release.py --skip-url-check --json
```

Results:

- release tooling safe path: 13 states, 12 edges, 0 invariant failures;
- hazard probes caught overwrite-without-force, release-before-privacy-scan,
  release-with-private-state, publish-with-missing-dependency-source,
  companion-skill packaging, companion-skill publishing, and hardcoded image
  provider;
- install check passed and found Codex's `raster_image_generation` provider at
  `.system/imagegen`;
- smoke checks passed;
- public release check ran validations successfully but correctly blocked on
  missing GitHub sources for `model-first-function-flow`, `grill-me`,
  `concept-led-ui-redesign`, and `frontend-design`.

## 2026-05-02 - Three-Question Stop-And-Wait Startup Gate

Trigger: the user simplified FlowPilot startup to a hard pre-banner gate:
`Use FlowPilot` / `使用开始` must ask three questions first, and after asking,
the assistant must stop and wait for the user's reply before any banner,
route, subagent, heartbeat, imagegen, or implementation work can begin.

Decision: `use_flowguard`.

Modeled risk:

- startup banner emitted in the same response as the questions;
- startup answers recorded without the assistant stopping for a later user
  reply;
- background-agent fallback or manual resume inferred by the agent;
- heartbeat/manual continuation or live/single-agent execution contradicting
  the user's startup answers;
- route, child-skill, imagegen, implementation, or chunk work starting before
  the startup guard pass.

Model and protocol changes:

- added `startup_activation.startup_questions.dialog_stopped_for_user_answers`;
- changed the public invocation to open only the three-question prompt;
- made `single_message_invocation` an invalid answer source for startup gate
  evidence;
- updated state/frontier templates, protocol docs, README, and handoff notes;
- updated `scripts/flowpilot_startup_guard.py` to require stop-and-wait
  evidence;
- updated startup, meta, and capability simulations with
  `startup_dialog_stopped_for_user_answers`.

Validation:

```powershell
python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\run_startup_guard_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py
python -m json.tool templates\flowpilot\state.template.json
python -m json.tool templates\flowpilot\execution_frontier.template.json
python -m json.tool templates\flowpilot\mode.template.json
python simulations\run_startup_guard_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\check_install.py
python scripts\smoke_autopilot.py
```

Results after integration:

- startup guard safe path: 66 states, 65 edges, 0 invariant failures;
- all ten startup-bypass hazard states detected, including
  `answers_recorded_without_dialog_stop`;
- meta model states: 92202;
- meta model edges: 96742;
- capability model states: 86318;
- capability model edges: 91560;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0;
- installation and smoke checks passed.

## 2026-05-02 - PM-Owned Startup Gate And Reviewer Report

Trigger: the user clarified that startup review should not be an approval
object. The human-like reviewer audits facts and writes a report to PM. PM
decides whether to open startup or return blockers to workers. Workers repair,
then the reviewer rechecks before PM can open the gate.

Decision: `use_flowguard`.

Modeled risk:

- reviewer report treated as startup approval;
- PM opens startup without a clean reviewer report;
- PM opens while reviewer blockers are still assigned for worker remediation;
- worker remediation is accepted without reviewer recheck;
- clean-start or no-reuse requests proceed without evidence that old routes,
  old screenshots, old icons, old concept images, or old UI assets were not
  reused.

Model and protocol changes:

- added report-only startup preflight review evidence;
- added PM-owned `pm_start_gate` evidence;
- added `.flowpilot/startup_review/latest.json` and
  `.flowpilot/startup_pm_gate/latest.json` templates;
- changed `scripts/flowpilot_startup_guard.py --record-pass` so it requires
  the PM gate to be opened from the current clean reviewer report;
- added `--write-review-report` and `--record-pm-start-gate` startup guard
  modes;
- updated startup, meta, and capability simulations with the reviewer -> PM ->
  worker remediation -> reviewer recheck -> PM open loop.

Validation:

```powershell
python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\meta_model.py simulations\capability_model.py simulations\run_startup_guard_checks.py simulations\run_meta_checks.py simulations\run_capability_checks.py
python simulations\run_startup_guard_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\check_install.py
python scripts\flowpilot_startup_guard.py --help
```

Results after integration:

- startup guard safe path: 194 states, 193 edges, 0 invariant failures;
- startup guard hazard probes detected reviewer direct open, PM open without
  report, PM open on blocked report, worker fix without recheck, and clean
  start without cleanup;
- meta model states: 92212;
- meta model edges: 96752;
- capability model states: 86338;
- capability model edges: 91580;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0;
- nonterminating components: 0;
- installation check passed.

## 2026-05-02 - Remove Separate Startup Guard; Reviewer Facts Plus PM Gate

Trigger: the user rejected replacing the old startup guard with another runtime
review script. The correct startup design is not "script as reviewer"; it is
two human roles: reviewer checks facts and reports, PM opens or returns
blockers. There is no third startup opener.

Decision: `use_flowguard`.

Modeled risk:

- route heartbeat accepted at 30 minutes instead of 1 minute;
- Codex cron/heartbeat mislabeled as the external Windows watchdog;
- missing Windows scheduled task accepted as watchdog evidence;
- missing 30-minute singleton global supervisor evidence accepted;
- reviewer writes a clean startup report without direct fact checks;
- reviewer opens the startup gate directly;
- PM opens without a clean factual reviewer report;
- worker remediation accepted without reviewer recheck;
- child skill, imagegen, implementation, or route execution starts before PM
  opens startup;
- clean-start request proceeds without old-route or old-asset cleanup evidence.

Model and protocol changes:

- deleted the runtime startup guard script and the old startup guard model;
- added `simulations/startup_pm_review_model.py` and
  `simulations/run_startup_pm_review_checks.py` as FlowGuard-only validation
  artifacts;
- replaced `startup_activation_guard_passed` with
  `work_beyond_startup_allowed`;
- changed startup labels to `fact_report` and
  `pm_start_gate_opened_from_fact_report`;
- updated templates and protocol so `.flowpilot/startup_review/latest.json` is
  the reviewer factual report and `.flowpilot/startup_pm_gate/latest.json` is
  the only PM startup-opening record;
- added `docs/reviewer_fact_audit.md` and a reviewer fact-check baseline for
  startup, material sufficiency, product architecture, child skills,
  inspections, and final backward replay.

Validation:

```powershell
python -m py_compile simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py
python simulations\run_startup_pm_review_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Final results:

- startup PM-review safe path: 194 states, 193 edges, 0 invariant failures;
- all startup hazard probes detected, including the 30-minute route heartbeat,
  Codex watchdog, missing Windows task, missing global supervisor, and
  reviewer-no-fact-check hazards;
- meta model states: 92210;
- meta model edges: 96750;
- capability model states: 86334;
- capability model edges: 91576;
- invariant failures: 0;
- missing required labels: 0;
- stuck states: 0;
- nonterminating components: 0;
- installation check passed;
- installed FlowPilot skill `SKILL.md` and `references/protocol.md` were
  synchronized after checking that they still contained the removed startup
  guard command;
- smoke autopilot passed;
- public release check remains blocked by existing missing GitHub dependency
  sources for companion skills.

### 2026-05-02 Follow-Up - User-Decision-Bound Subagent Fact Review

The startup reviewer fact report now explicitly binds the background-agent user
answer to actual subagent state:

- if the user allowed background agents, the reviewer must verify six live
  role-bearing subagents were freshly spawned for the current FlowPilot task
  after that user decision and after current route allocation;
- if the user chose single-agent continuity, the reviewer must verify explicit
  fallback authorization and must not claim live subagents.

The startup PM-review model now tracks `live_agents_active` and detects
`reviewer_clean_accepts_underfilled_live_subagents`. Validation reran with:

```powershell
python -m py_compile simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py
python simulations\run_startup_pm_review_checks.py
python scripts\check_install.py
python scripts\smoke_autopilot.py
```

Results: startup PM-review, install check, and smoke autopilot passed.

### 2026-05-02 Follow-Up - Per-Invocation Run Directory Isolation

FlowPilot startup now models and documents a fresh target-project run directory
for every formal invocation:

- create `.flowpilot/runs/<run-id>/`;
- write `.flowpilot/current.json` as the active-run pointer;
- update `.flowpilot/index.json` as the run catalog for audit and Cockpit tabs;
- write mutable control state only under the active run root;
- when continuing previous work, write a prior-work import packet and treat old
  state, routes, agent IDs, screenshots, icons, and generated assets as
  read-only input evidence only.

The startup reviewer must now check current-run isolation and prior-work import
boundary before a clean report can open the PM startup gate. Meta, capability,
and startup PM-review models reject PM startup opening or work-beyond-startup
when the run directory, current pointer, run index, run-scoped control state,
top-level legacy quarantine, or prior-work import packet is missing.

Validation reran with:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts\flowpilot_paths.py scripts\flowpilot_user_flow_diagram.py scripts\flowpilot_busy_lease.py scripts\flowpilot_run_with_busy_lease.py scripts\flowpilot_lifecycle.py scripts\flowpilot_global_supervisor.py scripts\flowpilot_watchdog.py simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py
python simulations\run_startup_pm_review_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\check_install.py
python scripts\smoke_autopilot.py
python scripts\flowpilot_user_flow_diagram.py --root . --json
python scripts\flowpilot_busy_lease.py status --root . --json
python scripts\flowpilot_lifecycle.py --root . --mode pause --json
git diff --check
```

Results: startup PM-review, meta, capability, install, smoke, legacy-layout
path resolution, busy-lease status, lifecycle inventory, template JSON parse,
FlowGuard import, and whitespace checks passed.

### 2026-05-03 Follow-Up - Reviewer-Owned UI Walkthrough

The user identified a review-quality gap: UI screenshot QA, automated
interaction evidence, or worker reports could be mistaken for human-like
reviewer approval. FlowPilot now treats those artifacts as pointers only. For
UI, browser, desktop, rendered visual, localization, and interaction gates, the
reviewer must personally walk the surface or block/request more evidence.

The capability model now requires these UI review gates before rendered
aesthetic, divergence, and final verification closure:

- concept personal visual review and concept design recommendations;
- rendered UI personal walkthrough;
- click/keyboard reachability checks for required controls;
- text overlap/clipping, whitespace, density, crowding, hierarchy,
  readability, and responsive/window-size checks;
- reviewer design recommendations for PM routing.

Validation reran with:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py
python simulations\run_capability_checks.py
python simulations\run_meta_checks.py
python scripts\check_install.py
```

Results: capability model passed with 185422 states and 195906 edges; meta
model passed with 184421 states and 193501 edges; install/template checks
passed, including `templates/flowpilot/human_review.template.json`.

### 2026-05-03 Follow-Up - Officer-Owned Async FlowGuard Gates

The user identified a role-boundary and throughput gap: FlowGuard simulations
could still appear to be run by the main executor while the process/product
FlowGuard officers only approved existing outputs. FlowPilot now treats
FlowGuard model gates as officer-owned asynchronous gates when live background
roles are available.

The repaired protocol is:

- PM writes a modeling request with assigned officer roles, output root, answer
  shape, and main-executor parallel-preparation boundary;
- process/product FlowGuard officers author, run, interpret, and approve or
  block their own model reports;
- main executor may continue read-only context gathering, dependency inventory,
  and non-model evidence drafts while models run, but cannot freeze routes,
  implement protected work, checkpoint, complete, or claim model approval from
  its own command output;
- officer reports must include model author, runner, interpreter, commands run
  by officer, input snapshots, model files, state/edge counts, counterexample
  or missing-label inspection, blindspots, and decision.

Validation reran with:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile .flowpilot\task-models\actor-authority-flow\model.py .flowpilot\task-models\actor-authority-flow\run_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py
python .flowpilot\task-models\actor-authority-flow\run_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results: actor-authority checks passed with 29 states and 28 edges and caught
new hazards for missing PM modeling request, gated main-executor parallel work,
and report-only officer approval. Meta checks passed with 184427 states and
193507 edges. Capability checks passed with 190728 states and 201212 edges.

### 2026-05-03 Follow-Up - Universal Adversarial Role Approval

The user identified that the UI reviewer fix and officer-owned FlowGuard fix
were both instances of a broader approval-quality gap: any PM, reviewer, or
FlowGuard officer approval can become weak if it merely reads a completion
report or another role's evidence packet.

FlowPilot now treats every role approval as an independent adversarial
validation gate:

- reports, screenshots, logs, and role outputs are evidence pointers only;
- the approving role must personally check direct sources, files, screenshots,
  state fields, model outputs, route/frontier/ledger entries, or live behavior
  relevant to the gate;
- the approving role must record adversarial hypotheses tested, concrete
  evidence references, commands or probes run when applicable, residual
  blindspots, and a decision;
- completion-report-only approval is invalid for startup PM opening, material
  intake, product architecture, child-skill manifests, FlowGuard model gates,
  implementation/human review, composite backward review, final product replay,
  and the final route-wide PM ledger approval.

Validation reran with:

```powershell
python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py
python simulations\run_startup_pm_review_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results: startup PM-review passed with 442 safe states and 441 edges, including
the `pm_opens_without_independent_gate_audit` hazard. Meta model passed with
208227 states and 217307 edges. Capability model passed with 202980 states and
213464 edges. All three had zero invariant failures, zero missing labels, zero
stuck states, and no nonterminating components where applicable.

### 2026-05-03 Follow-Up - Local Skill Inventory Before PM Skill Selection

Trigger: the user clarified that FlowPilot should inventory locally available
skills and host capabilities early, but the project manager should decide which
skills actually serve the product only after product-function architecture and
capability mapping.

Decision: `use_flowguard`.

Modeled risk:

- the material packet omits local skills that could materially affect route
  planning;
- raw local skill availability is treated as authority to invoke a child skill;
- child-skill discovery starts before the PM classifies candidates as
  required, conditional, deferred, or rejected;
- the PM approves a child-skill gate manifest before PM skill selection exists.

Protocol changes:

- material intake now includes a candidate-only local skill and host capability
  inventory;
- added `local_skill_inventory.template.json`;
- added `pm_child_skill_selection.template.json`;
- child-skill route discovery now proceeds only from PM-selected skills, not
  from raw local availability.

Validation:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python scripts\check_install.py
python scripts\smoke_autopilot.py
git diff --check
```

Results: FlowGuard import reported schema `1.0`. Meta checks passed with
292707 states, 305707 edges, zero invariant failures, zero missing labels, zero
stuck states, and no nonterminating components. Capability checks passed with
245702 states, 258706 edges, zero invariant failures, zero missing labels, zero
stuck states, and no nonterminating components. Installation checks and
autopilot smoke checks passed. `git diff --check` reported only existing
Windows line-ending warnings, with no whitespace errors.

Finding: the first meta-model rerun exposed an over-broad checkpoint invariant
for the FlowPilot skill-improvement observation check. The checkpoint action
correctly reset current-node execution gates for the next node, but the
invariant treated any written checkpoint with the reset gate as a failure. The
invariant is now scoped to the `checkpoint_pending` path, so it still rejects
checkpoint writes before the PM observation check without rejecting the
post-checkpoint next-node reset.

The protocol-level invariant is that skill inventory is early descriptive
material, while child-skill execution requires PM selection and the existing
child-skill fidelity gates.

### 2026-05-03 Follow-Up - Major Node Route Sign Display

Trigger: the user observed that a real FlowPilot run displayed the route sign
on the first node but did not keep showing it on later major route-node entry.

Decision: `use_flowguard`.

Modeled risk:

- startup display passed, but later ordinary major route-node entry was not
  classified as a chat-display trigger;
- `chat_displayed_in_chat` could be treated as true from a generated display
  packet rather than from the exact Mermaid block appearing in the assistant
  message;
- internal subnodes or heartbeat ticks could be confused with major route-node
  entries.

Protocol and model changes:

- added `major_node_entry`, `parent_node_entry`, `leaf_node_entry`, and
  `pm_work_brief` as explicit user-flow diagram display triggers;
- kept `key_node_change` as a legacy alias;
- clarified that major node means an effective node in the current
  `flow.json`/mainline, not a current subnode, micro-step, or heartbeat tick;
- clarified that generated files, Markdown previews, and display packets do
  not satisfy closed-Cockpit chat display until the Mermaid block is actually
  pasted in the assistant message;
- added a `major_node_entry_not_classified` hazard to the user-flow diagram
  model.

Validation:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts\flowpilot_user_flow_diagram.py simulations\user_flow_diagram_model.py simulations\run_user_flow_diagram_checks.py scripts\check_install.py
python simulations\run_user_flow_diagram_checks.py
python scripts\flowpilot_user_flow_diagram.py --root . --trigger major_node_entry --markdown --json
python scripts\check_install.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Results: FlowGuard import reported schema `1.0`. User-flow diagram checks
passed with 72 states and 71 edges, all required trigger labels present, and
the new major-node classification hazard detected. Meta checks passed with
292707 states and 305707 edges. Capability checks passed with 245702 states and
258706 edges. No invariant failures, missing labels, stuck states, or
nonterminating components were reported.
