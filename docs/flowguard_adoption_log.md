# FlowGuard Adoption Log

This human-readable log summarizes FlowGuard adoption records for major protocol changes.
Machine-readable entries live in `.flowguard/adoption_log.jsonl`.

## 2026-05-02 - Resource Output Lineage

- Trigger: the user asked to rerun FlowPilot through FlowGuard and identify
  work that gets done but never reaches final output, such as generated images
  that are never used.
- Decision: `use_flowguard`.
- Models updated: `.flowpilot/task-models/resource-output-lineage/`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Concept authenticity and stale visual evidence were already covered, but
    generated-resource output lineage was not a first-class final-ledger gate.
  - Generated concept images, visual assets, screenshots, route diagrams, model
    reports, and similar artifacts now need a disposition before completion:
    consumed, final-output, evidence, superseded, quarantined, or discarded
    with reason.
  - The targeted model reproduced eight waste hazards, including imagegen work
    that is generated but never consumed and ledgers that claim zero unresolved
    resources before disposition.
- Validation:
  - `python .flowpilot\task-models\resource-output-lineage\run_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`

## 2026-05-02 - PM-Initiated FlowGuard Delegation

- Trigger: the project manager should be able to proactively use FlowGuard as a
  modeling tool for uncertain route, repair, feature, product-object,
  file-format, protocol, or validation decisions.
- Decision: `use_flowguard`.
- Models updated: `.flowpilot/task-models/pm-flowguard-delegation/`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - PM modeling requests must name the decision, uncertainty, evidence,
    candidate options or option-generation need, assigned officer, and answer
    shape.
  - The process FlowGuard officer handles "how should FlowPilot do this?"
    uncertainty; the product FlowGuard officer handles "what is the target
    object/product behavior?" uncertainty.
  - The assigned officer checks modelability first.
  - Missing evidence becomes evidence-collection work; over-broad requests
    become split modeling requests.
  - Reports must include coverage, blindspots, failure paths, recommendation,
    confidence, next smallest executable action, and route mutation candidate.
  - PM synthesis remains the route decision.
- Validation:
  - `python .flowpilot\task-models\pm-flowguard-delegation\run_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`

## 2026-05-02 - Control Surface Protocol Patches

- Trigger: the watchdog must not inspect unreliable background-agent busy state, and FlowPilot needed the four protocol patches for local busy leases, Mermaid route maps, role identity, and source drift evidence.
- Decision: `use_flowguard`.
- Models updated: `.flowpilot/task-models/control-surface-protocol-patches/`, `.flowpilot/task-models/external-watchdog-loop/`, `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Long operations now require the busy-lease wrapper policy and terminal checkpoints require cleared leases.
  - Watchdog decisions trust only `state.json`, latest heartbeat evidence, and `busy_lease.json`.
  - `execution_frontier.json`, lifecycle records, automation metadata, and global records are diagnostic drift signals only.
  - Live subagent busy state is explicitly not inspected.
  - Visible route maps must be backed by refreshed Mermaid artifacts after route creation or mutation.
  - Role identity is split into `role_key`, `display_name`, and diagnostic-only `agent_id`.
- Validation:
  - `python .flowpilot\task-models\control-surface-protocol-patches\run_checks.py`
  - `python .flowpilot\task-models\external-watchdog-loop\run_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`
  - `python scripts\flowpilot_watchdog.py --root . --dry-run --json`
  - `python scripts\flowpilot_run_with_busy_lease.py --root . --operation "wrapper smoke" --max-minutes 1 --json -- python -c "print('lease-wrapper-ok')"`

## 2026-05-02 - Global Supervisor Lifecycle

- Trigger: user-level global supervisor checks were creating too many Codex conversations, and the user requested the agreed fixed 30-minute design rather than the earlier quiet thread-bound draft.
- Decision: `use_flowguard`.
- Models updated: `.flowpilot/task-models/global-reset-supervisor/`, `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - The user-level global supervisor cadence is fixed at 30 minutes and is not configurable.
  - Heartbeat mode refreshes a per-project active registration lease before global supervisor singleton setup.
  - Pause, stop, completion, terminal state, manual stop, missing project state, unreadable project state, and expired leases make a project ineligible for reset.
  - Teardown order is project unregister first, project watchdog/heartbeat shutdown next, and user-level global supervisor deletion last only after empty-registry confirmation.
  - The first model pass caught an ordering bug where terminal event expiry could delete the global supervisor while this project registration was still active; the terminal path now unregisters first.
- Validation:
  - `python .flowpilot\task-models\global-reset-supervisor\run_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python -m py_compile` on touched Python files
  - `python scripts\flowpilot_global_supervisor.py --status --json`
  - `python scripts\flowpilot_watchdog.py --root . --dry-run --json`
  - `python scripts\flowpilot_lifecycle.py --root . --json`
  - `python scripts\flowpilot_global_supervisor.py --refresh-registration --root . --heartbeat-automation-id flowpilot-route-021-stable-heartbeat --dry-run --json`
  - `python scripts\flowpilot_global_supervisor.py --unregister-project --root . --unregister-reason smoke --dry-run --json`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`
  - installed skill hash match plus quick validation

## 2026-05-02 - User Flow Diagram Display Policy

- Trigger: the user clarified that Mermaid-style diagrams are for users, not
  program execution; chat and Cockpit UI should show the same simple FlowPilot
  process diagram, while raw FlowGuard Mermaid state graphs should be off by
  default.
- Decision: `use_flowguard`.
- Models updated: `.flowpilot/task-models/control-surface-protocol-patches/`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - FlowPilot now has one user-facing flow diagram shared by chat and Cockpit
    UI.
  - The diagram is generated from route/frontier JSON, stays at 6-8 major
    stages, and highlights the current stage.
  - It refreshes at startup, key node changes, route mutation, completion
    review, or explicit user request, not every heartbeat.
  - Raw FlowGuard Mermaid exports are diagnostic only, disabled by default, and
    generated only on explicit request.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python -m py_compile scripts\flowpilot_user_flow_diagram.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py .flowpilot\task-models\control-surface-protocol-patches\model.py .flowpilot\task-models\control-surface-protocol-patches\run_checks.py`
  - `python scripts\flowpilot_user_flow_diagram.py --root . --json`
  - `python .flowpilot\task-models\control-surface-protocol-patches\run_checks.py`
  - `python scripts\check_install.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`

## 2026-05-02 - Resource Lineage Consumption Correction

- Trigger: the user clarified that UI concepts and screenshots are intermediate
  comparison inputs, not necessarily final deliverable assets.
- Decision: `use_flowguard`.
- Models reviewed: `.flowpilot/task-models/resource-output-lineage/`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Intermediate consumers count as valid use: implementation planning, concept
    divergence review, screenshot QA, aesthetic review, and repair-direction
    decisions.
  - Concept images and screenshots are not waste when they feed the
    `concept target -> implementation -> screenshot QA -> divergence review ->
    iteration closure` loop.
  - Missing per-file ledger evidence is an auditability gap, not proof of
    resource waste.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python .flowpilot\task-models\resource-output-lineage\run_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`

## 2026-05-02 - Optional Heartbeat Manual Resume Notices

- Trigger: the user clarified that heartbeat/scheduled wakeups are optional and
  unsupported hosts must rely on manual resume, while every controlled
  nonterminal stop should tell the user how to continue.
- Decision: `use_flowguard`.
- Models updated: `simulations/meta_model.py` and
  `simulations/capability_model.py`.
- Main findings:
  - Manual-resume mode remains a first-class continuation path and does not
    require heartbeat/watchdog/global-supervisor automation.
  - The old heartbeat-health gate is now modeled as continuation readiness:
    automated heartbeat health when supported, or manual-resume
    state/frontier/crew-memory readiness when no real wakeup exists.
  - Controlled blocked exits must record a nonterminal resume notice; completed
    exits must record a completion notice instead of a resume prompt.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`
  - JSON parse check for `templates/flowpilot`, `.flowpilot`, and `.flowguard`

## 2026-05-02 - Startup Activation Hard Gate

- Trigger: the user found that a formal FlowPilot restart could bypass the
  intended startup crew, continuation, and route-state activation sequence.
- Decision: `use_flowguard`.
- Modeled workflow: startup activation from route file creation through
  canonical state/frontier sync, current six-role crew ledger, role memory,
  continuation readiness, startup guard pass, and first work beyond startup.
- Findings:
  - A route-local file without matching canonical state/frontier/crew evidence
    is a shadow route, not a valid partial startup.
  - Child-skill, imagegen, implementation, route chunk, and completion work are
    blocked until `startup_activation_guard_passed`.
  - Existing route-021 terminal local runtime correctly fails the new guard.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\run_startup_guard_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
  - `python scripts\check_install.py`
  - `python simulations\run_startup_guard_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\flowpilot_startup_guard.py --root . --route-id route-021 --json`

## 2026-05-02 - Live Subagent Startup Decision Gate

- Trigger: the user clarified that missing six live background agents should
  pause for an explicit user decision instead of silently falling back to
  memory-seeded role continuity.
- Decision: `use_flowguard`.
- Models updated: `simulations/startup_guard_model.py`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Formal FlowPilot startup now targets six live background agents by default.
  - `startup_activation.live_subagent_startup` must record either six live
    agents started/resumed or explicit single-agent role-continuity fallback.
  - Startup guard rejects fallback without a recorded user decision.
  - Meta and capability models require live-subagent startup resolution before
    `startup_activation_guard_passed`.
- Validation:
  - `python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\run_startup_guard_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
  - `python scripts\check_install.py`
  - `python simulations\run_startup_guard_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`

## 2026-05-02 - FlowPilot Installer And Public Release Tooling

- Trigger: the user approved a FlowPilot-only installer, dependency manifest,
  and public release preflight while explicitly rejecting automatic publishing
  of companion skills.
- Decision: `use_flowguard`.
- Modeled workflow: dependency manifest, installer, FlowPilot-only release
  preflight, host capability mapping, dependency source checks, privacy scan,
  validation, and release preparation.
- Main findings:
  - Release tooling must never write, package, tag, push, upload, or publish
    companion skill repositories.
  - Existing skills are skipped by default; overwrites require explicit force
    and system skills are refused.
  - Host-specific tools such as image generation are capability mappings, not
    universal skill names. Codex maps `raster_image_generation` to `imagegen`;
    other hosts can record a different provider.
  - Public release remains blocked until GitHub sources are filled for
    GitHub-backed companion skills.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python -m py_compile scripts\install_flowpilot.py scripts\check_public_release.py scripts\check_install.py scripts\smoke_autopilot.py simulations\release_tooling_model.py simulations\run_release_tooling_checks.py`
  - `python simulations\run_release_tooling_checks.py`
  - `python scripts\install_flowpilot.py --check --json`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`
  - `python scripts\check_public_release.py --skip-url-check --json`

## 2026-05-02 - Three-Question Stop-And-Wait Startup Gate

- Trigger: the user simplified formal startup: `Use FlowPilot` / `使用开始`
  asks three questions first, then the assistant must stop and wait for the
  user's reply before the banner or any background work.
- Decision: `use_flowguard`.
- Models updated: `simulations/startup_guard_model.py`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Startup invocation now opens only `startup_pending_user_answers`.
  - `startup_activation.startup_questions.dialog_stopped_for_user_answers`
    records the hard pause after the prompt.
  - The startup guard rejects answers recorded without that stop-and-wait
    evidence, rejects inferred/default/prior-route answers, and rejects
    `single_message_invocation` as a startup answer source.
  - The banner, route files, child skills, subagents, heartbeat probes, imagegen,
    implementation, and route chunks remain blocked until the later user reply
    supplies all three answers and the startup guard passes.
- Validation:
  - `python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\run_startup_guard_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
  - JSON parse check for `templates/flowpilot/state.template.json`,
    `templates/flowpilot/execution_frontier.template.json`, and
    `templates/flowpilot/mode.template.json`
  - `python simulations\run_startup_guard_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`


## flowpilot-explicit-opt-in-trigger-20260502 - Make FlowPilot skill activation explicit opt-in only

- Project: FlowPilot development repository
- Trigger reason: User requested that FlowPilot only be used when they explicitly say to use the skill, and not because a task is substantial or a .flowpilot directory exists.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-02T17:48:17+00:00
- Ended: 2026-05-02T17:48:17+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/capability_model.py
- simulations/meta_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python -m py_compile simulations/meta_model.py simulations/run_meta_checks.py simulations/capability_model.py simulations/run_capability_checks.py`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python scripts/install_flowpilot.py --check --json`

### Findings
- FlowPilot skill metadata and default activation now say opt-in only; .flowpilot is continuity state after explicit invocation, not an implicit trigger.
- Installed global FlowPilot skill and repository source skill were updated consistently; the duplicate global backup copy was also adjusted so it no longer advertises broad automatic activation.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- No new targeted FlowGuard model was added; existing meta and capability route models were rerun because this was a narrow trigger-policy documentation and skill-metadata change.

### Next Actions
- Future installs should preserve the opt-in-only FlowPilot description unless the user explicitly asks to restore implicit activation.


## flowpilot-startup-review-pm-gate-20260502 - PM-owned startup gate with reviewer report

- Project: FlowPilot development repository
- Trigger reason: User clarified that the human-like reviewer should audit startup evidence and report to PM, while PM owns the startup gate and sends blockers back to workers until rechecked.
- Status: completed
- Skill decision: use_flowguard
- Models updated: `simulations/startup_guard_model.py`, `simulations/meta_model.py`, `simulations/capability_model.py`.

### Modeled Risks
- Reviewer directly opens the startup gate.
- PM opens the gate without a clean reviewer report.
- PM opens while reviewer blockers are still assigned for worker remediation.
- Worker remediation is accepted without reviewer recheck.
- A clean-start request proceeds while old route or old asset cleanup evidence is missing.

### Commands
- `python -m py_compile scripts\flowpilot_startup_guard.py simulations\startup_guard_model.py simulations\meta_model.py simulations\capability_model.py simulations\run_startup_guard_checks.py simulations\run_meta_checks.py simulations\run_capability_checks.py`
- `python simulations\run_startup_guard_checks.py`
- `python simulations\run_meta_checks.py`
- `python simulations\run_capability_checks.py`
- `python scripts\check_install.py`
- `python scripts\flowpilot_startup_guard.py --help`

### Findings
- Startup now has three separate records: reviewer report, PM start-gate decision, and final startup guard pass.
- `--write-review-report` writes `.flowpilot/startup_review/latest.json` without opening the gate.
- `--record-pm-start-gate open` records PM ownership from the current clean report.
- `--record-pass` requires the PM-owned open decision before writing `work_beyond_startup_allowed: true`.
- The startup guard model detects the new bypass hazards; meta and capability models pass with no invariant failures, missing labels, stuck states, or nonterminating components.

### Skipped Steps
- Did not sync the installed Codex skill copy because another agent owns the FlowPilot trigger-condition changes in the same installed skill surface.


## flowpilot-remove-startup-guard-20260502 - Reviewer facts plus PM-only startup opening

- Project: FlowPilot development repository
- Trigger reason: User rejected a replacement startup review script and required deletion of the separate startup guard concept. Reviewer must check facts and report; PM is the only startup opener.
- Status: completed
- Skill decision: use_flowguard
- Models updated: `simulations/startup_pm_review_model.py`, `simulations/meta_model.py`, `simulations/capability_model.py`.

### Modeled Risks
- Reviewer accepts a 30-minute route heartbeat where route heartbeat must be one minute.
- Reviewer accepts Codex cron as the external watchdog instead of a Windows scheduled task.
- Reviewer accepts missing Windows watchdog task, missing global supervisor evidence, or missing global registry evidence.
- Reviewer writes a clean report without direct fact checks.
- Reviewer opens startup directly.
- PM opens without a clean factual report, opens a blocked report, or accepts worker remediation without reviewer recheck.
- Image generation, child-skill work, implementation, or route execution starts before PM opens startup.

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- `python -m py_compile simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
- `python simulations\run_startup_pm_review_checks.py`
- `python simulations\run_meta_checks.py`
- `python simulations\run_capability_checks.py`
- `python scripts\check_install.py`
- `python scripts\smoke_autopilot.py`
- `python scripts\check_public_release.py --skip-url-check`

### Findings
- The old runtime startup guard script and old startup guard simulation were removed rather than replaced with another runtime script.
- FlowGuard validation now lives in `startup_pm_review_model`; it is not a startup reviewer.
- Startup artifacts are now reviewer factual report plus PM startup gate.
- Meta and capability models now gate formal work on `work_beyond_startup_allowed` from the PM gate, with factual reviewer evidence required first.
- A repo-wide reviewer audit found material sufficiency and product architecture wording that could be read as packet-only review; both now require direct factual checks.
- Startup PM-review, release tooling, meta, capability, install, and smoke checks passed.
- Installed FlowPilot `SKILL.md` and `references/protocol.md` were synchronized so the next explicit FlowPilot invocation no longer sees the removed startup guard command.
- Public release preflight remained blocked only by existing missing dependency GitHub sources.

### Skipped Steps
- Did not run full forced installer overwrite because it would replace the entire installed skill directory. Only the checked skill entrypoints were synchronized.


## flowpilot-subagent-user-decision-review-20260502 - Startup reviewer binds subagent facts to user answer

- Project: FlowPilot development repository
- Trigger reason: User clarified that reviewer facts must be bound to user decisions, including subagent authorization.
- Status: completed
- Skill decision: use_flowguard
- Models updated: `simulations/startup_pm_review_model.py`.

### Findings
- Startup review templates now distinguish background-agent role evidence from the stronger requirement: user background-agent decision must match actual subagent state.
- If background agents are allowed, reviewer must verify six live role-bearing subagents started or resumed after the user decision.
- If single-agent continuity is selected, reviewer must verify explicit fallback authorization and must not claim live subagents.
- FlowGuard startup PM-review model now detects underfilled live-subagent startup.

### Commands
- `python -m py_compile simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py`
- `python simulations\run_startup_pm_review_checks.py`
- `python scripts\check_install.py`
- `python scripts\smoke_autopilot.py`

### Results
- Startup PM-review, install check, and smoke autopilot passed.


## flowpilot-fresh-subagents-per-new-task-20260502 - New FlowPilot tasks cannot reuse historical agent IDs

- Project: FlowPilot development repository
- Trigger reason: User identified that a new FlowPilot task had reused six historical background-agent IDs from old role memory. Every new formal FlowPilot task must create a fresh live-agent cohort when background agents are authorized.
- Status: completed
- Skill decision: use_flowguard
- Models updated: `simulations/startup_pm_review_model.py`, `simulations/meta_model.py`, `simulations/capability_model.py`.

### Modeled Risks
- Reviewer counts six live role records but accepts `agent_id` values restored from prior routes or older tasks.
- PM opens startup from a report that lacks current-task live-agent freshness and historical-ID nonreuse checks.
- Formal route or capability work proceeds after reused historical IDs are recorded as current live-agent evidence.

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- `python -m py_compile simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py`
- `python simulations\run_startup_pm_review_checks.py`
- `python simulations\run_meta_checks.py`
- `python simulations\run_capability_checks.py`
- `python scripts\check_install.py`
- `python scripts\smoke_autopilot.py`
- `git diff --check`

### Findings
- New formal startup now requires fresh current-task live background agents after startup answers and current route allocation.
- Historical `agent_id` values are audit history only. Same-task heartbeat/manual-resume may resume the current task-born cohort, but new tasks cannot reuse old IDs.
- Startup reviewer templates now require current-task freshness evidence, historical ID comparison, and blocker reporting for reused IDs.
- Startup PM-review now detects `reviewer_clean_accepts_reused_historical_agent_ids`.
- Meta and capability models renamed startup crew labels to fresh-spawn labels and gate work on current-task fresh live-agent evidence or explicit single-agent fallback.

### Results
- Py compile, startup PM-review, meta checks, capability checks, install check, smoke autopilot, template JSON load, installed-skill hash sync, and diff whitespace checks passed.


## flowpilot-run-directory-isolation-20260502 - Fresh run folder per formal invocation

- Project: FlowPilot development repository
- Trigger reason: User asked whether FlowPilot state should live in the target project or the local installed FlowPilot skill folder, then approved changing FlowPilot to start each use in an isolated per-run folder.
- Status: completed
- Skill decision: use_flowguard
- Models updated: `simulations/startup_pm_review_model.py`, `simulations/meta_model.py`, `simulations/capability_model.py`.

### Modeled Risks
- A new FlowPilot invocation resumes old top-level `.flowpilot/state.json` as current state.
- "Continue previous work" bypasses fresh startup by directly reusing an old run's control state.
- Reviewer opens a clean startup report without checking current run pointer/index consistency.
- PM opens startup before the prior-work import packet exists for a continuation run.

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- `python -m py_compile scripts\flowpilot_paths.py scripts\flowpilot_user_flow_diagram.py scripts\flowpilot_busy_lease.py scripts\flowpilot_run_with_busy_lease.py scripts\flowpilot_lifecycle.py scripts\flowpilot_global_supervisor.py scripts\flowpilot_watchdog.py simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
- `python simulations\run_startup_pm_review_checks.py`
- `python simulations\run_meta_checks.py`
- `python simulations\run_capability_checks.py`
- `python scripts\check_install.py`
- `python scripts\smoke_autopilot.py`
- `python scripts\flowpilot_user_flow_diagram.py --root . --json`
- `python scripts\flowpilot_busy_lease.py status --root . --json`
- `python scripts\flowpilot_lifecycle.py --root . --mode pause --json`
- `git diff --check`

### Findings
- FlowPilot's installed skill folder remains protocol/template storage only; per-project runtime state belongs in the target project's `.flowpilot/`.
- New formal invocations now create `.flowpilot/runs/<run-id>/`; top-level `current.json` and `index.json` are pointer/catalog files only.
- Continuing prior work creates a new run and imports old outputs as read-only evidence. Old control state, old live-agent IDs, old screenshots/icons/assets, and old route gates are not current evidence.
- Runtime helpers resolve active-run paths through `scripts/flowpilot_paths.py` while preserving read compatibility with legacy `.flowpilot/` projects.

### Results
- Startup PM-review, meta, capability, install, smoke, template JSON parse, legacy-layout path resolution, busy-lease status, lifecycle inventory, installed-skill sync, and diff whitespace checks passed.


## flowpilot-user-flow-diagram-runtime-audit-20260503 - Read-only audit of missing FlowPilot user flow diagram display

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User reported that when Cockpit UI is not available, the FlowPilot Mermaid/user-flow diagram is not visible in chat at node transitions.
- Status: completed
- Skill decision: use_flowguard_read_only_audit
- Started: 2026-05-03T06:41:33+00:00
- Ended: 2026-05-03T06:41:33+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/meta_model.py
- simulations/capability_model.py
- scripts/flowpilot_user_flow_diagram.py

### Commands
- OK (0.000s): `python -c import flowguard; print(flowguard.SCHEMA_VERSION)`
- OK (0.000s): `python scripts/flowpilot_user_flow_diagram.py --root . --json`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/smoke_autopilot.py`

### Findings
- Protocol requires a chat user-flow diagram at startup/key node changes, but execution assets do not wire a mandatory generator/display hook into heartbeat/manual-resume turns.
- The active run's persisted user-flow diagram artifact is stale relative to execution_frontier.json, and frontier render metadata still reports null/zero render fields.
- The diagram stage classifier misclassifies final verification as modeling when next_gate contains FlowGuard because it matches verify but not verification/final-verification.
- Installed FlowPilot skill does not package the diagram generator/templates, so agents using only the installed skill rely on prompt memory rather than a callable helper.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- No production code was changed during this investigation.

### Next Actions
- Add an executable user-flow display hook/check that refreshes the active-run diagram and requires the chat Mermaid block or explicit no-UI fallback evidence before node work proceeds.


## flowpilot-reviewer-personal-ui-walkthrough-20260503 - Reviewer direct UI inspection gate hardening

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User reported that UI/screenshot/interaction reviewers could approve by reading screenshot or interaction evidence instead of personally walking the UI and giving visual/layout critique.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T08:49:19+02:00
- Ended: 2026-05-03T08:49:19+02:00

### Modeled Risks
- Screenshot QA or worker interaction logs substitute for reviewer-owned UI inspection.
- Aesthetic verdicts pass without the reviewer personally inspecting the rendered surface.
- UI completion advances without checking click reachability, text overlap/clipping, whitespace, density, crowded controls, hierarchy, readability, and concrete design recommendations.

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- `python "%USERPROFILE%\.codex\skills\model-first-function-flow\assets\toolchain_preflight.py" --json`
- `python -m py_compile simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py`
- `python simulations\run_capability_checks.py`
- `python simulations\run_meta_checks.py`
- `python scripts\check_install.py`
- Synced `skills/flowpilot` to `%USERPROFILE%\.codex\skills\flowpilot`, then ran `python scripts\install_flowpilot.py --check --json`

### Findings
- Existing docs already said reviewer-owned gates require direct fact checks, but UI capability modeling only had broad booleans such as screenshot QA and aesthetic review.
- The capability model now requires concept personal visual review, rendered UI personal walkthrough, interaction reachability checks, layout/overlap/density checks, and reviewer design recommendations before UI aesthetic/divergence/final verification gates can close.
- Added `templates/flowpilot/human_review.template.json` so reviewer reports have explicit fields for `worker_report_only: false`, personal walkthrough, visual/layout findings, and PM-routable recommendations.

### Results
- Capability checks passed: 185422 states, 195906 edges, no invariant failures, no missing labels, no stuck states.
- Meta checks passed: 184421 states, 193501 edges, no invariant failures, no missing labels, no stuck states.
- Install/template checks passed, including the new human-review template.
- Installed FlowPilot skill now contains the personal-walkthrough reviewer rules.


## flowpilot-realtime-route-sign-hard-gate-20260503 - Make FlowPilot realtime route sign Mermaid a chat fallback hard gate with reviewer checks

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot workflow change: chat display fallback, route mutation/backtrack visibility, and reviewer gate enforcement
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-03T07:25:56+00:00
- Ended: 2026-05-03T07:25:56+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- none recorded

### Findings
- none recorded

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- none recorded


## flowpilot-realtime-route-sign-hard-gate-20260503 - Make FlowPilot realtime route sign Mermaid a chat fallback hard gate with reviewer checks

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot workflow change: chat display fallback, route mutation/backtrack visibility, and reviewer gate enforcement
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-03T07:42:30+00:00
- Ended: 2026-05-03T07:42:30+00:00
- Duration seconds: 0.000
- Commands OK: False

### Model Files
- simulations/user_flow_diagram_model.py

### Commands
- OK (0.000s): `python simulations/run_user_flow_diagram_checks.py`
- OK (0.000s): `python -m unittest tests.test_flowpilot_user_flow_diagram`
- OK (0.000s): `python scripts/check_install.py`
- FAIL (0.000s): `python simulations/run_meta_checks.py (blocked by existing external_watchdog field mismatch unrelated to route sign)`
- FAIL (0.000s): `python simulations/run_capability_checks.py (blocked by existing duplicate final_product_model_officer_adversarial_probe_done argument unrelated to route sign)`

### Findings
- Closed-Cockpit route sign must be pasted as chat Mermaid; file generation alone is insufficient.
- Review/validation failure and route mutation require a visible returns-for-repair edge and reviewer evidence.

### Counterexamples
- none recorded

### Friction Points
- Repository had concurrent dirty changes and unrelated meta/capability simulation inconsistencies, so broad checks could not complete.

### Skipped Steps
- none recorded

### Next Actions
- Reconcile existing meta/capability model drift separately, then rerun full simulations.


## flowpilot-officer-owned-async-modeling-20260503 - Make FlowPilot FlowGuard model gates officer-owned asynchronous gates with provenance requirements

- Project: FlowGuardProjectAutopilot
- Trigger reason: Behavior-bearing FlowPilot protocol change affecting model-gate ownership, route authority, parallel work boundaries, and validation flow
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T08:04:30+00:00
- Ended: 2026-05-03T08:04:30+00:00
- Duration seconds: 5400.000
- Commands OK: True

### Model Files
- .flowpilot/task-models/actor-authority-flow/model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python .flowpilot/task-models/actor-authority-flow/run_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python scripts/smoke_autopilot.py`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/install_flowpilot.py --check --json`

### Findings
- PM dispatches FlowGuard modeling requests to matching officers; matching officer must author, run, interpret, and approve/block with provenance.
- Main executor may continue only non-dependent prep while officer model gates are open; protected route, implementation, checkpoint, and completion gates remain blocked.
- Validation exposed and fixed two model consistency issues: duplicate capability reset argument and stale user-flow reviewer evidence after meta route mutations.

### Counterexamples
- none recorded

### Friction Points
- Installed skill check reports dependency presence but does not compare installed flowpilot contents against repository source.

### Skipped Steps
- none recorded

### Next Actions
- Consider adding an explicit install sync or drift check for installed flowpilot skill content.

## 2026-05-03 - Heartbeat-Only Continuation Retirement

### Trigger
- The user decided the external recovery loop and user-level supervisor made
  FlowPilot too complex and unstable, and requested removing them rather than
  turning them into optional features.

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`
- `simulations/startup_pm_review_model.py`
- `scripts/flowpilot_lifecycle.py`

### Commands
- OK: `python -m py_compile scripts\flowpilot_paths.py scripts\flowpilot_lifecycle.py scripts\flowpilot_user_flow_diagram.py simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py scripts\check_install.py scripts\smoke_autopilot.py`
- OK: `python simulations\run_startup_pm_review_checks.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python scripts\check_install.py`
- OK: `python scripts\smoke_autopilot.py`
- OK: `python scripts\flowpilot_lifecycle.py --root . --mode scan --write-record --json`

### Findings
- Active continuation now has two supported states only: stable one-minute
  heartbeat, or explicit manual resume.
- Runtime helpers, templates, skill text, public protocol, schema notes,
  verification docs, startup PM review checks, and Cockpit health display no
  longer create, require, or display the retired recovery layers.
- Local retired runtime records under `.flowpilot/` and the user-level Codex
  registry directory were removed after path-boundary checks.

### Counterexamples
- none recorded

### Friction Points
- Historical FlowGuard notes still mention retired designs, so active docs now
  include a superseding note to separate history from current behavior.

### Skipped Steps
- none recorded

### Next Actions
- Keep future continuation changes limited to heartbeat/manual-resume unless
  the user explicitly reopens the retired recovery design.

## 2026-05-03 - Universal Adversarial Role Approval

### Trigger
- The user identified that PM, reviewer, and officer approvals could still read
  as "approval after reading evidence" instead of independent adversarial
  verification. The requested standard applies to every review, not only UI.

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py`
- OK: `python simulations\run_startup_pm_review_checks.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`

### Findings
- Added a universal approval baseline to the skill, protocol, schema, and
  templates: reports are pointers only; approving roles must run direct
  probes, cite concrete files/screenshots/state fields/commands/results, test
  adversarial hypotheses, and record blindspots.
- Meta model now gates startup PM opening, material sufficiency, product
  architecture, child-skill manifests, FlowGuard model approvals,
  node/composite/final human review, final product replay, and final ledger
  approval behind independent validation states.
- Capability model mirrors the same rule for backend/UI capability paths,
  including child-skill current gates, implementation review, capability
  backward review, final product replay, final human review, and final ledger
  approval.

### Results
- Startup PM-review checks passed: 442 safe states, 441 edges, no invariant
  failures or missing labels; the missing independent PM audit hazard is
  detected.
- Meta checks passed: 208227 states, 217307 edges, no invariant failures, no
  missing labels, no stuck states.
- Capability checks passed: 202980 states, 213464 edges, no invariant failures,
  no missing labels, no stuck states.

### Next Actions
- Future role templates and Cockpit UI should surface
  `completion_report_only: false`, independent validation paths, concrete
  references, adversarial hypotheses, and residual blindspots as required
  fields before any approve action is enabled.

## 2026-05-03 - Root Acceptance, Node Experiments, And Zero Residual Risk Closure

### Trigger
- The user clarified that FlowPilot should not leave real residual risks in the
  final report. Early PM requirements should become root proof obligations,
  each current node should have its own concrete experiment plan, final review
  should replay standard and risk scenarios, and terminal completion should
  refresh state/evidence automatically.

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py`
- OK: JSON validation for the new and changed FlowPilot templates.
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python scripts\smoke_autopilot.py`

### Findings
- Added PM-owned `root_acceptance_contract.json` and
  `standard_scenario_pack.json` before contract freeze.
- Added per-node `node_acceptance_plan.json` so current-node risks map to
  concrete experiments and terminal replay scenarios before implementation
  starts.
- Replaced residual-risk parking with explicit risk-or-blindspot triage:
  fixed, routed to repair, current-gate blocker, terminal replay scenario,
  non-risk note, or explicit role-approved exception. Completion requires zero
  unresolved residual risks.
- Added `terminal_closure_suite.json` before terminal notice to refresh final
  state, frontier, ledger, lifecycle evidence, role memory, and report
  readiness.

### Results
- Meta checks passed: 208227 states, 217307 edges, no invariant failures, no
  missing labels, no stuck states.
- Capability checks passed: 216298 states, 226782 edges, no invariant failures,
  no missing labels, no stuck states.
- Smoke checks passed after using a long timeout because the suite reruns both
  long FlowGuard models.

### Counterexamples
- none recorded

### Friction Points
- The smoke suite can exceed a short 120-second timeout because it reruns
  release, startup, meta, and capability checks. Use a long timeout for full
  smoke validation.

### Next Actions
- Future Cockpit/approval UI should expose the root contract, node acceptance
  plan, standard scenario replay, residual risk triage, and terminal closure
  suite as hard completion gates.

## 2026-05-03 - Startup Wording Cleanup For Explicit Answers

### Trigger
- The user asked to clean remaining protocol/template inconsistencies after we
  found text that still implied banner-before-question startup or implicit
  `full-auto` fallback.

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py scripts\check_install.py`
- OK: JSON validation for `templates/flowpilot/mode.template.json`,
  `templates/flowpilot/state.template.json`, and
  `templates/flowpilot/execution_frontier.template.json`.
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`

### Findings
- Cleaned active protocol and template text so FlowPilot startup always asks
  the three startup questions, stops for a later explicit answer set, and only
  then emits the startup banner.
- Removed implicit mode fallback wording. `full-auto` is still an allowed mode,
  but it is recorded only as an explicit user answer.
- Updated mode/state templates to start with `mode: null` until the explicit
  startup answer is recorded.
- Renamed the model label from `default_mode_recorded` to
  `explicit_full_auto_mode_selected` so the executable evidence no longer
  suggests a default-mode path.

### Results
- Meta checks passed: 208227 states, 217307 edges, no invariant failures, no
  missing labels, no stuck states.
- Capability checks passed: 220522 states, 231006 edges, no invariant
  failures, no missing labels, no stuck states.

### Counterexamples
- none recorded

### Next Actions
- Keep examples and UI launch flows using the public invocation
  `Use FlowPilot. Ask the startup questions first.` Do not introduce a
  fallback mode or banner-before-answer shortcut in future docs or templates.


## flowpilot-pm-model-report-decision-packet-20260503 - Require FlowGuard officer model reports to provide PM decision packets with risk tiers, review agenda, toolchain recommendations, human walkthrough targets, and confidence boundaries

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that FlowGuard workers report to PM, and PM decides what to do from model-derived risks and suggestions
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T09:13:07+00:00
- Ended: 2026-05-03T09:13:07+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations\meta_model.py
- simulations\capability_model.py

### Commands
- OK (0.000s): `python -c import flowguard; print(flowguard.SCHEMA_VERSION)`
- OK (0.000s): `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py`
- OK (0.000s): `python simulations\run_meta_checks.py`
- OK (0.000s): `python simulations\run_capability_checks.py`
- OK (0.000s): `python scripts\check_install.py`
- OK (0.000s): `python scripts\smoke_autopilot.py`
- OK (0.000s): `python scripts\install_flowpilot.py --check --json`

### Findings
- Officer report templates now include PM-facing risk tiers, review agenda, toolchain/model suggestions, human walkthrough recommendations, PM decision options, and confidence boundary without absolute no-risk wording.
- Meta and capability models now reject FlowGuard officer model approval unless report extraction fields are present with adversarial model evidence.
- Repository source and installed local flowpilot skill were synchronized for the updated PM decision packet wording.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Future FlowGuard officer reports should be treated as PM decision support, not route decisions or no-risk certificates.


## flowpilot-terminal-human-backward-replay-20260503 - Require terminal human backward replay before PM completion approval

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User required final review to be a human-style backward acceptance pass over the delivered product and every effective node, with PM segment decisions and repair-driven reruns.
- Status: completed
- Skill decision: use_flowguard
- Mode: model_first_change

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations/meta_model.py simulations/capability_model.py simulations/run_meta_checks.py simulations/run_capability_checks.py scripts/check_install.py scripts/smoke_autopilot.py`
- OK: JSON validation for all `templates/flowpilot/**/*.json`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`
- OK: `python scripts/check_install.py`
- OK: `python scripts/smoke_autopilot.py`

### Findings
- Added `terminal_human_backward_replay_map.json` as a PM-owned terminal review map built from the clean final ledger.
- The reviewer must start from the delivered product, then manually replay root acceptance, parent/module nodes, and leaf nodes against current behavior and node acceptance plans.
- Every terminal replay segment now requires a PM continue/repair/route-mutation/stop decision.
- A terminal replay repair invalidates affected evidence, rebuilds the final ledger and replay map, and reruns final review; the default restart is from the delivered product unless PM justifies an impacted-ancestor restart.
- FlowGuard meta checks initially exposed that the new repair branch was unreachable under the generic route-revision budget. The model was narrowed so terminal replay has its own single repair count without expanding the global route-revision state space.

### Results
- Meta checks passed: 281507 states, 292187 edges, no invariant failures, no missing labels, no stuck states.
- Capability checks passed: 235810 states, 246294 edges, no invariant failures, no missing labels, no stuck states.

### Counterexamples
- Initial unreachable labels: `terminal_human_backward_replay_found_repair_issue`, `terminal_human_backward_pm_repair_decision_interrogated`, and `route_updated_after_terminal_human_backward_replay_failure`.
- Resolution: make terminal backward replay repair a terminal-specific repair path that invalidates final evidence and returns to route checks without increasing the global route-revision budget.

### Skipped Steps
- No conformance replay adapter was added; this change updates protocol templates and executable process models, not a runtime state writer.

### Next Actions
- Keep final completion wording tied to terminal human backward replay, PM segment decisions, repair/restart policy, and zero unresolved residual risks.


## flowpilot-local-skill-inventory-pm-selection-20260503 - Inventory local skills before PM child-skill selection

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that FlowPilot should collect locally available skills and host capabilities during material intake, while PM should decide which skills to use only after product-function architecture and capability mapping.
- Status: completed
- Skill decision: use_flowguard
- Mode: model_first_change

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations/meta_model.py simulations/run_meta_checks.py simulations/capability_model.py simulations/run_capability_checks.py`
- OK: JSON/template validation through `python scripts/check_install.py`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`
- OK: `python scripts/smoke_autopilot.py`
- OK: `git diff --check` with Windows line-ending warnings only

### Findings
- Added a candidate-only local skill and host capability inventory to material intake.
- Added PM-owned child-skill selection before child-skill route discovery.
- PM selection records classify skills as required, conditional, deferred, or rejected, including negative-scope decisions and hard gates.
- Child-skill route discovery now starts from PM-selected skills instead of raw host availability.
- Initial meta-model validation exposed an over-broad checkpoint invariant around current-node skill-improvement observation gates. The invariant now checks the pre-checkpoint pending path, not the post-checkpoint next-node reset state.

### Results
- Meta checks passed: 292707 states, 305707 edges, no invariant failures, no missing labels, no stuck states, and no nonterminating components.
- Capability checks passed: 245702 states, 258706 edges, no invariant failures, no missing labels, no stuck states, and no nonterminating components.
- Installation and autopilot smoke checks passed.

### Counterexamples
- Initial meta check failed when `checkpoint_written` remained true after execution-scope gates reset for the next node.
- Resolution: scope the invariant to `chunk_state == "checkpoint_pending"` so the model still rejects checkpoint writes before PM observation review while allowing the next-node reset.

### Skipped Steps
- No runtime skill scanner implementation was added in this change. The protocol, templates, and executable process models now define the inventory and PM selection records that a runtime scanner or manual material intake can populate.

### Next Actions
- Keep local skill availability candidate-only. A child skill may be used only when PM selection and the existing child-skill fidelity gates approve it for the route.


## flowpilot-skill-improvement-report-20260503 - Nonblocking PM-owned skill improvement reports

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested that PM collect issues in FlowPilot itself during each run, without blocking the current project or requiring immediate root-repo repairs, then write a final report for later manual skill maintenance.
- Status: completed
- Skill decision: use_flowguard
- Mode: model_first_change

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py scripts\check_install.py`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python scripts\smoke_autopilot.py`
- OK: `git diff --check` with Windows line-ending warnings only

### Findings
- Added run-local `flowpilot_skill_improvement_observations.jsonl` and PM-owned `flowpilot_skill_improvement_report.json` templates.
- Added protocol text requiring PM to ask for FlowPilot-skill issues at node/review boundaries and write the final report before terminal completion.
- The observations are explicitly nonblocking: they do not alter the current project acceptance ledger, do not become residual project risk, and do not require fixing the root skill repository before the active run completes.
- FlowGuard modeling initially exposed two integration risks: observation/no-issue branches doubled the state graph when modeled as lasting state, and old checkpoint evidence could leak into the next-node reset. The final model keeps the action labels but merges observation/no-issue into the same control state, and clears old checkpoint evidence when a new node acceptance plan begins.

### Results
- Meta checks passed: 292707 states, 305707 edges, no invariant failures, no missing labels, no stuck states, and no nonterminating components.
- Capability checks passed: 245702 states, 258706 edges, no invariant failures, no missing labels, no stuck states, and no nonterminating components.
- Install and smoke checks passed.

### Counterexamples
- First meta run exceeded the 300000-state graph limit when observation/no-issue branches were modeled as different lasting states.
- Second meta run failed because `checkpoint_written` persisted into the next-node entry path after the current-node observation flag reset.
- Resolution: make both observation branches converge to the same control state and treat node-acceptance start as the point where old checkpoint evidence is no longer current.

### Skipped Steps
- No automatic ingestion of past skill-improvement reports was added. The user explicitly prefers manual review of these reports for now.

### Next Actions
- Keep skill-improvement reports independent from project acceptance. Future automation may read them only if explicitly designed and modeled as a separate maintenance workflow.


## flowpilot-parent-backward-replay-20260503 - Structural parent-node backward reviews

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested that FlowPilot avoid fuzzy high-risk/integration heuristics and require an independent backward human review for every major route node, defined structurally as any effective route node with children.
- Status: completed
- Skill decision: use_flowguard
- Mode: model_first_change

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations/meta_model.py simulations/capability_model.py simulations/run_meta_checks.py simulations/run_capability_checks.py scripts/check_install.py scripts/smoke_autopilot.py`
- OK: JSON/template validation for `templates/flowpilot/**/*.json`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`
- OK: `python scripts/check_install.py`
- OK: `python scripts/smoke_autopilot.py`

### Findings
- Added a structural parent/composite-node trigger: every effective route node with children must be listed in parent backward targets and reviewed before that parent can close.
- The parent replay starts from the parent-level delivered result and rechecks the parent goal, child rollup, child evidence, child node acceptance plans, and live artifacts or product behavior.
- Child-local review passes are only pointers. They cannot substitute for the parent replay or the terminal route-wide replay.
- PM must record a segment decision after each parent replay: continue, repair an existing child, add a sibling child, rebuild the child subtree, bubble the issue to the parent, or stop.
- Route mutation makes affected parent evidence stale and requires the same parent replay again before closure.

### Results
- Meta checks passed: 292707 states, 305707 edges, no invariant failures, no missing labels, no stuck states, and no nonterminating components.
- Capability checks passed: 245702 states, 258706 edges, no invariant failures, no missing labels, no stuck states, and no nonterminating components.
- Install, JSON, compile, and autopilot smoke checks passed.

### Counterexamples
- Initial modeling exposed an over-modeled target enumeration path that pushed the meta graph past the 300000-state limit.
- A later meta run exposed a real ordering issue where checkpoint flow could be reached before the current-node skill-improvement observation gate.
- Resolution: keep parent target enumeration as a structural route-level obligation instead of per-target lasting graph state, and move the skill-improvement observation check before checkpoint eligibility.

### Skipped Steps
- No runtime route execution was started or resumed from the repository `.flowpilot` state. This change updates the skill protocol, templates, and executable process models.

### Next Actions
- Keep the parent-review trigger structural. Semantic labels such as high-risk, integration, feature, or downstream dependency can inform the review context but must not decide whether the replay is required.


## flowpilot-desktop-cockpit-state-lifecycle-20260503 - Model FlowPilot desktop cockpit state lifecycle before native implementation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Stateful desktop cockpit behavior: real route mapping, task tabs, i18n, settings support/sponsor, tray lifecycle, fresh asset lineage, and restrained motion
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T16:27:18+00:00
- Ended: 2026-05-03T16:27:18+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- .flowpilot/runs/run-20260503-174644-desktop-cockpit/task-models/desktop-cockpit-state-lifecycle/model.py

### Commands
- OK (0.000s): `flowguard import check: schema 1.0`
- OK (0.000s): `python .flowpilot\runs\run-20260503-174644-desktop-cockpit\task-models\desktop-cockpit-state-lifecycle\run_checks.py`

### Findings
- FlowGuard exploration passed after reducing the event set to representative state transitions; explicit hazard states detect cross-run route mix, stale frontier success, partial i18n, unsafe support/sponsor, close-exits-app, old assets, decorative motion, card pile layout, and skipped implementation gate.

### Counterexamples
- none recorded

### Friction Points
- Initial broad event exploration timed out, so the model was narrowed to representative events plus explicit hazard-state checks.

### Skipped Steps
- Runtime conformance replay skipped because production desktop code does not exist yet; required after implementation.
- Real Windows tray interaction skipped until the native desktop app launches.

### Next Actions
- Proceed to concept-led design language and fresh imagegen candidate search, then conformance and interaction checks after implementation.


## flowpilot-desktop-cockpit-realtime-route-amendment-20260503 - Add realtime no-manual-refresh route-map requirement to FlowPilot desktop cockpit model

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified the cockpit route map must update live from FlowPilot source files without a manual refresh click
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T16:39:58+00:00
- Ended: 2026-05-03T16:39:58+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- .flowpilot/runs/run-20260503-174644-desktop-cockpit/task-models/desktop-cockpit-state-lifecycle/model.py

### Commands
- OK (0.000s): `python .flowpilot\runs\run-20260503-174644-desktop-cockpit\task-models\desktop-cockpit-state-lifecycle\run_checks.py`

### Findings
- Model now includes realtime_watch_enabled, source_change_seen, auto_refresh_applied, and manual_refresh_required; implementation is blocked if route correctness depends on manual refresh.

### Counterexamples
- Initial realtime model found stale success after a later frontier conflict; resolving route state now clears the prior visible success panel before rerender or degradation.

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Implement a native file watcher or bounded automatic polling loop and prove source-change update without pressing refresh.


## flowpilot-desktop-cockpit-model-role-remediation-20260503 - Remediate product officer model block for realtime and tray lifecycle gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Product officer blocked the cockpit state model because implementation_allowed omitted tray lifecycle and realtime degraded-source path
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T16:45:31+00:00
- Ended: 2026-05-03T16:45:31+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- .flowpilot/runs/run-20260503-174644-desktop-cockpit/task-models/desktop-cockpit-state-lifecycle/model.py

### Commands
- OK (0.000s): `python .flowpilot\runs\run-20260503-174644-desktop-cockpit\task-models\desktop-cockpit-state-lifecycle\run_checks.py`

### Findings
- Added tray_lifecycle_verified gate before implementation_allowed and added route_auto_refreshed_degraded for changed-source conflicts/missing files.

### Counterexamples
- Product officer found implementation_allowed reachable without tray lifecycle evidence; the model now blocks that state.

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Request product and process officer re-review on amended passing results.


## flowpilot-major-node-route-sign-display-20260503 - Require FlowPilot Route Sign display at major route-node entry

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed that the FlowPilot route sign appeared on the first node but not on later major node entries in another thread.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T17:57:00+00:00
- Ended: 2026-05-03T17:57:00+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/user_flow_diagram_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile scripts\flowpilot_user_flow_diagram.py simulations\user_flow_diagram_model.py simulations\run_user_flow_diagram_checks.py scripts\check_install.py`
- OK: `python simulations\run_user_flow_diagram_checks.py`: 72 states, 71 edges, no invariant failures, all display-trigger labels present
- OK: `python scripts\flowpilot_user_flow_diagram.py --root . --trigger major_node_entry --markdown --json`: accepted the new trigger and generated active-node Mermaid
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`: 292707 states, 305707 edges, no invariant failures, missing labels, stuck states, or nonterminating components
- OK: `python simulations\run_capability_checks.py`: 245702 states, 258706 edges, no invariant failures, missing labels, stuck states, or nonterminating components

### Findings
- The bug was a protocol and trigger vocabulary gap: startup and `key_node_change` were modeled, but ordinary later major `flow.json` node entry was not a first-class route-sign trigger.
- The display packet could also be marked `chat_displayed_in_chat` from a script argument, which is weaker than proving the Mermaid block actually appeared in the assistant message.
- FlowPilot now treats `major_node_entry`, `parent_node_entry`, `leaf_node_entry`, and `pm_work_brief` as explicit display triggers, while ordinary heartbeat ticks and internal subnodes do not trigger reposts.

### Counterexamples
- `major_node_entry_not_classified`: a major node entry in closed-Cockpit mode did not require chat Mermaid before node work.

### Friction Points
- The current workspace had concurrent untracked desktop cockpit files and pre-existing result-file changes. Verification was run without editing those scopes; the pre-existing `capability_results.json` diff was restored after the broad check regenerated it.

### Skipped Steps
- No live external thread transcript was available, so the fix targets the reusable skill protocol, trigger set, templates, and model rather than rewriting that thread's history.

### Next Actions
- In the next real FlowPilot run, use `--trigger major_node_entry` before entering each major route node when Cockpit is closed, paste the generated Markdown in chat, and only then mark chat display evidence.


## flowpilot-autonomous-ui-route-20260503 - Route UI work through autonomous concept UI redesign

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested that FlowPilot replace its default UI child-skill route with the new experimental autonomous UI orchestration skill while keeping the old concept-led skill available.
- Status: completed with one unrelated concurrent self-check caveat
- Skill decision: use_flowguard
- Started: 2026-05-03T19:05:00+00:00
- Ended: 2026-05-03T19:05:00+00:00
- Duration seconds: 0.000
- Commands OK: mostly true

### Model Files
- simulations/capability_model.py
- simulations/run_capability_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py scripts\install_flowpilot.py`
- OK: `python -m json.tool flowpilot.dependencies.json`
- OK: `python -m json.tool templates\flowpilot\capabilities.template.json`
- OK: `python simulations\run_capability_checks.py`: 247882 states, 260886 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python simulations\run_meta_checks.py`: 292707 states, 305707 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python scripts\install_flowpilot.py --check --json`: FlowPilot, autonomous UI skill, frontend-design, design-iterator, design-implementation-reviewer, concept-led-ui-redesign, FlowGuard, and imagegen provider detected
- OK: local skill validation for installed `flowpilot`, `autonomous-concept-ui-redesign`, `design-iterator`, and `design-implementation-reviewer`
- OK: repository/installed hash comparison for FlowPilot and autonomous UI skill files
- OK with warnings: `git diff --check` reported only CRLF normalization warnings
- Caveat: `python scripts\check_install.py` failed on concurrently added defect-governance required files/results that were outside this UI-route change.

### Findings
- FlowPilot now routes UI redesign, implementation, polish, visual iteration, deviation review, and geometry/screenshot QA through `autonomous-concept-ui-redesign` by default.
- The old `concept-led-ui-redesign` remains installed and declared as an internal dependency/fallback for the autonomous route rather than being deleted.
- The capability model now requires the PM to select the autonomous UI pipeline before UI work and requires geometry QA before final UI visual closure.

### Counterexamples
- Initial capability check found states where ordinary route-repair resets cleared the new autonomous-pipeline selection while leaving UI concept evidence alive. The model was revised so the pipeline selection is route-strategy state and is not cleared by generic execution-quality resets.

### Friction Points
- Another active thread modified the repository during this task, including defect-governance check requirements and desktop-cockpit files. This task did not revert those changes.

### Skipped Steps
- `check_public_release.py --skip-url-check` timed out when it included full validation because the validation suite is long-running in the dirty concurrent workspace; the manifest-only release preflight was run with `--skip-validation` and passed with only the dirty-worktree warning.

### Next Actions
- Restart Codex or start a fresh thread so the newly installed skills appear in the available skill list, then invoke FlowPilot on a UI task and verify the PM selects `autonomous-concept-ui-redesign` for the UI child-skill route.

## FlowPilot Defect Governance And Clean Restart Guard

- Task ID: `flowpilot-defect-governance-clean-restart-20260503`
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T21:00:00+02:00
- Ended: 2026-05-03T22:00:08+02:00
- Commands OK: true

### Model Files
- `simulations/defect_governance_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile scripts\flowpilot_defects.py simulations\defect_governance_model.py simulations\run_defect_governance_checks.py simulations\meta_model.py simulations\capability_model.py scripts\install_flowpilot.py scripts\check_install.py`
- OK: `python -m unittest tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_defects`
- OK: `python simulations\run_defect_governance_checks.py`: 23 states, 22 edges, no invariant failures
- OK: `python simulations\run_meta_checks.py`: 502502 states, 522670 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python simulations\run_capability_checks.py`: 500493 states, 525949 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python simulations\run_user_flow_diagram_checks.py`
- OK: `python simulations\run_startup_pm_review_checks.py`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --install-missing --force --json`
- OK: `python scripts\install_flowpilot.py --check --json`: installed FlowPilot source digest matched repository source digest
- OK with warnings: `git diff --check` reported only CRLF normalization warnings

### Findings
- FlowPilot now initializes a run-level defect ledger, evidence ledger, and live skill improvement report before route work starts.
- Reviewer or worker blockers must be logged as defect events by the discovering role before PM triage; PM owns triage and closure, but closure requires repair plus same-class recheck first.
- Terminal closure now fails while blocker defects are open or fixed but still pending recheck.
- Evidence that is fixture-only, stale, invalid, or superseded must remain classified instead of being overwritten by later good evidence.
- Controlled pause now writes a pause snapshot so a later restart can separate reusable context from obsolete UI work.
- Repository-owned installed FlowPilot skills are now checked for source freshness, not just presence.
- The previous desktop cockpit experiment run, generated cockpit folder, runtime package cache, test data file, and stale `.flowpilot/current.json`/`index.json` pointers were removed to support a clean next run.

### Counterexamples
- The new defect governance model explicitly detects: blocker triage before defect logging, PM closure without same-class recheck, terminal completion with fixed-pending-recheck defects, invalid evidence being treated as erased, and pause/restart without a snapshot.
- The expanded meta model initially exposed a duplicate state-field assignment during route repair modeling; the route-repair transition was corrected and the graph runners were adjusted to reuse the already-built graph.

### Friction Points
- The repository was already dirty from concurrent skill work, including autonomous UI skill files and prior FlowPilot model changes. This task preserved those changes and avoided deleting or reverting them.
- Expanded state space made meta and capability checks large, so graph state limits were raised and duplicate graph construction was removed from the runners.

### Skipped Steps
- No new desktop UI was built in this task; the user's instruction was to prepare the FlowPilot process for a future clean UI restart and remove old UI traces.

### Next Actions
- Start the next FlowPilot desktop UI task from a fresh run; verify the run creates defect/evidence ledgers and a live improvement report before design or implementation begins.
