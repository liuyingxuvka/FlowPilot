# Failure Modes

The FlowGuard models for FlowPilot found or guard against:

- premature completion;
- target drift;
- low-standard formal route created after FlowPilot activation;
- hidden self-interrogation evidence with no visible user-facing transcript;
- full grill-me rounds with fewer than 100 questions per active layer;
- full grill-me rounds that hit the question count but over-focus
  on one layer, such as UI, while skipping functional, state, implementation,
  validation, recovery, or delivery/showcase questions;
- focused grill-me repeated against the same scope without stale evidence,
  route mutation, or impact bubbling;
- focused grill-me replaced by either a full round at every tiny scope or a
  lightweight self-check that is too shallow for a phase, group, module, leaf
  node, or child-skill boundary;
- lightweight self-checks treated as formal grill-me evidence;
- route progress hidden in `.flowpilot/` with no visible user flow diagram while
  the Cockpit UI is unavailable;
- user flow diagrams that invent a new execution path, or mix superseded routes
  into the primary current view instead of treating them as history;
- user flow diagram display after route mutation uses an old Mermaid artifact
  instead of refreshing from the rechecked route and execution frontier;
- formal chunks that begin before the current node roadmap is visible in chat;
- continuation records written without automated heartbeat health when
  supported or manual-resume readiness checks when unsupported;
- FlowPilot assumes every host supports real wakeups and blocks or creates
  fake heartbeat evidence in hosts such as generic CLI or VS Code agents that
  expose no automation interface;
- host continuation capability is not probed before heartbeat/watchdog/global
  supervisor setup;
- heartbeat is created while the paired watchdog or singleton global
  supervisor is missing, leaving a half-protected automation state;
- host does not support real wakeups but FlowPilot still creates heartbeat,
  watchdog, or global-supervisor automation;
- host does not support real wakeups and FlowPilot treats that as skill
  failure instead of recording `manual-resume` fallback evidence;
- heartbeat automation prompt rewritten for ordinary route/plan changes instead
  of using a stable launcher that reads persisted execution frontier state;
- route mutation or next-jump change leaves `execution_frontier.json` or the
  visible Codex plan projection stale;
- heartbeat recovery asks the project manager for only one current gate, so the
  resumed run walks for one or two minutes and stops instead of receiving a
  completion-oriented runway;
- project manager resume output is not synced into the visible Codex plan
  projection before the main executor starts work;
- FlowPilot writes PM runway evidence under `.flowpilot/` but does not call
  the host native plan tool, such as Codex `update_plan`, even though the tool
  exists and the user can see a stale desktop plan;
- the visible plan is updated as a one-step current-gate list instead of a
  downstream runway toward completion, causing sleep/wake cycles after every
  tiny gate;
- continuation resumes after interruption and jumps to `next_node` while
  `active_node` is still unfinished;
- continuation resumes an unfinished node, writes a future-facing "continue to
  next gate" decision, and stops without executing the persisted `next_gate` or
  recording a concrete blocker;
- host automation marked active while heartbeat evidence stops advancing and no
  external stale-heartbeat watchdog records the gap;
- external watchdog writes only local evidence and leaves no user-level global
  record for cross-project stale-event review;
- external watchdog reset evidence misreported as guaranteed recovery before a
  later heartbeat proves that the automation fired again;
- external watchdog treats live subagent busy state as a reset-decision source,
  or omits source-status/drift warnings for stale state/frontier/lifecycle
  evidence;
- duplicate user-level global supervisors process the same stale queue;
- a local chat, route, or project disables the user-level global supervisor
  instead of unregistering only its own project record;
- global stale-event processing resets a heartbeat without rereading
  project-local state and watchdog evidence;
- a Windows or external global task is treated as the official reset actor even
  though only Codex automation can reset Codex heartbeat automations;
- route decided before FlowGuard process design;
- formal route work starts before the fixed six-agent crew is created,
  restored, and persisted in `crew_ledger.json`;
- heartbeat recovery reads state but does not restore or replace the six-agent
  crew before asking the project manager what to do next;
- heartbeat recovery assumes stored subagent ids still have live private
  context and asks the project manager before loading role memory packets;
- an unavailable role is replaced from a generic prompt instead of the latest
  `.flowpilot/runs/<run-id>/crew_memory/` packet;
- meaningful role work updates only a report path or raw transcript but does
  not refresh the compact role memory packet before checkpoint;
- a raw chat transcript is treated as the authoritative role memory instead of
  structured role memory fields;
- role identity is conflated so raw `agent_id` becomes the user-facing label or
  the authority key instead of diagnostic-only recovery evidence;
- main executor decides the next route jump directly instead of asking the
  project manager;
- main executor authors or runs FlowGuard model files for an officer, turning
  the officer into an approval-only stamp;
- project manager, reviewer, or FlowGuard officer performs implementation work
  instead of keeping role authority separate;
- route mutation after a blocking review is written without project-manager
  repair-strategy interrogation, repair decision, stale-evidence invalidation,
  and frontier rewrite;
- route or implementation proceeds with only a development-process model and no
  product-function model for the target behavior;
- parent or leaf execution starts before the corresponding product-function
  model is checked;
- technical evidence such as test success, screenshot existence, or app launch
  is treated as product acceptance without human-like inspection;
- human-like inspection finds a blocking issue but the route continues without
  issue grilling, route mutation, repair modeling, repair evidence, and
  same-inspector recheck;
- repair work starts or closes without its own development-process model and
  product-function model;
- parent or final backward review is skipped, so composed product defects are
  missed after local node checks pass;
- final completion uses the initial checklist or last local review instead of
  a PM-built dynamic route-wide gate ledger from the current route;
- route mutation, inserted repair nodes, or superseded nodes are not reflected
  in the final ledger before completion;
- child-skill gates that passed locally are not collected into the final
  route-wide ledger for terminal replay;
- stale or invalidated evidence still closes a current-route obligation in the
  final ledger;
- superseded nodes lack replacement, waiver, or no-longer-effective
  explanations in the final ledger;
- final human-like reviewer approves completion before the project manager
  builds the final route-wide ledger;
- project manager records completion approval before final ledger unresolved
  count is zero and before human-like backward replay;
- non-leaf parent/module/group closes merely because each child passed locally,
  without a composite backward human-like review against the parent goal;
- composite backward review finds a parent rollup gap, but the route does not
  structurally return to an affected child, insert a sibling child, rebuild the
  child subtree, or bubble the impact to the next parent;
- a structural route repair leaves old implementation or child evidence marked
  valid before the changed route, frontier, visible plan, and affected child
  work are rechecked;
- child skill named but its `SKILL.md` and relevant references were not read;
- route modeled before the project manager extracts a child-skill gate
  manifest from the loaded skill files;
- child-skill gates enter the route without required approver roles and
  forbidden approvers;
- the main executor treats its own draft evidence as child-skill gate approval;
- node-level child-skill execution starts from the startup manifest without PM
  current-node refinement;
- child skill workflow collapsed into a weaker FlowPilot shorthand;
- child skill invoked without a visible mini-route of key milestones;
- capability marked complete without mapping the child skill's completion
  standard into route gates;
- required child-skill step skipped without an explicit reason, waiver, or
  blocker;
- formal chunk execution without verification;
- formal chunk execution without focused parent-scope grill-me, parent-subtree
  FlowGuard review, focused node-level grill-me, or lightweight heartbeat
  self-check;
- formal chunk execution without the reusable quality package;
- quality package treated as an empty pass with no typed result for thinness,
  improvement classification, child-skill visibility, validation strength, and
  rough-finish risk;
- repeated "raise the standard" questioning of the same candidate instead of
  classifying it as small, medium, large, or not doing with reason;
- checkpoint written before anti-rough-finish review;
- high-risk gate overlap with active work;
- stale route continuing after model gap;
- stale implementation reused after a completion review raised the standard;
- sidecar subagent returned but not merged;
- parent/module-level subagent scan treated as permission to assign work;
- subagent assigned ownership of a child node, checkpoint, route advancement,
  or completion decision;
- new subagent spawned while a suitable idle subagent was available;
- UI implementation before the relevant UI child-skill gates and evidence;
- post-implementation rendered QA evidence substituted for the child skill's
  pre-implementation concept-target/reference decision;
- an `imagegen` output accepted as a concept target based on source alone even
  though the content is an existing screenshot, existing-image variant, desktop
  capture, old route UI, taskbar-inclusive capture, or prior failed UI evidence
  with cosmetic changes;
- human-like inspection jumps directly to pass/fail without first recording
  what the artifact, screenshot, output, or exercised feature actually appears
  to be;
- UI concept targets, rendered UI screenshots, app icons, or product-facing
  visual assets pass without an explicit aesthetic verdict and concrete
  reasons;
- a failed or weak aesthetic review is treated as a soft note while
  implementation, checkpoint, package polish, or completion keeps moving;
- a blocking review is recorded as evidence but the route keeps moving without
  marking the failed child stale, incrementing the route, and moving the
  frontier to a reset or inserted repair child;
- UI implementation started before the child skill's concept-target decision
  was shown or explicitly waived;
- one-shot UI concept work followed by local tweaks without a recorded
  child-skill loop-closure decision;
- child-skill visual differences observed but not closed by that skill's
  divergence process;
- delivered UI evidence does not match the route's intended delivery surface;
- product-facing visual assets accepted without UI child-skill evidence;
- non-UI routes accidentally invoking UI-only gates;
- completion before final feature matrix, acceptance matrix, and
  quality-candidate reviews;
- completion while obvious high-value work remains;
- no-progress recovery loops.

Keep these failure modes in the model and tests.

## Required Guard Shape

- Completion checks must use historical gate evidence, not only the current
  running-state helper.
- A formal FlowPilot route must start from the showcase-grade floor; do not add
  a lower default tier.
- Full grill-me runs at formal boundaries only: startup, route mutation or
  standard expansion, and completion review.
  It must be user-visible, persisted as evidence, contain at least 100
  questions per active layer, and cover the full layer matrix:
  goal/acceptance, functional capability, data/state/source of truth,
  implementation strategy, UI/UX when relevant, validation/QA,
  recovery/heartbeat, and delivery/showcase/public-boundary quality.
- Startup full grill-me seeds the frozen floor, improvement candidate pool, and
  initial validation direction in one round. Do not add separate immediate
  post-freeze interviews for the same topics.
- Focused grill-me runs at phase, group, module, leaf-node, and child-skill
  boundaries with 20-40 questions by default and up to 50 for complex
  boundaries. It must record the scope id, local ambiguity, child-skill gates,
  validation needs, unchanged cross-layer impacts, and parent impact-bubbling
  decisions.
- Lightweight self-check runs at continuation micro-steps with 5-10 targeted
  questions and cannot satisfy a full or focused grill-me gate.
- Until the Cockpit UI is available, chat is the temporary cockpit: emit user
  flow diagrams, simulated next jumps, checks, fallback exits, continuation
  state, and acceptance delta at startup, route updates, and node transitions.
- Treat the user flow diagram as a projection of canonical `.flowpilot` state:
  current route first, current node and next checks second, superseded route
  history third.
- Refresh `.flowpilot/runs/<run-id>/diagrams/user-flow-diagram.mmd` from the checked
  route/frontier before showing chat or UI progress, especially after route
  mutation. Raw FlowGuard Mermaid exports stay off by default and are generated
  only on explicit request.
- FlowPilot must probe host continuation capability before route execution. If
  real wakeups are supported, create the automated continuation bundle as one
  lifecycle setup: stable heartbeat, paired watchdog, singleton global
  supervisor, and hidden/noninteractive watchdog evidence when applicable. If
  real wakeups are unsupported, record `manual-resume` fallback evidence and do
  not create heartbeat/watchdog/global-supervisor automation.
- Heartbeat must include real host continuation when available and a health
  check before each formal node. Manual-resume mode must include state/frontier
  freshness evidence instead of claiming unattended recovery.
- Heartbeat automation should stay a stable launcher. Route version, active
  node, next node, current mainline, fallback, checks-before-advance, and
  visible plan projection live in `.flowpilot/runs/<run-id>/execution_frontier.json`.
- Route mutations must recheck the affected model, rewrite the execution
  frontier, sync the visible Codex plan from that frontier, and only then
  resume behavior-bearing work.
- `next_node` is a future jump, not the current execution target, until the
  frontier current-node completion guard sets `advance_allowed: true`.
- While the active node is unfinished, heartbeat evidence must name and execute
  the persisted `current_subnode` or `next_gate`, or record a concrete blocker.
  A heartbeat may not close by only writing "continue to X" when the next gate
  is still executable.
- Multi-hour routes on hosts with real wakeups should record an external
  watchdog policy. A watchdog may detect stale heartbeats, require an official
  Codex app automation reset (`PAUSED -> ACTIVE`), and write
  `.flowpilot/runs/<run-id>/watchdog/` evidence. It must not mutate `automation.toml`
  directly, and a reset is not proof of recovery until a later heartbeat
  appears. Unsupported hosts record `manual-resume` and skip watchdog/global
  supervisor setup entirely.
- External watchdogs should also write compact user-level global records under
  `$FLOWPILOT_GLOBAL_RECORD_DIR` or `$CODEX_HOME/flowpilot/watchdog`. The global
  registry is an index; project-local watchdog evidence remains authoritative.
- Watchdog reset decisions trust only active-run `state.json`, latest heartbeat evidence,
  and `busy_lease.json`. Frontier, lifecycle, automation, and global records
  are diagnostic drift signals; live subagent busy state is not inspected.
- PM-initiated FlowGuard modeling must not be vague delegation. If PM asks a
  FlowGuard officer to model an uncertain route, product, object, file format,
  protocol, or repair decision, the request names the decision, uncertainty,
  evidence, candidate options or option-generation need, assigned officer, and
  required answer shape. The officer checks modelability first; missing
  evidence creates evidence work, over-broad requests split, and only an
  actionable report can feed PM route decision.
- The user-level global supervisor must be singleton Codex app cron automation.
  Verify it in the same setup step that creates or repairs heartbeat and
  watchdog. Reuse one active automation, update one paused singleton to
  `ACTIVE` when global protection is required, and reject or exit duplicate
  startup attempts unless a human explicitly forces replacement. The fixed
  creation shape uses `kind: cron`, `rrule: FREQ=MINUTELY;INTERVAL=30`, `cwds`
  as one workspace string path, `executionEnvironment: local`,
  `reasoningEffort: medium`, and `status: ACTIVE`. Each heartbeat refreshes
  this project's global registration lease. Pause, stop, and completion
  unregister only the current project; the user-level global supervisor is
  deleted last only after a locked registry reread confirms no active,
  unexpired registrations remain.
- The global supervisor must reread project-local state and watchdog evidence,
  expire terminal/manual-stop records, supersede old route generations, and
  dedupe repeated stale events before recording a reset requirement.
- The watchdog policy is lifecycle state, not node-local state. Checkpoints,
  node transitions, user-flow-diagram refreshes, and visible plan syncs must not
  recreate, re-register, start, restart, or re-enable the paired watchdog
  automation. Visible command windows during normal node advance indicate a
  lifecycle reset or task configuration bug.
- Windows watchdog scheduled tasks must be hidden/noninteractive. A direct
  interactive `python.exe` action is a failure risk because it can flash a
  console window even when the task is not being recreated.
- Pause, restart, and terminal cleanup must scan all lifecycle authorities:
  Codex automations, global supervisor records, Windows scheduled tasks, local
  state, execution frontier, and watchdog evidence. Disabled Windows FlowPilot
  tasks are still residual objects until unregistered or explicitly waived.
- Every invoked child skill must pass a fidelity gate: load its contract, map
  its workflow and completion standard into route gates, show the child-skill
  mini-route, write the evidence checklist, and verify completion against the
  source skill before capability close.
- FlowPilot must not treat a child skill name as enough evidence. The evidence
  must show required source-skill steps, loaded or skipped references, output
  paths, skipped-step reasons, and final completion decision.
- FlowGuard must design the route before implementation and then check the
  route after design changes.
- The quality package is mandatory before formal chunks and implementation. It
  records thinness, candidate classification, child-skill mini-route
  visibility, validation strength, and rough-finish risk.
- Medium or large quality candidates require route mutation and FlowGuard
  recheck; small candidates may stay in the current node; rejected candidates
  need reasons.
- Anti-rough-finish review must pass before checkpoint or completion closure.
- After anti-rough-finish review, human-like inspection must load product
  context, run manual/product-style experiments where possible, and pass before
  checkpoint or completion closure.
- Every meaningful route scope must have both a development-process model and
  a product-function model. FlowGuard enforces the state transitions; the AI
  inspector judges product quality and writes evidence-backed issues.
- Blocking inspection issues must be grilled into specific repairable records,
  mutate the route into repair nodes, run repair process/product models, and
  close only after same-inspector recheck passes.
- Every non-leaf parent/module/group must run composite backward review before
  closure. The review must replay child evidence against the parent product
  model, inspect whether children compose into the parent goal, and on failure
  mutate the route to an affected existing child, an adjacent sibling child, a
  rebuilt child subtree, or a bubbled parent impact. Old child/parent evidence
  becomes stale until the changed child/subtree passes and the parent backward
  review reruns.
- Final completion review must reconcile feature matrix, acceptance matrix, and
  quality candidates, replay the product-function model, and pass final
  human-like inspection before final self-interrogation closes the route.
- Completion self-interrogation must either exhaust obvious high-value work or
  force a route update, recheck, rework, and reverification.
- Before terminal completion, the project manager must rebuild the final
  route-wide gate ledger from the current route, not from the initial route.
  It must account for effective nodes, superseded nodes, child-skill gates,
  human-review gates, product/process model gates, generated-resource lineage,
  stale evidence, waivers, blockers, and unresolved items. Completion is
  blocked until unresolved count is zero, every generated resource has a
  consumed/final-output/evidence/superseded/quarantined/discarded disposition,
  the human-like reviewer has replayed the ledger backward from the final
  product, and the PM has approved the clean ledger.
- Child-node sidecar scan is the only formal subagent opportunity gate. Parent
  or module review may not directly spawn subagents or transfer node ownership.
- Sidecar scope checking must be separate from reuse-or-spawn assignment.
- `sidecar_report_returned` is not completion evidence; main-agent merge and
  verification are required.
- Formal routes create a persistent six-agent crew: project manager,
  human-like reviewer, process FlowGuard officer, product FlowGuard officer,
  worker A, and worker B. The project manager owns route, heartbeat-resume,
  completion-runway, PM stop, repair, and completion decisions; workers are
  sidecars only.
- Heartbeat recovery loads the crew ledger and role memory packets,
  restores/replaces the crew from that memory, asks the project manager for a
  completion-oriented runway, syncs that runway into the visible plan, executes
  at least the current gate when executable, then continues until a PM stop
  signal, hard gate, blocker, route mutation, or real execution limit stops
  progress.
- Completion must archive the crew ledger and role memory packets after
  lifecycle reconciliation.
- Idle subagents are a reusable pool, not proof that the current child node has
  already been scanned.
- A model gap forces route update, model recheck, and summary resync before more
  formal work.
- UI capability gates must be unreachable on backend-only routes.
- UI routes must route detailed design, concept, visual QA, and implementation
  polish through the appropriate child skills instead of duplicating those
  prompts in FlowPilot.
- Concept-led UI routes must record the source skill's pre-implementation
  concept-target/reference decision before implementation; rendered QA evidence
  after implementation is not a substitute unless the child skill or user
  explicitly waived the concept target.
- Generated concept targets need two gates: source and authenticity. Source
  verifies imagegen or authoritative user reference. Authenticity verifies the
  target is an independent concept, not a reused screenshot, screenshot
  variant, desktop capture, old route UI, taskbar-inclusive capture, or prior
  failed UI evidence. Authenticity failure mutates the route back to clean
  concept regeneration.
- Human-like review needs a pre-judgement observation record. The reviewer must
  first say what is visibly or behaviorally present, then use that observation
  to support the later pass, fail, or more-evidence decision.
- UI concept, rendered UI, app icon, and product-facing visual asset reviews
  also need an aesthetic judgement after neutral observation. The reviewer
  records `aesthetic_verdict` as `pass`, `weak`, or `fail` with concrete
  reasons. A failed aesthetic verdict routes to repair or regeneration and
  blocks implementation, checkpoint, package polish, and completion.
- Failed review gates are strict route mutations. Reset the same child only
  when its scope covers the finding; otherwise insert repair/regeneration
  sibling nodes or split into multiple focused children. Old failed evidence
  remains as history but is stale for closure.
- After rendered QA, FlowPilot requires the child skill's loop-closure evidence
  for material differences, but the child skill owns the detailed divergence
  rules.
- App icons and product-facing visual assets must be included in UI
  child-skill evidence before UI/desktop completion can be claimed.
- Backend routes must not complete without implementation and final
  verification evidence.

When a new failure class appears, update the smallest relevant model first,
preserve the counterexample, then patch the protocol or implementation.
