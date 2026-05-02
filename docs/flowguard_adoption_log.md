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
