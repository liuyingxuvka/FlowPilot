# FlowGuard Adoption Log

This human-readable log summarizes FlowGuard adoption records for major protocol changes.
Machine-readable entries live in `.flowguard/adoption_log.jsonl`.

## 2026-05-06 - FlowPilot v0.3.1 PM File-Backed Payload Patch

- Trigger: after the `v0.3.0` source release was published, a relevant router
  runtime change appeared locally to let PM-owned route artifacts use
  file-backed role payload envelopes.
- Decision: `use_flowguard`.
- Mode: `process_preflight` for behavior-bearing router and release side
  effects.
- Scope updated:
  - extended file-backed role payload loading to PM material understanding,
    product-function architecture, and root acceptance contract events;
  - added optional file-backed loading for PM/reviewer/officer artifacts that
    already support direct payloads;
  - preserved role-output envelope metadata in written PM artifacts;
  - added router runtime coverage for PM material understanding through a
    `memo_path`/`memo_hash` envelope;
  - bumped release metadata to `0.3.1`.
- Validation:
  - `python -m py_compile skills\flowpilot\assets\flowpilot_router.py`;
  - `python -m pytest tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_material_understanding_accepts_file_backed_memo_payload tests\test_flowpilot_router_runtime.py tests\test_flowpilot_control_gates.py -q`.
- Results:
  - targeted PM file-backed payload coverage passed;
  - full router runtime and control gate suite passed with 68 tests.

## 2026-05-06 - FlowPilot v0.3.0 GitHub Skill Source Release Preflight

- Trigger: the user asked to publish the local FlowPilot skill to GitHub main
  and then clarified that `flowpilot.dependencies.json` must use the GitHub
  skill source instead of copying FlowPilot from this repository.
- Decision: `use_flowguard`.
- Mode: `process_preflight` for release, dependency-source, and GitHub
  publishing side effects.
- Scope updated:
  - changed the `flowpilot` dependency entry to an explicit GitHub skill source
    at `liuyingxuvka/FlowPilot`, `main`, `skills/flowpilot`;
  - retained local checkout refresh behavior through `install.local_sync_mode:
    copy_from_repo` and `repo_path`;
  - updated install tooling so source freshness and `--sync-repo-owned` still
    work for GitHub-sourced, repo-owned skills;
  - updated dependency-source documentation and README dependency tables;
  - bumped release metadata to `0.3.0` and added the changelog entry.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema
    `1.0`;
  - `python -m json.tool flowpilot.dependencies.json`;
  - `python -m py_compile scripts\install_flowpilot.py scripts\audit_local_install_sync.py scripts\check_public_release.py scripts\check_install.py`;
  - `python scripts\install_flowpilot.py --sync-repo-owned --json`;
  - `python scripts\install_flowpilot.py --check --json`;
  - `python scripts\audit_local_install_sync.py --json`;
  - `python scripts\check_public_release.py --json --skip-url-check --skip-validation`;
  - `python scripts\check_public_release.py --json --skip-validation`;
  - `python scripts\check_install.py`;
  - `python simulations\run_release_tooling_checks.py`;
  - `python scripts\smoke_autopilot.py`;
  - `git diff --check`.
- Results:
  - real FlowGuard was importable;
  - installed `flowpilot` source refreshed from the checkout and matched the
    repository source digest;
  - dependency URLs, including the public FlowPilot skill source URL, resolved;
  - public-boundary diagnostics passed after replacing local absolute paths in
    tracked release-facing files;
  - `git diff --check` reported only line-ending normalization warnings.

## 2026-05-04 - Retired Recovery Residue Cleanup

- Trigger: the user observed that FlowPilot runs could still refer to old
  long-cadence recovery evidence, suggesting active prompts or required reading
  still contained historical design residue.
- Decision: `use_flowguard`.
- Scope updated:
  - deleted the retired recovery scripts, prompt, template, helper, and obsolete
    findings page from the active source tree;
  - replaced the preflight findings page with the current effective
    heartbeat-only continuation, packet-control, PM/reviewer, and startup
    display fallback boundaries;
  - kept the retired recovery state filename ignored so old local residue or
    backups cannot be accidentally committed;
  - added install and local-sync checks that fail if retired recovery source
    paths reappear;
  - synchronized the installed `flowpilot` Codex skill and verified source
    freshness.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema
    `1.0`;
  - `python -m py_compile scripts\audit_local_install_sync.py scripts\check_install.py scripts\install_flowpilot.py`;
  - `python scripts\check_install.py`;
  - `python simulations\run_meta_checks.py`;
  - `python simulations\run_capability_checks.py`;
  - `python simulations\run_startup_pm_review_checks.py`;
  - `python scripts\install_flowpilot.py --sync-repo-owned --json`;
  - `python scripts\audit_local_install_sync.py --json`;
  - `python scripts\install_flowpilot.py --check --json`;
  - `python scripts\smoke_autopilot.py`.
- Results:
  - install self-check and local sync audit passed;
  - installed `flowpilot` source digest matched the repository source digest;
  - meta, capability, and startup PM-review models passed with zero invariant
    failures;
  - smoke autopilot passed;
  - remaining exact retired source path strings are confined to absence
    guardrails.

## 2026-05-04 - FlowPilot v0.2.1 Release Metadata And Tag Preflight

- Trigger: after the post-`v0.2.0` controller, PM/reviewer, heartbeat, and
  Cockpit cleanup changes were pushed to `main`, the user asked whether the
  GitHub tag, version metadata, and README should be updated too.
- Decision: `use_flowguard`.
- Mode: `process_preflight` for release/tag side effects.
- Scope updated:
  - bumped `VERSION` to `0.2.1`;
  - split post-`v0.2.0` work into a new `CHANGELOG.md` `0.2.1` section;
  - updated README current-release links and corrected the Chinese Cockpit
    description to match the current source tree;
  - kept the rollback backup in the repository while replacing local absolute
    paths in the backup README, manifest, and zip with portable path examples.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema
    `1.0`;
  - `python simulations/run_release_tooling_checks.py`;
  - `python scripts/check_install.py`;
  - `python scripts/audit_local_install_sync.py --json`;
  - `python scripts/smoke_autopilot.py`;
  - `python scripts/check_public_release.py --skip-validation --json`;
  - `python scripts/check_public_release.py --skip-url-check --skip-validation --json`;
  - `git diff --check`.
- Results:
  - release-tooling model passed with 16 states, 15 edges, zero invariant
    failures, and all required labels present;
  - install, local-sync audit, smoke, dependency URL, public-boundary, and
    whitespace checks passed;
  - public release preflight initially blocked on a backup README containing a
    machine-specific path; the backup text and archive were sanitized and the
    privacy scan then passed;
  - GitHub repository ruleset `Protect default branch` was active for the
    branch target.

## 2026-05-04 - Heartbeat Resume Re-Enters Packet Control Plane

- Trigger: after the controller/PM/reviewer packet redesign, the user asked
  whether heartbeat prompts also needed to change so a stopped or sleeping run
  wakes as Controller only instead of continuing worker work directly.
- Decision: `use_flowguard`.
- Scope updated:
  - heartbeat/manual-resume templates now carry a Controller-only wakeup
    sequence, stable-launcher boundary, packet recovery state, and ambiguity
    block policy;
  - added `packet_ledger.template.json` and linked packet status into
    `state.template.json`, `execution_frontier.template.json`, and
    `continuation_evidence.template.json`;
  - protocol docs now require heartbeat/manual resume to load current-run
    state plus packet ledger, restore roles, ask PM for `PM_DECISION` with
    `controller_reminder`, require reviewer dispatch before workers, and send
    existing worker results to reviewer;
  - packet-control, meta, and capability FlowGuard models now include
    heartbeat packet-ledger load, PM reminder check, reviewer dispatch policy,
    ambiguous-worker-state block, and missing-state block coverage.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema
    `1.0`
  - `python -m py_compile simulations/meta_model.py simulations/run_meta_checks.py simulations/capability_model.py simulations/run_capability_checks.py skills/flowpilot/assets/packet_control_plane_model.py skills/flowpilot/assets/run_packet_control_plane_checks.py scripts/check_install.py`
  - `python skills/flowpilot/assets/run_packet_control_plane_checks.py`
  - `python scripts/check_install.py`
  - `python simulations/run_startup_pm_review_checks.py`
  - `python simulations/run_meta_checks.py`
  - `python simulations/run_capability_checks.py`
- Results:
  - packet control plane: 9 traces, zero invariant violations, zero dead
    branches, zero missing labels;
  - startup PM-review: passed;
  - meta model: 559,207 states, 579,379 edges, zero invariant failures, zero
    missing labels, zero stuck states;
  - capability model: 529,853 states, 555,313 edges, zero invariant failures,
    zero missing labels, zero stuck states.

## 2026-05-04 - Autonomous UI Skill Standalone Concept-Led Merge

- Trigger: the user decided the old `concept-led-ui-redesign` skill should be
  removable and asked to migrate its concept-led front half into
  `autonomous-concept-ui-redesign` without losing the existing autonomous UI
  upgrades.
- Decision: `use_flowguard`.
- Scope updated:
  - `skills/autonomous-concept-ui-redesign/SKILL.md` no longer loads the old
    skill for `concept_redesign`; functional framing, display element review,
    information architecture, concept brief, candidate search, selected concept
    review, divergence review, visual QA, platform notes, and app-icon checks
    are now built into this skill.
  - `skills/autonomous-concept-ui-redesign/references/` gained the migrated
    concept-led reference files.
  - `skills/autonomous-concept-ui-redesign/scripts/app_icon_asset_check.py` was
    migrated so app/software icon validation no longer depends on the old skill.
  - `flowpilot.dependencies.json`, FlowPilot current docs, and README dependency
    tables no longer declare `concept-led-ui-redesign` as a required or optional
    FlowPilot dependency.
- Preserved user-requested upgrades:
  - default explicit accent color;
  - app/software icon realization as a real platform identity gate;
  - native desktop screenshot trust and real-platform recapture requirements.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema
    `1.0`
  - `python -m json.tool flowpilot.dependencies.json`
  - `python -m py_compile skills/autonomous-concept-ui-redesign/scripts/app_icon_asset_check.py scripts/check_install.py scripts/install_flowpilot.py simulations/meta_model.py simulations/capability_model.py simulations/startup_pm_review_model.py`
  - `python scripts/install_flowpilot.py --sync-repo-owned --json`
  - `python scripts/install_flowpilot.py --check --json`
  - `python scripts/check_install.py`
  - `python simulations/run_startup_pm_review_checks.py`
  - `python simulations/run_meta_checks.py`
  - `python simulations/run_capability_checks.py`
- Current install note: local installed `flowpilot` and
  `autonomous-concept-ui-redesign` digests match the repository source after
  sync. The dependency manifest no longer asks for the old
  `concept-led-ui-redesign` skill.

## 2026-05-04 - Skill Rule Tightening After Desktop Cockpit Review

- Trigger: the user reviewed the FlowPilot desktop cockpit run and asked to
  update reusable skill behavior while keeping external predictive KB out of
  FlowPilot's public hard requirements.
- Decision: `use_flowguard`.
- Scope updated:
  - `skills/autonomous-concept-ui-redesign/` now treats native desktop
    offscreen/headless screenshots as provisional until renderer trust is
    checked, and requires real platform recapture or `partial`/`blocked` when
    text/readability is suspect.
  - `skills/flowpilot/`, `templates/flowpilot/`, `simulations/meta_model.py`,
    and `simulations/capability_model.py` now use one generated-resource
    terminal disposition vocabulary:
    `consumed_by_implementation`, `included_in_final_output`, `qa_evidence`,
    `flowguard_evidence`, `user_flow_diagram`, `superseded`, `quarantined`,
    and `discarded_with_reason`.
  - The user's predictive KB support-entry cards were consolidated so the
    canonical PayPal.Me support preference includes warm support copy and clear
    no-purchase/no-rights boundaries.
- Main findings:
  - External KB postflight is a local/user workflow concern, not a FlowPilot
    public dependency; no FlowPilot hard gate was added for external KB.
  - Generated-resource rules already existed, but mixed labels such as
    `selected`, `used`, `deleted`, `final-output`, and generic `evidence`
    weakened execution clarity.
  - Native desktop screenshot QA belongs in the autonomous UI skill, not the
    older concept-led skill path.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python -m py_compile simulations/meta_model.py simulations/capability_model.py simulations/run_meta_checks.py simulations/run_capability_checks.py`
  - JSON parse checks for generated-resource and terminal closure templates
  - YAML parse checks for the two support-entry KB cards
  - old generated-resource vocabulary scan returned no hits
  - `python simulations/run_meta_checks.py`
  - `python simulations/run_capability_checks.py`
  - `python scripts/check_install.py`
  - `python -m unittest tests.test_flowpilot_defects tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_control_gates tests.test_flowpilot_meta_route_sign`
  - installed `flowpilot` and `autonomous-concept-ui-redesign` skill copies
    hash-match the repository sources
- Caveats:
  - `python scripts/install_flowpilot.py --check --json` still reports overall
    `ok: false` because the optional old `concept-led-ui-redesign` companion
    skill is not installed. The two repo-owned skills changed in this task are
    fresh.
  - `python scripts/smoke_autopilot.py` timed out after 124 seconds and was
    stopped; direct meta, capability, install, JSON/YAML, and unit checks were
    run instead.

## 2026-05-04 - FlowPilot Four-Question Startup Display Surface

- Trigger: after the native FlowPilot Cockpit UI existed, the user clarified
  that formal startup must ask whether to open Cockpit UI or keep using chat
  route signs.
- Decision: `use_flowguard`.
- Models updated: `simulations/startup_pm_review_model.py`,
  `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Startup now has four explicit answers: run mode, background-agent
    permission, scheduled continuation, and display surface.
  - The assistant must still stop immediately after asking the startup
    questions; no banner, route write, subagent launch, heartbeat probe, UI
    launch, imagegen, or implementation may happen in that same response.
  - If the user chooses Cockpit, the startup display entry action is opening
    Cockpit UI when startup state is ready; if the user chooses chat, the
    startup route sign must be displayed in chat.
  - The startup PM model now detects Cockpit requested but not opened, chat
    requested but no route sign displayed, and chat used despite a Cockpit
    answer.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)`: schema
    `1.0`
  - `python simulations/run_startup_pm_review_checks.py`
  - `python simulations/run_meta_checks.py`
  - `python simulations/run_capability_checks.py`
  - `python -m unittest tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_cockpit_state_reader tests.test_flowpilot_cockpit_i18n`
  - `python scripts/check_install.py`
- Current install note: repository self-check passes, but
  `skills/flowpilot` has been synced to
  `%USERPROFILE%\.codex\skills\flowpilot`; the installed FlowPilot digest now
  matches repository source. The installer was also tightened so missing
  optional companion skills are warning-only by default and are installed only
  with explicit `--include-optional`.

## 2026-05-04 - Default Accent Color For UI Design Skills

- Trigger: the user observed that the FlowPilot cockpit UI lacked a clear
  emphasis color, causing dense UI regions to visually run together.
- Decision: `use_flowguard` for a lightweight skill-behavior change; no new
  targeted model was created because this was a bounded documentation and
  local-skill policy update rather than a route-control state change.
- Scope updated:
  - `skills/autonomous-concept-ui-redesign/SKILL.md`
  - installed `concept-led-ui-redesign` skill instructions and references
  - installed `frontend-design` skill instructions
- Main findings:
  - The concept-led palette contract previously allowed either no accent or
    one explicit accent color, so accent was genuinely optional by default.
  - UI design routes now default to one explicit accent color unless the user
    explicitly asks for no accent, an existing design system is neutral-only,
    or a named product reason makes neutral-only safer.
  - The accent must have a named job such as focus, selected state, primary
    action, active route, key metric, or another hierarchy cue.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `rg` check for old optional-accent wording and new default-accent wording
  - `python scripts/check_install.py`
  - `python scripts/install_flowpilot.py --check --json`

## 2026-05-04 - App Icon Realization Gate For Autonomous UI Routes

- Trigger: the user observed that the generated UI/icon direction did not
  prove the icon became the actual software, taskbar, tray, or package icon,
  and clarified that the active FlowPilot UI route used
  `autonomous-concept-ui-redesign`, not only `concept-led-ui-redesign`.
- Decision: `use_flowguard` for a lightweight skill/protocol gate update; no
  new targeted model was created because the change is an explicit child-skill
  evidence requirement rather than a new route-control state machine.
- Scope updated:
  - `skills/autonomous-concept-ui-redesign/SKILL.md`
  - `skills/autonomous-concept-ui-redesign/references/run-report-template.md`
  - `skills/autonomous-concept-ui-redesign/references/layout-geometry-qa.md`
  - `skills/flowpilot/SKILL.md`
  - `skills/flowpilot/references/protocol.md`
  - `templates/flowpilot/capabilities.template.json`
- Main findings:
  - The completed cockpit route selected
    `autonomous-concept-ui-redesign via FlowPilot child-skill selection`.
    `concept-led-ui-redesign` was an internal dependency for early design work,
    not the main FlowPilot route strategy.
  - The cockpit code sets a runtime-generated `QIcon` on the Qt application,
    main window, settings dialog, and tray icon, but there is no persistent
    selected icon source asset, `.ico`, AppUserModelID check, packaged
    executable icon, shortcut, or installer manifest evidence.
  - Future autonomous UI routes now require an app icon realization gate when
    the target is a desktop, mobile, packaged web, browser-extension, or
    branded software artifact. An icon shown only inside the UI or concept image
    is not enough.
  - Evidence must show whether the same selected icon source is bound to the
    runtime window/app icon, taskbar/dock/shelf identity, tray/menu-bar icon
    when present, and package/shortcut/installer manifest when packaging is in
    scope.
- Validation:
  - `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - `python -m json.tool templates/flowpilot/capabilities.template.json`
  - `python scripts/check_install.py`
  - `python scripts/install_flowpilot.py --install-missing --force --json`
  - `rg` checks for the new app icon realization wording in repository and
    installed skill copies
- Caveat:
  - `python scripts/install_flowpilot.py --check --json` reports the optional
    companion `concept-led-ui-redesign` skill is currently absent from the
    local Codex skills directory, even though the primary autonomous and
    FlowPilot skills are installed and source-fresh. This should be repaired or
    explicitly waived before another full autonomous concept route depends on
    that sibling skill.

## 2026-05-04 - FlowPilot Desktop Cockpit Clean Restart

- Trigger: the user requested a from-zero FlowPilot Windows desktop cockpit UI
  with live route/state mapping, multi-run tabs, bilingual UI, support entry,
  tray lifecycle, fresh concept/icon direction, screenshots, interaction
  checks, review, and iteration.
- Decision: `use_flowguard`.
- Models created: `.flowpilot/runs/run-20260503-233622-desktop-cockpit-restart/task-models/desktop-cockpit-process-control/`
  and `.flowpilot/runs/run-20260503-233622-desktop-cockpit-restart/task-models/desktop-cockpit-product-state/`.
- Main findings:
  - The cockpit implementation must treat real FlowPilot route/frontier/state
    files as source of truth and must not depend on a manual refresh click.
  - The support entry uses the local KB-approved PayPal URL
    `https://paypal.me/Yingxuliu` with support-only copy and no sales,
    warranty, priority, commercial-rights, or feature-promise language.
  - Fresh imagegen concept candidates and final screenshots are recorded in a
    generated-resource evidence ledger with explicit dispositions.
  - Native Qt screenshots should be captured from the real Windows platform on
    this host; offscreen rendering produced unreadable glyph boxes.
- Validation:
  - `python .flowpilot/runs/run-20260503-233622-desktop-cockpit-restart/task-models/desktop-cockpit-process-control/run_checks.py`
  - `python .flowpilot/runs/run-20260503-233622-desktop-cockpit-restart/task-models/desktop-cockpit-product-state/run_checks.py`
  - `python -m compileall -q flowpilot_cockpit tests`
  - `python -m unittest tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_cockpit_state_reader tests.test_flowpilot_cockpit_i18n`
  - `python scripts/check_install.py`

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

## 2026-05-02 - Retired Recovery Prototype History

- Historical status: superseded on 2026-05-04.
- Original scope: a broader recovery prototype explored local activity leases,
  reset orchestration, source-drift diagnostics, route-map refresh, and role
  identity separation.
- Current interpretation:
  - route maps and role identity remain relevant protocol work;
  - the recovery prototype itself is not an active FlowPilot requirement;
  - current startup, continuation, install, and lifecycle behavior must follow
    the 2026-05-04 current findings and executable checks instead of this
    historical prototype.

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
- Reviewer accepts stale or retired recovery evidence as current startup proof.
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
- `python -m py_compile` on the touched path, lifecycle, diagram, startup, meta,
  capability, install, and smoke scripts
- `python simulations\run_startup_pm_review_checks.py`
- `python simulations\run_meta_checks.py`
- `python simulations\run_capability_checks.py`
- `python scripts\check_install.py`
- `python scripts\smoke_autopilot.py`
- `python scripts\flowpilot_user_flow_diagram.py --root . --json`
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
- `simulations/startup_pm_review_model.py`
- `simulations/prompt_isolation_model.py`
- `simulations/flowpilot_router_loop_model.py`
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- none recorded

### Findings
- FlowGuard was used because this change affects FlowPilot authority, state,
  gate order, and idempotent role-event recording.
- The modeled risk was Controller treating direct prose, inline event payloads,
  or router hard-check internals as formal mail.
- Startup and prompt-isolation models now include hazards for non-file-backed
  reviewer/PM outputs, Controller direct free text, and Controller inspection of
  router hard-check internals.
- Router role events now require `report_path`/`report_hash` or
  `decision_path`/`decision_hash` for reviewer, officer, and PM report/decision
  events. Inline body keys such as `passed`, `decision`, `blockers`, `checks`,
  and `evidence` are rejected from Controller-visible payloads.
- Role cards now state that Controller is relay-only, every exchange must
  identify the active role boundary, and direct Controller text without a
  router-authorized envelope is unauthorized.
- The installed `flowpilot` skill was stale immediately after source edits and
  became fresh after `python scripts\install_flowpilot.py --sync-repo-owned --json`.

### Counterexamples
- none recorded

### Friction Points
- The combined `python scripts\smoke_autopilot.py` command timed out in the main
  thread because meta and capability graph checks are large. Its component
  checks were rerun individually and passed: card instruction coverage, release
  tooling, startup PM review, meta, and capability.
- The first control-gate test pass exposed only a message-string regression in
  `simulations/meta_model.py`; the model behavior was unchanged and the message
  was restored to include "six-role memory rehydration".

### Skipped Steps
- No release, remote push, or publication action was taken.
- Production conformance replay remains skipped where the abstract router-loop
  model has no production replay adapter.

### Next Actions
- none recorded


## flowpilot-runtime-protocol-hardening-20260506 - Harden router/result-review flow, artifact validation, display projection, and live skill issue reminders.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved a 13-point FlowPilot skill upgrade plan after observed run defects and required FlowGuard simulation before production edits.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-06

### Risk Intent
- Prevent reviewer pass/block decisions before the worker-result review card is actually delivered.
- Let safe packet/result envelope aliases pass through one normalized runtime path instead of causing avoidable human reissue loops.
- Keep completed route nodes visually completed when the frontier advances to the next active node.
- Add a lightweight, router-triggered reminder for Controller to record current-run FlowPilot skill issues without adding repeated fixed checklist noise.
- Give PM and worker roles a simple `validate-artifact` preflight so missing fields are found together before returning envelopes or node plans.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/packet_runtime.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/worker_b.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md`
- `skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md`
- `templates/flowpilot/flowpilot_skill_improvement_observation.template.json`
- `simulations/flowpilot_router_loop_model.py`
- `simulations/run_flowpilot_router_loop_checks.py`
- `simulations/defect_governance_model.py`
- `simulations/run_defect_governance_checks.py`
- `tests/test_flowpilot_router_runtime.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema `1.0`.
- OK: `python -m py_compile skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_router_loop_model.py simulations\run_flowpilot_router_loop_checks.py simulations\defect_governance_model.py simulations\run_defect_governance_checks.py tests\test_flowpilot_router_runtime.py`.
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`: no invariant failures, missing labels, stuck states, or nonterminating components.
- OK: `python simulations\run_defect_governance_checks.py`: new protocol-anomaly reminder hazard detected as expected and safe graph passed.
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k "current_node or display_plan or node_acceptance or control_blocker or validate_artifact"`: 10 passed.
- OK: `python -m pytest tests\test_flowpilot_barrier_bundle.py tests\test_flowpilot_card_instruction_coverage.py tests\test_flowpilot_router_runtime.py`: 62 passed.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed FlowPilot skill source digest matched repository digest.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- Result-review routing now requires the reviewer worker-result review card after result relay and before reviewer pass/block events.
- Packet/result envelope aliases are normalized centrally in `packet_runtime.py`, including `packet_body_path`, `packet_body_hash`, `body_path`, `body_hash`, `to_role`, and `next_holder`.
- Display-plan projection now gives completed node status priority over active-node fallback, so a finished nonterminal node does not remain `in_progress` when the frontier advances.
- Router control blockers now include `skill_observation_reminder` metadata, and Controller instructions tell it to record a skill issue only when the run exposed a FlowPilot protocol/card/router weakness.
- `validate-artifact` reports missing node-acceptance, packet-envelope, result-envelope, and role-output envelope fields together instead of forcing one manual repair loop per missing field.

### Counterexamples
- The router-loop model now rejects reviewer decisions without a delivered worker-result review card.
- The defect-governance model now rejects protocol anomalies reaching pause or completion without a skill-observation reminder.

### Friction Points
- During parallel work, previously tested patches disappeared from the tracked diff and had to be reapplied. Future long FlowPilot skill edits should explicitly verify `git diff` and source freshness before install sync, not only rely on earlier command success.
- Existing unrelated worktree changes were present in `.gitignore`, `scripts/smoke_autopilot.py`, `simulations/run_meta_checks.py`, `simulations/run_capability_checks.py`, and an untracked FlowGuard proof test; this task did not revert or overwrite them.

### Skipped Steps
- No UI implementation, release, remote push, or publication action was taken.
- Production conformance replay remains skipped for the abstract router-loop model because no production replay adapter exists in the current allowed scope.

### Next Actions
- Keep the router-triggered reminder lightweight; do not add a fixed repeated skill-issue checklist unless real runs show missed observations after this change.
- Add a future dedicated coordination check if parallel agents continue to make tested diffs disappear between validation and install sync.


## flowpilot-slow-model-proof-cache-20260506 - Add proof-backed fast reuse for slow FlowGuard meta/capability checks

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to speed up FlowPilot without lowering model quality by avoiding repeated full meta/capability checks when the model inputs and results have not changed.
- Status: completed_installed
- Skill decision: used_flowguard
- Date: 2026-05-06

### Risk Intent
- Preserve the existing full FlowGuard checks as the default and for forced validation.
- Allow `--fast` reuse only when the runner file, model file, FlowGuard schema version, and result file match a successful proof.
- Keep proof files local runtime artifacts rather than tracked source files.

### Implementation Files
- `simulations/run_meta_checks.py`
- `simulations/run_capability_checks.py`
- `scripts/smoke_autopilot.py`
- `tests/test_flowguard_result_proof.py`
- `.gitignore`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: `1.0`
- OK: `python -m py_compile simulations\run_meta_checks.py simulations\run_capability_checks.py scripts\smoke_autopilot.py tests\test_flowguard_result_proof.py`
- OK: `python -m unittest tests.test_flowguard_result_proof`
- OK by background subagent: `python simulations\run_meta_checks.py --force`: `598029` states, `618200` edges, progress OK, loop/stuck OK.
- OK by background subagent: `python simulations\run_capability_checks.py --force`: `557123` states, `582582` edges, progress OK, loop/stuck OK.
- OK: `python scripts\smoke_autopilot.py --fast`: reused both proof files.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The optimization does not skip first validation. It only reuses a result after a successful full run has written a matching proof.
- Any change to the model file, runner file, FlowGuard schema version, or result file invalidates the proof and returns to full validation unless another proof is generated.

### Skipped Steps
- No release, remote push, or publication action was taken.


## flowpilot-startup-banner-action-chat-instruction-20260506 - Put the banner chat-display instruction directly in the router action.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User wanted the FlowPilot startup banner preserved, with the simplest reliable prompt placed in the router's `emit_startup_banner` action itself.
- Status: completed_installed
- Skill decision: use_flowguard
- Started: 2026-05-06T00:00:00+02:00
- Ended: 2026-05-06T00:00:00+02:00

### Risk Intent
- Prevent another AI from treating a startup banner path, file, flag, or state record as equivalent to showing the banner in the user chat.
- Keep the fix small: no new proof system, no new banner state machine, and no extra generic skill rule beyond the router action prompt.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- OK: `python <codex-home>\skills\model-first-function-flow\assets\toolchain_preflight.py --json`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_banner_action_and_result_are_user_visible`.
- OK: `python simulations\run_prompt_isolation_checks.py`.
- OK: `python simulations\run_startup_pm_review_checks.py`.
- OK: `python simulations\run_meta_checks.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\check_install.py`.

### Findings
- `emit_startup_banner` now returns `display_text_format: plain_text`, `controller_must_display_text_before_apply: true`, `generated_files_alone_satisfy_chat_display: false`, and a `controller_display_rule` telling the host to paste the exact banner text into the user chat before applying the action or continuing.
- The installed local `flowpilot` skill was synchronized from repository source and audited as fresh.

### Skipped Steps
- No new FlowGuard model was created because the existing startup/prompt-isolation models already cover the hazard class: banner emitted without user-visible text. The change only strengthened the router action envelope for that already-modeled step.


## flowpilot-next-recipient-and-ui-snapshot-20260505 - Router-explicit next recipients, reviewed route activation, and UI-readable route snapshots

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that previous FlowGuard simulation did not prove that Controller always knows which role to contact next, and requested P0/P1 implementation before the native UI rebuild.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Prevent Controller from accepting officer/reviewer route-check results before the Router has delivered the matching work card.
- Prevent PM route activation from falling back to a dummy route when a reviewed draft exists.
- Ensure resume recovery derives the next packet recipient from `packet_ledger.json`, not chat memory.
- Give the future Windows Cockpit a canonical route snapshot built from `current.json`, route/frontier/state, and packet ledger rather than stale index entries.

### Model Files
- `simulations/router_next_recipient_model.py`
- `simulations/run_router_next_recipient_checks.py`
- `simulations/router_next_recipient_results.json`

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/manifest.json`
- `skills/flowpilot/assets/runtime_kit/cards/officers/route_process_check.md`
- `skills/flowpilot/assets/runtime_kit/cards/officers/route_product_check.md`
- `skills/flowpilot/assets/runtime_kit/cards/reviewer/route_challenge.md`
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py`
- `docs/legacy_to_router_equivalence.md`
- `docs/legacy_to_router_equivalence.json`
- `docs/flowpilot_ten_step_migration_status.json`

### Commands
- OK: `python -m py_compile simulations\router_next_recipient_model.py simulations\run_router_next_recipient_checks.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_router_next_recipient_checks.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_check_results_require_router_delivered_check_cards tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_role_output_envelope_writes_body_and_keeps_controller_visible_payload_sealed tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_display_plan_is_controller_synced_projection_from_pm_plan tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_current_node_packet_relay_requires_reviewer_dispatch`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_heartbeat_startup_records_one_minute_active_binding_for_resume_reentry tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_system_card_delivery_requires_manifest_check tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_product_architecture_and_root_contract_gate_route_skeleton`
- OK: `python scripts\check_install.py`
- OK by background subagent in temp copy: prompt isolation, resume, router loop, meta, capability, install self-check, and unittest suite (`Ran 87 tests ... OK`).
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The new FlowGuard model covers the explicit-next-recipient hazards: unknown next role, direct role pass without Router dispatch, dummy route activation, Controller content decision, duplicate worker ownership, wrong reissue target, resume without ledger-derived next, parent repair without PM segment decision, frontier rewrite without stale marking, UI using stale running index entries, and completion missing legacy obligations.
- Runtime route checks now require three Router-delivered cards before activation: process officer, product officer, then human reviewer.
- Every Router action carries `next_step_contract`, which makes the intended recipient and Controller boundaries explicit.
- `route_state_snapshot.json` and `active_ui_task_catalog` are runtime contracts for future UI work; they are not the native Windows UI itself.
- Installed `flowpilot` is fresh against repository source after sequential sync/check: installed digest equals source digest and `source_fresh=true`.

### Friction Points
- Running install, audit, and install-check in parallel can race while the installed skill directory is being overwritten. The final verification should run these sequentially.

### Skipped Steps
- No native Windows Cockpit UI implementation, release publication, or remote push was performed in this phase.


## flowpilot-router-next-recipient-contract-preflight-20260505 - Model explicit Router next-recipient authority before P0/P1 implementation.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that Controller can still be left to infer who should receive the next FlowPilot action after PM route drafts, reviewer blocks, resume recovery, worker packets, parent replay, and UI sync.
- Status: completed_model_preflight_only
- Skill decision: used_flowguard
- Mode: process_preflight

### Model Files
- Temporary inline FlowGuard model only; no production code or repository model file was added in this preflight.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: temporary inline model `flowpilot_router_next_recipient_contract_temp`

### Findings
- The temporary model passed with 25 states, 24 edges, one complete state, zero stuck states, zero Explorer violations, and all required explicit-recipient labels reachable.
- The hazard checks detected Controller unknown-next, direct role pass without router-dispatched package, dummy route activation, Controller content decision, double worker owner, wrong reissue target, resume without ledger-derived next recipient, parent repair without PM segment decision, frontier rewrite without stale evidence, stale running-index UI source, and completion with missing legacy obligation.
- Existing FlowGuard coverage did not fully model the user-facing risk that Controller may know the order but not the exact next recipient/action. P0/P1 should add this as a persistent model and runtime contract before production code changes.

### Skipped Steps
- No production code edits, persistent model files, install sync, or full regression suite were run as part of this preflight.
- Background broad regression was delegated separately with incremental logging requirements and was still running when this note was written.

### Next Actions
- Add a persistent next-recipient FlowGuard model during P0, then implement router-owned next actions for route checks, officer packets, repair/reissue, resume continuation, parent/terminal repair branches, and UI active-run snapshots.


## flowpilot-pm-minimum-sufficient-complexity-20260505 - Add PM anti-overengineering discipline to route and node decisions.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed that AI project managers often produce multi-dimensional, over-complex solutions when a simpler functionally equivalent route would meet the same goal.
- Status: completed_installed
- Skill decision: used_flowguard
- Date: 2026-05-05

### Risk Intent
- Prevent FlowPilot PM from treating high quality as permission to add unnecessary nodes, child skills, artifacts, dependencies, handoffs, or validation branches.
- Preserve the existing high-standard gates while requiring complexity to justify a concrete benefit: risk reduction, semantic fidelity, verification strength, maintenance reduction, failure isolation, or user-visible value.
- Make the rule durable in PM cards, templates, and FlowGuard/card-coverage checks rather than leaving it as a one-off prompt sentence.

### Model Files
- `simulations/card_instruction_coverage_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Implementation Files
- `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_root_contract.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_selection.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_evidence_quality_package.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md`
- `templates/flowpilot/product_function_architecture.template.json`
- `templates/flowpilot/root_acceptance_contract.template.json`
- `templates/flowpilot/pm_child_skill_selection.template.json`
- `templates/flowpilot/node_acceptance_plan.template.json`
- `templates/flowpilot/routes/route-001/flow.template.json`
- `templates/flowpilot/final_route_wide_gate_ledger.template.json`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `python -m py_compile simulations\card_instruction_coverage_model.py skills\flowpilot\assets\flowpilot_router.py`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python -m unittest tests.test_flowpilot_card_instruction_coverage`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: source/installed target card hash check for 11 PM cards.
- OK: running-run runtime card hash check for 11 PM cards across `run-20260505-122356`, `run-20260505-135230`, and `run-20260505-151908`.
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`
- OK by background subagent: `python simulations\run_card_instruction_coverage_checks.py`
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK by background subagent: `python simulations\run_user_flow_diagram_checks.py`
- OK by background subagent: `python simulations\run_startup_pm_review_checks.py`
- OK by background subagent: `python simulations\run_defect_governance_checks.py`
- OK by background subagent: `python simulations\run_release_tooling_checks.py`
- OK by background subagent after new model states: `python simulations\run_meta_checks.py`
- OK by background subagent after new model states: `python simulations\run_capability_checks.py`
- OK by background subagent: `python scripts\check_install.py`
- OK by background subagent: `python scripts\audit_local_install_sync.py --json`
- OK by background subagent: `python scripts\install_flowpilot.py --check --json`
- OK by background subagent: `python -m unittest tests.test_flowpilot_card_instruction_coverage tests.test_flowpilot_router_runtime tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram` with 90 tests.
- OK by background subagent: `python scripts\smoke_autopilot.py` after rerun with a longer timeout.

### Findings
- `Minimum Sufficient Complexity` is now a PM-wide decision rule: if two approaches meet the same frozen contract, user-visible behavior, quality bar, and proof strength, PM chooses the lower-complexity route.
- Complexity is now explicitly justified at product architecture, root contract, child-skill selection, route skeleton, current-node planning, node acceptance, repair, evidence quality, final ledger, and closure surfaces.
- Templates now preserve structured fields for simpler-path review, rejected extra complexity, complexity justifications, route/node complexity review, child-skill simpler-path review, and final unused-complexity dispositions.
- The card instruction coverage model now checks required PM cards for machine-detectable `Minimum Sufficient Complexity` wording and rejects a hazard card missing that guidance.
- The meta and capability FlowGuard models now require minimum-sufficient-complexity states before product architecture readiness, child-skill selection scope decisions, and node acceptance plans.
- Installed FlowPilot was refreshed from repository source and reports `source_fresh: true`.
- Existing running FlowPilot runtime card copies were updated where possible. Already loaded in-memory prompt text cannot be retroactively replaced, but future file reads and deliveries from those run-scoped cards see the new rule.

### Counterexamples
- The first new card-coverage run caught `pm.current_node_loop` and then `pm.evidence_quality_package` because the wording included the principle but lacked stable detectable simpler/smaller/unnecessary language. The cards were clarified and the check passed.
- `flowpilot_router.py` had a pre-existing local indentation error that blocked router import for card checks; a two-line indentation fix was applied so verification could load the router.

### Skipped Steps
- No release, remote push, Git commit, or PR was created.
- No frozen acceptance contract, current-run decisions, generated route, or sealed packet/result body was rewritten.


## flowpilot-control-blocker-already-recorded-resolution-20260505 - Resolve delivered control blockers from already-recorded follow-up events.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed a control-plane ordering issue where the corrected event was recorded before the blocker was marked delivered; a duplicate submission later returned `already_recorded` without clearing the delivered blocker.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: `1.0`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py`
- OK by background subagent: `python -m pytest -p no:cacheprovider -q tests/test_flowpilot_router_runtime.py`: 43 passed.
- OK by background subagent: `python simulations\run_meta_checks.py`: no invariant failures, no stuck loops, no unreachable success.
- OK by background subagent: `python simulations\run_capability_checks.py`: `ok=true`, no invariant failures, no stuck states.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`: installed `flowpilot` digest matches repository source.

### Findings
- The durable fix is intentionally narrow: when an external event is already recorded, the router now checks whether that same event is allowed to resolve the active delivered control blocker before returning `already_recorded`.
- The already-recorded compensation path is limited to `control_plane_reissue` blockers. PM-required or fatal protocol blockers still need their normal follow-up/recovery path and are not cleared by a duplicate already-recorded event.
- The follow-up event must still match the blocker's `allowed_resolution_events`; unrelated duplicates cannot clear a blocker.
- The router now clears `latest_control_blocker_path` when the active blocker is resolved, so the run state does not keep a stale active-blocker pointer after resolution.
- The active run was checked during the task and the matching ordering blocker was cleared. A later final inspection found `.flowpilot/current.json` and `run-20260505-151908` absent, so no further live-run patch could be applied safely from this thread.

### Skipped Steps
- No release, remote push, or destructive workspace action was taken.


## flowpilot-startup-route-sign-chat-display-20260505 - Require router-returned Mermaid route signs before startup display actions.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed that another AI could run FlowPilot without ever showing the Mermaid route sign in the chat, even though route-sign files were generated.
- Status: completed_installed
- Skill decision: use_flowguard
- Started: 2026-05-05T21:40:09+02:00
- Ended: 2026-05-05T21:40:09+02:00

### Risk Intent
- Prevent a file-only route-sign update from being treated as a visible user-facing Mermaid display.
- Ensure the startup router action returns exact Markdown Mermaid text and requires Controller to paste it in chat before applying the action.
- Keep Cockpit handling explicit: if Cockpit was requested, the router records a chat route-sign fallback plus reviewer/Cockpit probe requirements instead of silently claiming product UI success.

### Implementation Files
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/flowpilot_paths.py`
- `skills/flowpilot/assets/flowpilot_user_flow_diagram.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `.flowpilot/runs/run-20260505-151908/runtime_kit/cards/roles/controller.md`
- `simulations/user_flow_diagram_model.py`
- `simulations/run_user_flow_diagram_checks.py`
- `simulations/user_flow_diagram_results.json`
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- OK: `python <codex-home>\skills\model-first-function-flow\assets\toolchain_preflight.py --json`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\flowpilot_paths.py skills\flowpilot\assets\flowpilot_user_flow_diagram.py simulations\user_flow_diagram_model.py simulations\run_user_flow_diagram_checks.py scripts\check_install.py`.
- OK: `python simulations\run_user_flow_diagram_checks.py`: 82 states, 81 edges, 9/9 hazards detected, no missing labels, no invariant failures.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_skill_entrypoint_remains_small_router_launcher tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_activation_requires_reviewer_facts_before_work tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_cockpit_requested_startup_display_records_chat_fallback_mermaid`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK by background subagent: `python simulations\run_startup_pm_review_checks.py`, `python simulations\run_prompt_isolation_checks.py`, `python simulations\run_flowpilot_resume_checks.py`, `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`, `python simulations\run_meta_checks.py`, and `python simulations\run_capability_checks.py`.
- OK by background subagent: `python -m unittest tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_meta_route_sign tests.test_flowpilot_router_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_packet_runtime`.
- OK by background subagent: `python scripts\check_install.py` and `python scripts\smoke_autopilot.py`.

### Findings
- The startup display action now includes `display_text`, `display_text_format: markdown_mermaid`, `controller_must_display_text_before_apply: true`, `generated_files_alone_satisfy_chat_display: false`, and the route-sign Mermaid hash.
- Applying the display action writes the standard route-sign artifacts and records whether the request was chat or Cockpit. For Cockpit requests, the router selects `chat_route_sign_fallback` and records that Cockpit probing and reviewer fallback checks remain required.
- The installed local `flowpilot` skill was synchronized from repository source and audited as fresh.
- The active run `run-20260505-151908` does not carry its own `flowpilot_router.py` copy, so future router executions use the synchronized source/installed router. Its active Controller card was patched only with the new chat-display rule; other active runtime card differences were preserved to avoid split-brain changes while another AI is using the run.

### Counterexamples
- The user-flow diagram model now rejects the hazard where generated route-sign files are treated as chat-display evidence without router-returned Mermaid `display_text`.

### Skipped Steps
- No release, remote push, or broad active-run runtime kit overwrite was performed.


## flowpilot-router-control-blockers-20260505 - Route router hard rejections through structured control blocker artifacts.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that Controller was seeing router rejection reasons and needed a formal protocol for when to return a malformed envelope/report to the responsible role versus when to route a repair decision to PM.
- Status: completed_installed
- Skill decision: used_flowguard
- Date: 2026-05-05

### Risk Intent
- Make controller-visible router hard checks explicit rather than pretending they are sealed.
- Prevent Controller from turning hard-check error text into project repair instructions.
- Preserve the distinction between same-role control-plane reissue, PM-owned repair decisions, and fatal protocol violations.
- Avoid blocking normal stage-precondition tests by materializing only structural, audit, schema, and packet-chain hard rejections as control blockers.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md`
- `simulations/meta_model.py`
- `simulations/capability_model.py`
- `tests/test_flowpilot_router_runtime.py`
- `tests/test_flowpilot_control_gates.py`

### Commands
- OK: `python -m unittest tests.test_flowpilot_router_runtime`
- OK by background subagent: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py simulations\meta_model.py simulations\capability_model.py scripts\check_install.py`
- OK by background subagent: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_card_instruction_coverage`: 74 tests.
- OK by background subagent: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`: 27 traces, 0 invariant violations.
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK by background subagent: `python simulations\run_meta_checks.py`: 592,023 states, 612,194 edges, 0 invariant failures, 0 stuck states.
- OK by background subagent: `python simulations\run_capability_checks.py`: 554,749 states, 580,208 edges, 0 invariant failures, 0 stuck states.
- OK by background subagent: `python scripts\smoke_autopilot.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --dry-run --json`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- Router hard rejections now write run-scoped `control_blocks/*.json` artifacts with `handling_lane`, target role, controller instruction, allowed/forbidden controller actions, source paths, and a public envelope-only payload view.
- The next router action becomes `handle_control_blocker` before normal routing resumes. Applying that action records delivery in a control-blocker delivery ledger.
- `control_plane_reissue` goes to the responsible role for same-role envelope/report reissue. `pm_repair_decision_required` and `fatal_protocol_violation` go to Project Manager.
- A delivered blocker is cleared only after a follow-up event is accepted. Controller is not allowed to inspect sealed role bodies, infer project state from chat, or contact workers directly for PM-owned repairs.
- Initial broad wrapping of every `RouterError` over-blocked normal precondition tests. The final implementation restricts blocker materialization to structure, audit, schema, and packet-chain failures.
- Installed FlowPilot skill was refreshed from repository source. Installed digest and source digest match: `787d87abc08a6661ef48ea9a493bd1236a02033a4cafa34fbfac85c748a9cb10`.

### Counterexamples
- Broadly converting ordinary stage-precondition failures into active control blockers caused later router tests to receive `handle_control_blocker` instead of the next normal card. This was corrected by adding a materialization predicate.

### Skipped Steps
- No release, remote push, Git commit, or PR was created.
- Running agents that already loaded old skill text will not have that in-memory text retroactively replaced; future reads/executions of the installed skill files see the synced version.


## flowpilot-mutual-role-reminder-controller-relay-20260505 - Require visible mutual role reminders in Controller packet/result relay summaries.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested that Controller and every packet/result recipient see a recurring mutual reminder of Controller limits, sender identity, recipient role, body boundary, and the need to repeat the reminder on the next return relay.
- Status: completed_installed
- Skill decision: used_flowguard
- Date: 2026-05-05

### Risk Intent
- Prevent Controller-visible relay summaries from silently becoming generic mail forwarding without role/authority reminders.
- Ensure packet and result relays carry the same reminder loop: Controller is relay-only, the sender/producer is identified, the target role is identified, sealed body content remains out of Controller-visible chat, and the next return envelope must repeat the visible mutual-role reminder.
- Keep the reminder in envelope/controller-relay metadata rather than expanding sealed packet body preambles.

### Model Files
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `skills/flowpilot/assets/run_packet_control_plane_checks.py`

### Implementation Files
- `skills/flowpilot/assets/packet_runtime.py`
- `templates/flowpilot/packets/packet_envelope.template.json`
- `templates/flowpilot/packets/result_envelope.template.json`
- `tests/test_flowpilot_packet_runtime.py`
- Current active run metadata under `.flowpilot/runs/run-20260505-151908/`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py -q`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_router_runtime.py -q`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_prompt_isolation_checks.py`
- OK: `python -m py_compile skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\packet_control_plane_model.py skills\flowpilot\assets\run_packet_control_plane_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK by background subagent: `python simulations\run_capability_checks.py`; 554,749 states, 580,208 edges, missing labels 0, stuck 0, nonterminating 0.

### Findings
- `packet_runtime.py` now builds `flowpilot.mutual_role_reminder.v1` for Controller handoffs and Controller relay records.
- Packet and result relays now include `mutual_role_reminder` plus `reply_continuation_reminder`, so recipients are explicitly told to include the same visible reminder when returning or relaying the next envelope.
- The active run `run-20260505-151908` had existing relay metadata without the new block. Sixteen existing Controller relay entries were migrated in-place across `packet_ledger.json` and packet/result envelope files, without modifying sealed body files or body hashes.
- The first model check produced a useful counterexample: result-level missing reminder happens after the worker result exists, so the invariant was narrowed to block result body open, review pass, and PM advance rather than treating the already-created worker result as unsafe.

### Skipped Steps
- No release, remote push, or destructive operation was taken.
- The background capability regression was intentionally delegated so the main implementation and install sync could finish without waiting on a long model run; it later completed OK.


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


## flowpilot-barrier-bundle-equivalence-20260505 - Equivalent barrier-bundle simplification for FlowPilot control overhead

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that FlowPilot/FlowGuard control flow was too slow, but required equivalent simplification with no AI discretion to lower gates.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Reduce repeated control-plane prompt/check overhead while preserving all legacy obligations.
- Prevent AI agents from using the simplification as permission to skip reviewer, FlowGuard officer, packet ledger, cache hash, stale evidence, route frontier, final ledger, or terminal replay gates.
- Preserve role isolation by keeping barrier bundles as envelope/ledger metadata only; role packet/result bodies remain separate and target-role-only.

### Implementation Files
- `skills/flowpilot/assets/barrier_bundle.py`
- `skills/flowpilot/assets/packet_runtime.py`
- `skills/flowpilot/assets/flowpilot_router.py`
- `templates/flowpilot/barrier_bundle.template.json`
- `templates/flowpilot/packets/packet_envelope.template.json`
- `templates/flowpilot/packets/result_envelope.template.json`
- `docs/barrier_bundle_equivalence.md`
- `docs/legacy_to_router_equivalence.md`
- `docs/legacy_to_router_equivalence.json`
- `simulations/barrier_equivalence_model.py`
- `simulations/run_barrier_equivalence_checks.py`
- `simulations/barrier_equivalence_results.json`
- `tests/test_flowpilot_barrier_bundle.py`
- `scripts/check_install.py`
- `scripts/smoke_autopilot.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: `1.0`
- OK: `python -m py_compile skills\flowpilot\assets\barrier_bundle.py skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\flowpilot_router.py simulations\barrier_equivalence_model.py simulations\run_barrier_equivalence_checks.py scripts\check_install.py scripts\smoke_autopilot.py tests\test_flowpilot_barrier_bundle.py`
- OK by background subagent: `python simulations\run_barrier_equivalence_checks.py`
- OK by background subagent: `python -m unittest tests.test_flowpilot_barrier_bundle`
- OK by background subagent: `python scripts\check_install.py`
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK by background subagent: `python simulations\run_meta_checks.py`
- OK by background subagent: `python simulations\run_capability_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The executable barrier model covers 16 legacy obligations across 9 barriers and reports no missing obligations at completion.
- The FlowGuard explorer report passed with no violations, dead branches, exception branches, or reachability failures.
- Hazard checks detect AI discretion bypass, Controller sealed-body read/summarization, Controller-origin evidence, wrong-role approval, missing role slices, missing obligations, missing reviewer/officer gates, invalid cache reuse, stale evidence use, route mutation without stale/frontier markers, and final closure without clean ledger or terminal replay.
- The active-run comparison in `simulations/barrier_equivalence_results.json` records pre-route control transitions reduced from 26 prompt deliveries to 6 barriers, while explicitly preserving packet semantics, approvals, hashes, stale markers, and final replay.
- Installed `flowpilot` is source-fresh against the repository skill after sync.

### Counterexamples
- All modeled counterexamples were expected negative fixtures and were detected by the barrier equivalence model.

### Friction Points
- The repository had many concurrent uncommitted edits from other agents. The barrier change was kept mostly additive, with narrow runtime and install-check hooks.

### Skipped Steps
- No release, remote push, publication action, destructive cleanup, or broad formatter was run.

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
  the explicit startup questions, stops for a later answer set, and only then
  emits the startup banner.
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

## FlowPilot Route Sign Node Entry Freshness

- Task ID: `flowpilot-route-sign-node-entry-freshness-20260503`
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-03T22:20:00+02:00
- Ended: 2026-05-03T22:55:00+02:00
- Commands OK: true

### Model Files
- `simulations/meta_model.py`
- `simulations/user_flow_diagram_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile scripts\flowpilot_paths.py scripts\flowpilot_user_flow_diagram.py simulations\meta_model.py`
- OK: `python -m unittest discover -s tests`: 10 tests
- OK: `python simulations\run_user_flow_diagram_checks.py`: 72 states, 71 edges, no invariant failures
- OK: `python simulations\run_meta_checks.py`: 506342 states, 526510 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --check --json`: installed FlowPilot source digest matched repository source digest
- OK with warnings: `git diff --check` reported only CRLF normalization warnings

### Findings
- The repeated display failure had three causes: the concrete node-entry sequence did not call the route-sign display gate, the model allowed stale first-node display evidence to survive into later nodes, and the diagram path resolver did not understand active-run fields such as `active_run_id`, `route_id`, and `current_node`.
- Node entry now requires refreshing and visibly displaying the current-node FlowPilot Route Sign before focused grill-me, quality package work, node acceptance planning, child-skill execution, implementation, or checkpoint.
- The meta model now tracks `user_flow_diagram_fresh_for_current_node`; a later node cannot write its node acceptance plan using a stale route sign from an earlier node.
- The active-run alias fix was verified against the current `.flowpilot/current.json` layout and produced a route sign for `route-001` / `N2_CONCEPT` instead of `unknown`.

### Counterexamples
- The first meta-model attempt intentionally failed by detecting stale route-sign evidence, but it was too broad and also rejected valid intermediate states where the next node was in the middle of refreshing the route sign. The invariant was narrowed to the node acceptance plan boundary and backed by a fresh-current-node flag.

### Friction Points
- The active run had no `diagrams/` directory and no later-node display record, proving that previous fixes added trigger vocabulary but did not force the actual invocation path.

### Skipped Steps
- No new UI work was performed. The fix is limited to FlowPilot protocol, route-sign generation, templates, model checks, tests, and installed skill synchronization.

### Next Actions
- On the next FlowPilot invocation or resume, verify that entering a major route node displays the current-node Mermaid route sign before any node work starts when Cockpit is not visibly open.

## FlowPilot v0.2.0 Release Sync And Cockpit Gates

- Task ID: `flowpilot-v0-2-0-release-sync-cockpit-gates-20260504`
- Status: completed_validation_ready_for_publication
- Skill decision: use_flowguard
- Started: 2026-05-04T08:05:00+02:00
- Ended: 2026-05-04T08:41:25+02:00
- Commands OK: true

### Model Files
- `simulations/release_tooling_model.py`
- `simulations/startup_pm_review_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: repository-owned installed `flowpilot` and `autonomous-concept-ui-redesign` skills are source-fresh.
- OK: stale release/private-path search: no current hits for `v0.1.0`, local absolute user paths, or old three-question startup phrases in release-facing source paths.
- OK: `python -m compileall -q scripts simulations flowpilot_cockpit tests`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`: repo-owned installed skills fresh, installed skill names unique, Cockpit source files tracked.
- OK: `python simulations\run_release_tooling_checks.py`: 16 safe states, 15 safe edges, all release hazards detected.
- OK: `python simulations\run_startup_pm_review_checks.py`: 898 safe states, 897 safe edges, all startup display-surface hazards detected.
- OK: `python -m unittest tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_cockpit_state_reader tests.test_flowpilot_cockpit_i18n`: 26 tests.
- OK: `python simulations\run_meta_checks.py`: 533139 states, 553307 edges, no invariant failures, no stuck states, no nonterminating components.
- OK: `python simulations\run_capability_checks.py`: 520353 states, 545809 edges, no invariant failures, no stuck states, no nonterminating components.
- OK: `python simulations\run_user_flow_diagram_checks.py`
- OK: `python simulations\run_defect_governance_checks.py`
- OK: `git diff --check`: only CRLF normalization warnings.
- OK with expected pre-commit warning: `python scripts\check_public_release.py --skip-url-check --json`: zero errors, one warning for dirty worktree before commit.

### Findings
- A releaseable Cockpit change needs an explicit local-sync audit, not only ordinary install presence checks, because installed skills can be present but stale.
- Duplicate active installed skill names are a real local routing hazard; stale FlowPilot backup skills were moved out of the active Codex skills root before release validation.
- Cockpit source files must be tracked before release; an untracked native UI package would otherwise make a local demo pass while publishing an incomplete package.

### Counterexamples
- The release tooling model now detects release preparation while duplicate installed FlowPilot skill names exist.
- The release tooling model now detects release preparation while Cockpit source files remain untracked.

### Friction Points
- The local and remote `main` histories currently have no merge base, so the release must integrate `origin/main` without force-push or stop if only destructive publication would work.

### Skipped Steps
- Network URL checking was skipped in the public release preflight because dependency source shape was already checked and the release gate focused on local source, privacy, install, smoke, and FlowGuard validation.

### Next Actions
- Integrate remote `main` without force-push, then publish the prepared v0.2.0 source release.

## FlowPilot PM Highest-Reasonable-Standard Gate

- Task ID: `flowpilot-pm-high-standard-product-architecture-20260504`
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-04T09:42:00+02:00
- Ended: 2026-05-04T10:54:12+02:00
- Commands OK: true

### Model Files
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py`
- OK: JSON parse check for `templates/flowpilot/**/*.json`
- OK: `python simulations\run_meta_checks.py`: 533145 states, 553313 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python simulations\run_capability_checks.py`: 520359 states, 545815 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `python scripts\check_install.py`
- OK: `python scripts\smoke_autopilot.py`

### Findings
- The PM product-function architecture now includes an explicit high-standard posture: a FlowPilot invocation means the project is important and the PM sets the highest reasonably achievable worker standard, not a lowest-viable route.
- The product-function gate now requires a strongest feasible product target, an unacceptable-result review, and a semantic-fidelity/no-silent-downgrade policy before user-task, capability, route, or contract freeze can proceed.
- Material gaps now have an explicit default: add discovery/validation, stage the delivery with an explicit gap, ask the user, or block. They cannot silently redefine the requested product.
- Source and installed FlowPilot skill copies were synchronized for the user-facing rule text.

### Counterexamples
- A route can otherwise pass by converting a requested product into a thin seed-data demo or placeholder UI while claiming the narrower artifact is the product. The new model labels make that downgrade visible before contract freeze.

### Friction Points
- Full smoke now takes about nine minutes because it reruns both large meta and capability models after release/startup checks.
- The repository already had unrelated working-tree changes in cockpit, release, and documentation paths; this change stayed scoped to FlowPilot protocol, templates, model gates, and installed skill text.

### Skipped Steps
- No public release or GitHub publication work was performed.

### Next Actions
- In the next real FlowPilot UI run, verify the PM architecture packet explicitly rejects fake/placeholder maps, thin demos, and silent source-data downgrades before route generation.


## flowpilot-research-package-loop - Add PM-owned research package worker reviewer loop to FlowPilot

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot process-control behavior change with route, evidence, worker, reviewer, and experiment states
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-04T10:02:25+00:00
- Ended: 2026-05-04T10:02:25+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py`
- OK (0.000s): `python simulations\run_meta_checks.py`
- OK (0.000s): `python simulations\run_capability_checks.py`
- OK (0.000s): `python scripts\check_install.py`
- OK (0.000s): `python scripts\smoke_autopilot.py`
- OK (0.000s): `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\install_flowpilot.py --check --json`
- OK (0.000s): `python scripts\audit_local_install_sync.py --json`

### Findings
- Required material research now blocks downstream product architecture until PM package, worker report, reviewer direct source check, reviewer sufficiency, and PM absorption or route mutation are complete.
- Added material_research_gap_closed normalization to keep the executable graph finite while preserving the enforceable research gate.

### Counterexamples
- none recorded

### Friction Points
- Initial required/not-required research branching exceeded the 900000-state model threshold before downstream branch normalization; final meta and capability checks passed after normalization.

### Skipped Steps
- none recorded

### Next Actions
- Future FlowPilot material gaps should instantiate research package, worker report, and reviewer report artifacts rather than staying as informal notes.


## flowpilot-ui-iteration-budget-10-20 - Raise FlowPilot UI refinement budget

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot child-skill behavior change for UI refinement loops across source, installed skills, active runs, and heartbeat continuation prompts
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-04T12:12:00+02:00
- Ended: 2026-05-04T12:28:00+02:00

### Model Files
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\capability_model.py simulations\run_capability_checks.py scripts\check_install.py`
- OK: `python scripts\check_install.py`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: JSON parse and budget assertion for the active FlowPilot Cockpit run and active ProjectRadar run state/frontier files
- OK: `python simulations\run_capability_checks.py`: 522749 states, 548209 edges, no invariant failures, no missing labels, no stuck states, no nonterminating components
- OK: `git diff --check` for the FlowPilot repository and standalone autonomous UI skill repository, with only existing Windows line-ending warnings

### Findings
- FlowPilot now records the autonomous UI refinement budget as 10 `design-iterator` rounds by default and a maximum of 20 rounds when the user has not set a different count.
- The installed `flowpilot` and `autonomous-concept-ui-redesign` skill copies were synchronized with the repository source.
- The current FlowPilot Cockpit redesign run and current ProjectRadar FlowPilot run now carry explicit `ui_iteration_budget` state so heartbeat continuation can inherit the 10/20 budget.

### Counterexamples
- none recorded

### Skipped Steps
- `simulations/run_meta_checks.py` was not rerun because this change affects UI child-skill budget and capability routing, not startup/meta-process control flow.

### Next Actions
- Future UI child-skill gate manifests should preserve the recorded 10/20 budget unless the user explicitly requests a different iteration count.


## flowpilot-startup-capability-fallback-review - Require reviewer-verified startup capability fallback

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot startup protocol change affecting background-agent, scheduled-continuation, Cockpit display, PM gate, and reviewer evidence behavior
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-04T12:35:00+02:00
- Ended: 2026-05-04T12:55:00+02:00

### Model Files
- `simulations/startup_pm_review_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\startup_pm_review_model.py simulations\run_startup_pm_review_checks.py simulations\meta_model.py simulations\capability_model.py scripts\check_install.py`
- OK: JSON parse for `templates\flowpilot\state.template.json`, `templates\flowpilot\startup_review.template.json`, and `templates\flowpilot\startup_pm_gate.template.json`
- OK: `python simulations\run_startup_pm_review_checks.py`: 2610 states, 2609 edges, no invariant failures, no missing labels, all fallback hazards detected
- OK: `python simulations\run_meta_checks.py`: 539167 states, 559339 edges, no invariant failures, no missing labels, no stuck states
- OK: `python simulations\run_capability_checks.py`: 522749 states, 548209 edges, no invariant failures, no missing labels, no stuck states
- OK: `python scripts\check_install.py`: 177 checks passed

### Findings
- Startup answers are now modeled as requested capabilities rather than automatic proof that live agents, heartbeat, or Cockpit are available.
- Single-agent, manual-resume, and chat-display fallback require reviewer direct probing plus PM-recorded capability resolution; worker/front-executor claims alone are invalid.
- Heartbeat evidence must prove attachment to the current run/thread/workspace/frontier. A same-name automation in another location is explicitly rejected.
- Chat route signs can be a display fallback for a missing or damaged Cockpit, but they do not satisfy product work whose scope is to build or repair Cockpit UI.

### Counterexamples
- Detected fake fallback hazards: PM fallback without reviewer probe, worker-claimed unavailability accepted by PM, ambiguous capability status opened by PM, and same-name heartbeat accepted as current heartbeat.

### Skipped Steps
- `python scripts\smoke_autopilot.py` was not rerun because this change is protocol/model/template focused and the targeted startup, meta, capability, JSON, and install checks passed.

### Next Actions
- Future FlowPilot startup implementations should write `startup_capability_resolution`, reviewer capability probes, and PM fallback decisions before opening work beyond startup.


## flowpilot-packet-role-origin-audit - Require reviewer-verified packet author ownership

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User required every packet/result review to verify the actual responsible actor produced the work, and to reject controller-authored work products as boundary violations.
- Status: completed_installed
- Skill decision: use_flowguard
- Started: 2026-05-04T15:00:00+02:00
- Ended: 2026-05-04T15:27:24+02:00

### Model Files
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py skills\flowpilot\assets\packet_control_plane_model.py skills\flowpilot\assets\run_packet_control_plane_checks.py scripts\check_install.py`
- OK: JSON parse checks for touched FlowPilot templates
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`: no invariant violations, no dead branches, no reachability failures
- OK: `python simulations\run_meta_checks.py`: no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python simulations\run_capability_checks.py`: no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python -m unittest tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`

### Findings
- Reviewer now has an explicit per-packet role-origin audit gate before content review can pass.
- Controller-authored or unassigned-origin work products are blocked, require controller warning, and require PM repair or reissue.
- Installed `flowpilot` skill copy was synchronized after the source change.

### Counterexamples
- The packet model now covers the case where Controller submits work as if it were the responsible worker; the route blocks instead of passing review.

### Skipped Steps
- No release, remote push, or publication action was taken.

### Next Actions
- Future packet templates should preserve `role_origin_audit` fields as a hard reviewer gate, not optional evidence.


## flowpilot-packet-envelope-body-control-plane - Enforce envelope/body packet routing

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested the full packet envelope/body mechanism so Controller only routes envelopes and cannot read/execute worker bodies or close gates from controller-origin work.
- Status: completed_installed
- Skill decision: use_flowguard
- Started: 2026-05-04T15:35:00+02:00
- Ended: 2026-05-04T16:04:49+02:00

### Model Files
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py skills\flowpilot\assets\packet_control_plane_model.py skills\flowpilot\assets\run_packet_control_plane_checks.py scripts\check_install.py`
- OK: JSON parse for all `templates/flowpilot/**/*.json`: 55 templates
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`: 18 traces, no invariant violations, no dead branches, no reachability failures
- OK: `python -m unittest tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram`: 23 tests
- OK: `python scripts\check_install.py`: installed-template and retired-path checks passed
- OK: `python simulations\run_meta_checks.py`: 568935 states, 589107 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python simulations\run_capability_checks.py`: 539933 states, 565393 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`: `flowpilot` source_fresh true
- OK: `python scripts\audit_local_install_sync.py --json`: repo-owned installed skills fresh
- OK: `git diff --check`: only Windows line-ending warnings

### Findings
- Added packet envelope/body and result envelope/body templates plus controller status packets.
- `packet_ledger` is now `flowpilot.packet_ledger.v2` and records envelope/body paths, hashes, holder history, controller envelope-only visibility, result envelope author fields, and envelope-aware role-origin audit fields.
- Reviewer/PM gates now require `packet_envelope_body_audit_done` before content review, then the existing per-packet role-origin audit.
- The packet model blocks controller body reads, controller body execution, wrong delivery, packet/result body hash mismatch, stale body reuse, wrong-role result completion, and controller-origin artifacts.
- Installed `flowpilot` skill copy was synchronized with repository source.

### Counterexamples
- Model preflight initially showed heartbeat resume of an existing worker result could bypass packet-envelope/hash evidence if prior ledger checks were not modeled. The heartbeat branch now loads prior packet envelope and body hash checks before reviewer review.

### Skipped Steps
- No UI redesign, release, remote push, or publication action was taken.

### Next Actions
- Future FlowPilot runtime work should instantiate `packets/<packet-id>/packet_envelope.json`, `packet_body.md`, `result_envelope.json`, `result_body.md`, and `controller_status_packet.json` from these templates for real route runs.


## flowpilot-physical-packet-runtime - Enforce file-backed envelope/body handoff

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that envelope/body routing must be a real file-backed runtime handoff, not only a declarative rule or template.
- Status: completed_installed
- Skill decision: use_flowguard
- Started: 2026-05-04T16:12:00+02:00
- Ended: 2026-05-04T17:17:31+02:00

### Model Files
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Runtime Files
- `skills/flowpilot/assets/packet_runtime.py`
- `scripts/flowpilot_packets.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile skills\flowpilot\assets\packet_runtime.py scripts\flowpilot_packets.py scripts\check_install.py`
- OK: `python -m py_compile simulations\meta_model.py simulations\run_meta_checks.py simulations\capability_model.py simulations\run_capability_checks.py tests\test_flowpilot_control_gates.py`
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates`
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`: 20 traces, no invariant violations, no dead branches, no reachability failures
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram`: 31 tests
- OK: JSON parse for all `templates/flowpilot/**/*.json`: 55 templates
- OK: `python simulations\run_meta_checks.py`: 573799 states, 593971 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python simulations\run_capability_checks.py`: 544973 states, 570433 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python scripts\check_install.py`
- OK: CLI smoke: `scripts\flowpilot_packets.py` issued a packet and controller handoff omitted the body sentinel
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`: `flowpilot` source_fresh true
- OK: `python scripts\audit_local_install_sync.py --json`: repo-owned installed skills fresh
- OK: `git diff --check`: only Windows line-ending warnings

### Findings
- Added an installed runtime that writes physical `packet_envelope.json`, `packet_body.md`, `result_envelope.json`, `result_body.md`, `controller_status_packet.json`, and `packet_ledger.json` entries.
- Controller handoff is generated from envelope fields only. Runtime tests verify body text does not appear in controller handoff.
- Reviewer validation now checks physical file hashes, packet/result role origin, completed-agent role membership, wrong-role completion, and controller-origin completion.
- Meta and capability models now require `packet_runtime_physical_isolation_verified` before envelope/body audit and role-origin review can open.

### Counterexamples
- A controller handoff containing packet body content is now modeled as `controller_handoff_body_content_blocked` and cannot dispatch, review, or advance.
- A PM packet without physical files is now modeled as `missing_physical_packet_files_blocked` and cannot dispatch.

### Skipped Steps
- No OS-level file permissions or encryption were added; the accepted scope was real files, controller context isolation, and review blocking.
- No UI redesign, release, remote push, or publication action was taken.

### Next Actions
- Future FlowPilot route execution should call `packet_runtime.py` or `scripts\flowpilot_packets.py` when issuing and completing work packets, and should never paste body text into controller-visible chat.


## flowpilot-controller-relay-mail-chain - Enforce controller-signed mail routing

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User required all formal FlowPilot mail to route through Controller, with Controller relay signatures, no-read/no-execute attestations, recipient pre-open checks, sender reissue on contamination, reviewer chain audit, startup user-intake mail, and heartbeat prompts aligned to the mail ledger.
- Status: completed_installed
- Skill decision: use_flowguard
- Started: 2026-05-04T17:20:00+02:00
- Ended: 2026-05-04T18:20:00+02:00

### Model Files
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Runtime Files
- `skills/flowpilot/assets/packet_runtime.py`
- `scripts/flowpilot_packets.py`

### Commands
- OK: `python -m py_compile skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\packet_control_plane_model.py skills\flowpilot\assets\run_packet_control_plane_checks.py simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py scripts\check_install.py scripts\flowpilot_packets.py`
- OK: `python -m unittest tests.test_flowpilot_packet_runtime`: 10 tests
- OK: `scripts\flowpilot_packets.py` CLI smoke: issue, packet handoff, controller relay, recipient body open, complete, result handoff, controller result relay, reviewer result open, review, and chain audit all passed without body leakage in controller handoffs
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram`: 37 tests
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`: 25 traces, no invariant violations, no dead branches, no reachability failures
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`: 578663 states, 598835 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python simulations\run_capability_checks.py`: 550013 states, 575473 edges, no invariant failures, no missing labels, no stuck/nonterminating states

### Findings
- Runtime now supports `controller_relay` signatures for packet and result envelopes, including no-read/no-execute fields, holder transitions, envelope hash, and recipient pre-open verification.
- Recipients cannot open packet or result bodies until the relevant controller relay signature is present and valid.
- Controller contamination or private role-to-role delivery returns the envelope to sender and requires a new replacement packet rather than post-hoc signing or relabelling.
- Reviewer chain audit now flags missing relay signatures, unopened mail, contamination without replacement, and private delivery, then sends PM a restart, repair-node, or sender-reissue decision boundary.
- Startup user prompts are written as a physical `user_intake` packet to PM, while explicit startup options remain controller-visible bootstrap instructions.
- Heartbeat prompts now load state, frontier, crew memory, packet ledger, relay history, and chain audit status without opening sealed bodies.

### Counterexamples
- CLI smoke initially exposed that result envelope handoff still assumed packet-only `from_role` and `to_role` fields. `build_controller_handoff` now handles both packet envelopes and result envelopes without leaking sealed body text.

### Skipped Steps
- No encryption or OS-level ACLs were added; the accepted enforcement layer is physical files, controller context isolation, relay attestations, recipient checks, and reviewer/PM blocking.
- No UI redesign, release, remote push, or publication action was taken.

### Next Actions
- Use the new runtime mail path for the next FlowPilot run startup: Controller bootstraps explicit user options, writes `user_intake` to PM, relays it with a controller signature, and PM starts only after reviewer startup-gate mail review.


## flowpilot-prompt-isolation-state-machine - Model minimal prompt injection and packet routing

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified prompt contamination risk and requested a FlowGuard simulation before changing FlowPilot startup, PM, Controller, and role prompt injection behavior.
- Status: design_model_passed
- Skill decision: use_flowguard
- Started: 2026-05-04T19:00:00+02:00
- Ended: 2026-05-04T19:41:22+02:00

### Model Files
- `simulations/prompt_isolation_model.py`
- `simulations/run_prompt_isolation_checks.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile simulations\prompt_isolation_model.py simulations\run_prompt_isolation_checks.py`
- OK: `python simulations\run_prompt_isolation_checks.py`: 173 states, 172 edges, 4 complete states, no invariant failures, no missing labels, all hazard states detected

### Findings
- The proposed design now has an executable model for a minimal bootloader, copied runtime kit, user-intake packet, Controller-only relay role, PM controller-reset duty, phase/event prompt cards, reviewer dispatch, worker result review, route activation, current-node repair, final ledger, and closure.
- The model exposes a real `flowguard.Workflow` wrapper and invariant while keeping a small explicit state graph runner for required-label, hazard, and reachability reporting.
- The model treats PM and Controller as limited state roles: they only act after the current prompt card or PM decision explicitly instructs them.
- The bootloader startup is now modeled as two separate actions: router computes an explicit `next_action`, then the bootloader performs exactly one startup action. Startup facts such as banner emission or run-shell creation fail if they appear without a matching router-approved bootloader action.
- Every system prompt-card delivery requires a prior Controller instruction to check the prompt manifest.
- Every runtime packet/result delivery requires a prior Controller instruction to check the packet ledger.
- PM cannot use worker output until reviewer review produces an event back to PM, and current-node repair requires both repair phase and reviewer-blocked event cards.

### Counterexamples
- The model detects banner before answers, banner/run-shell progression without a router `next_action`, bootloader-generated prompt bodies, roles before copied kit, user intake before PM bootstrap cards, work before PM resets Controller, worker body without reviewer dispatch, PM use of unreviewed evidence, route activation without officer/reviewer checks, node packet without node cards, repair packet without block event card, final ledger before node completion, completion before closure cleanup, prompt delivery without manifest instruction, mail delivery without ledger instruction, Controller body reads, Controller-origin project evidence, and wrong-role prompt/body delivery.

### Skipped Steps
- No FlowPilot skill code, runtime templates, installed skill copy, heartbeat automation, background agents, UI code, release, remote push, or publication action was changed.
- This is a design-level executable model only; implementation must still add the bootloader router, runtime kit, prompt delivery manifest, and validators.

### Next Actions
- Convert the current monolithic FlowPilot skill into a small router/bootloader plus role-scoped prompt cards and a runtime prompt-delivery manifest.
- Add implementation validators equivalent to this model before allowing a real FlowPilot run to use the new startup path.


## flowpilot-prompt-isolation-clean-rebuild - Router and card runtime implementation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested the legacy FlowPilot program be preserved as a second backup, then rebuilt from scratch around the prompt-isolation router/system-card/packet-ledger model rather than patched in place.
- Status: implementation_partially_verified
- Skill decision: use_flowguard
- Started: 2026-05-04T19:58:00+02:00
- Ended: 2026-05-04T20:15:23+02:00

### Backup Files
- `backups/flowpilot-20260504-second-backup-20260504-195841/`
- `backups/flowpilot-20260504-second-backup-20260504-195841.zip`

### Implementation Files
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/manifest.json`
- `skills/flowpilot/assets/runtime_kit/cards/`
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py`

### Commands
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`: 7 tests
- OK: `python scripts\check_install.py`: includes router/runtime-kit files, prompt-isolation result files, and second-backup preservation check
- OK: `python simulations\run_prompt_isolation_checks.py`: 173 states, 172 edges, 4 complete states, no invariant failures, no missing labels, all hazard states detected
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_router_runtime`: 42 tests
- OK: `python simulations\run_meta_checks.py`: 578663 states, 598835 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK: `python simulations\run_capability_checks.py`: 550013 states, 575473 edges, no invariant failures, no missing labels, no stuck/nonterminating states, no nonterminating components, 4368 complete terminal states

### Findings
- The active FlowPilot skill entry is now a small bootloader instruction file. It tells the assistant to run the router, execute exactly one router action, record it, and return to the router.
- `flowpilot_router.py` creates and validates pending action envelopes for startup, copies an audited runtime kit, initializes run-scoped mailbox/ledger state, and then switches to Controller-owned manifest/ledger delivery.
- The runtime kit splits former long prompt content into role core cards, PM phase cards, PM event cards, reviewer cards, and a startup banner card. Cards are data; they do not advance the route by themselves.
- System cards are manifest-addressed with `from: system`, `issued_by: router`, and `delivered_by: controller`.
- The first PM bootstrap sequence now delivers PM core, Controller reset duty, PM phase map, and startup-intake card before ledger delivery of `user_intake`.
- Follow-on phase/event cards require matching state flags, so final-ledger/current-node/repair cards are not delivered at startup.
- `check_install.py` now verifies the router, runtime kit, prompt-isolation model artifacts, and the second backup manifest plus zip archive.

### Counterexamples
- `tests.test_flowpilot_router_runtime` initially exposed that the first router implementation delivered later PM phase cards before the `user_intake` mail. The router now requires explicit state flags before later phase/event cards become due.

### Skipped Steps
- The installed global Codex skill copy was not synced in this pass.
- No release, remote push, publication, Cockpit UI work, heartbeat automation, or formal FlowPilot route was started.
- The new router currently implements the startup/bootstrap and first Controller card/mail gates plus role-event recording. Full current-node packet orchestration still relies on existing packet runtime and must be integrated further with route/frontier state.

### Next Actions
- Wait for the background capability model result and fix any reported gap.
- Extend router/controller integration from bootstrap gates into the full current-node packet loop and final-ledger loop.
- Update install/audit scripts if global installed-skill synchronization is requested.


## flowpilot-prompt-isolation-resume-current-node-loop - Resume and packet-loop enforcement

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved the clean-rebuild plan and requested execution with subagents for large FlowGuard simulations and regressions.
- Status: implementation_verified_local
- Skill decision: use_flowguard
- Started: 2026-05-04T20:16:00+02:00
- Ended: 2026-05-04T20:58:09+02:00

### Implementation Files
- `docs/flowpilot_clean_rebuild_plan.md`
- `docs/legacy_to_router_equivalence.md`
- `docs/legacy_to_router_equivalence.json`
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/manifest.json`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_resume_decision.md`
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py`

### Model Files
- `simulations/flowpilot_resume_model.py`
- `simulations/run_flowpilot_resume_checks.py`
- `simulations/flowpilot_resume_results.json`
- `simulations/flowpilot_router_loop_model.py`
- `simulations/run_flowpilot_router_loop_checks.py`
- `simulations/flowpilot_router_loop_results.json`
- `simulations/prompt_isolation_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py tests\test_flowpilot_router_runtime.py simulations\run_flowpilot_resume_checks.py simulations\run_flowpilot_router_loop_checks.py simulations\flowpilot_resume_model.py simulations\flowpilot_router_loop_model.py`
- OK: JSON parse for `docs\legacy_to_router_equivalence.json`, `simulations\flowpilot_resume_results.json`, `simulations\flowpilot_router_loop_results.json`, and `skills\flowpilot\assets\runtime_kit\manifest.json`
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_router_runtime`: 49 tests
- OK: `python simulations\run_prompt_isolation_checks.py`: 173 states, 172 edges, 4 complete states, no invariant failures, no missing labels, all hazards detected
- OK: `python simulations\run_flowpilot_resume_checks.py`: 129 states, 128 edges, 8 complete states, 4 blocked states, no invariant failures, no missing labels, all 25 hazards detected
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`: 34 states, 33 edges, 2 complete states, 3 blocked states, no invariant failures, no missing labels, no stuck states, no nonterminating components, all hazards detected
- OK: `python scripts\check_install.py`: runtime kit, card manifest, packet schema, equivalence JSON, resume/router-loop result files, and second-backup preservation checks passed
- OK: `python simulations\run_release_tooling_checks.py`: 16 states, 15 edges, no invariant failures, no missing labels, all hazards detected
- OK: `python simulations\run_startup_pm_review_checks.py`: 2610 states, 2609 edges, no invariant failures, no missing labels, all hazards detected
- OK by background subagent: `python simulations\run_meta_checks.py`: 578663 states, 598835 edges, no invariant failures, no missing labels, no stuck/nonterminating states
- OK by background subagent: `python simulations\run_capability_checks.py` equivalent runner logic: 550013 states, 575473 edges, no invariant failures, no missing labels, no stuck/nonterminating states. The first direct command attempt timed out at the subagent tool boundary after 124 seconds before output capture; the completed read-only regression passed.
- Partial: `python scripts\smoke_autopilot.py` exceeded the foreground tool timeout after 244 seconds because it serially runs release, startup, meta, and capability checks. The four constituent checks passed separately or by background subagent.
- OK: `git diff --check`: line-ending warnings only for modified text files; no whitespace errors.

### Findings
- Added resume re-entry system cards for Controller and PM. Controller now loads current-run state, frontier, packet ledger, and crew memory into `continuation/resume_reentry.json` without sealed-body reads or chat-history progress inference.
- The router now writes minimal `execution_frontier.json` and per-role `crew_memory/*.json` during startup.
- Startup `user_intake` and current-node work now use the physical `packet_runtime` schema `flowpilot.packet_ledger.v2`.
- Current-node execution is now gated by route activation, PM packet registration, reviewer dispatch approval, packet ledger checks, Controller envelope-only relay, worker result relay to reviewer, reviewer audit, and only then PM node completion.
- Route activation writes a run-scoped route/frontier skeleton. Reviewer-block route mutation writes mutation state and rewrites the active frontier to a repair node.
- Final-ledger and terminal replay events now have router preconditions; they cannot be recorded from a stale or incomplete node path.
- `check_install.py` now verifies legacy-to-router equivalence entries, duplicate-free manifest cards, hard Controller policy flags, packet-runtime schema alignment, and the new model result artifacts.

### Counterexamples
- Unit review exposed that `reviewer_reports_material_insufficient` was being classified as sufficient because the event string also ends with `sufficient`. The router now uses explicit event branches, and `tests.test_flowpilot_router_runtime` covers the insufficient case.
- Router-loop modeling detects completion before final backward replay, final replay before clean ledger, final ledger with unresolved items, PM completion without reviewer pass, reviewer pass before routed worker result, stale mutation frontier reuse, worker dispatch before reviewer approval, Controller-origin project evidence, and Controller sealed-body reads.
- Resume modeling detects dynamic launcher use, chat-history progress inference, old-run state reuse, ambiguous state without PM recovery, Controller-origin evidence, Controller self-approval, missing manifest/ledger checks, existing result routing without reviewer dispatch, and replacement crew without memory seed.

### Skipped Steps
- No global installed Codex skill copy was synced in this pass.
- No formal FlowPilot run, heartbeat automation, Cockpit UI work, release, remote push, or publication action was started.
- Abstract resume and router-loop conformance replay adapters are not yet implemented; the checks are executable design/state models plus runtime unit/self-check coverage.

### Next Actions
- Extend the router to full multi-node route resolver validation with route-version matching.
- Add officer/research packet loops and PM absorb-or-mutate decisions.
- Add stale-evidence and generated-resource ledger writers for route mutation and final closure.
- Add final ledger file writer, unresolved-count/resource validation, terminal closure-suite events, and production replay adapters for promoted abstract models.


## flowpilot-legacy-prompt-to-cards-matrix - Migration inventory and startup-gate reduction

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to compare old FlowPilot prompt behavior against the clean card/router rebuild before deciding which startup gates and role cards to implement next.
- Status: documentation_verified_local
- Skill decision: skip_with_reason for a new FlowGuard behavior model in this step. This pass produced a traceable migration inventory and install self-check, but did not change runtime route behavior.
- Date: 2026-05-04

### Implementation Files
- `docs/legacy_prompt_to_cards_matrix.md`
- `docs/legacy_prompt_to_cards_matrix.json`
- `scripts/check_install.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m json.tool docs\legacy_prompt_to_cards_matrix.json`
- OK: `python -m py_compile scripts\check_install.py`
- OK: `python scripts\check_install.py`

### Findings
- All 45 second-backup legacy `##` prompt sections are mapped to a current or planned card, validator, template/runtime artifact, router invariant, or intentional deferral.
- The old startup hard gate should not be copied wholesale. Prompt-overread protections move to the small launcher, manifest delivery, router pending actions, and packet ledgers.
- Real external startup checks remain hard: three startup answers, current-run authority, same-task crew freshness or explicit fallback, heartbeat/manual continuation evidence, display-surface evidence, old-state quarantine, and PM startup opening from independent reviewer facts.
- Background read-only audits corrected the matrix classification for chat route signs, strict-gate obligation review, quality package detail, capability routing fidelity, old visual evidence reuse, dependency installation policy, and reference-file preservation.

### Skipped Steps
- No production router behavior changed, so no new FlowGuard model or conformance replay was added in this pass.
- Startup fact-check, PM activation, chat route-sign refresh, dependency-policy, material/research, and strict-gate cards are identified as next work but not implemented here.


## flowpilot-ten-step-clean-rebuild-completion - Packet, evidence, resume, and final-ledger runtime

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested the ten-step clean rebuild be executed continuously, with background subagents handling heavy simulation and regression checks.
- Status: implementation_verified_and_installed_source_fresh
- Skill decision: use_flowguard
- Date: 2026-05-04

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/manifest.json`
- `skills/flowpilot/assets/runtime_kit/cards/reviewer/final_backward_replay.md`
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py`
- `docs/flowpilot_ten_step_migration_status.json`
- `docs/legacy_to_router_equivalence.md`
- `docs/legacy_to_router_equivalence.json`
- `docs/legacy_prompt_to_cards_matrix.md`
- `docs/legacy_prompt_to_cards_matrix.json`
- `docs/flowpilot_clean_rebuild_plan.md`
- `HANDOFF.md`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`: 21 tests
- OK: `python scripts\check_install.py`: 54 runtime cards, manifest/card validity, packet schema, legacy maps, ten-step status, and second backup preservation checks passed
- OK by background subagent: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_router_runtime`: 58 tests
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`: 349 states, 348 edges, 54 hazards detected
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`: 129 states, 128 edges, 1986 traces, zero violations
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`: 91 states, 90 edges, 5199 traces, zero violations
- OK by background subagent: `python simulations\run_meta_checks.py`: 578663 states, 598835 edges, zero invariant failures
- OK by background subagent: `python simulations\run_capability_checks.py`: 550013 states, 575473 edges, zero invariant failures
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed `flowpilot` source refreshed
- OK: `python scripts\audit_local_install_sync.py --json`: `flowpilot` and `autonomous-concept-ui-redesign` source_fresh true
- OK: `python scripts\install_flowpilot.py --check --json`: dependency and host capability checks passed

### Findings
- Material scan, research, and current-node work now route through physical packet/result envelopes with Controller limited to envelope relay.
- PM evidence quality package now writes evidence, generated-resource, and quality ledgers; stale/unresolved evidence, pending resources, missing UI screenshots, and reused old UI assets block the gate.
- Resume now blocks ambiguous continuation until PM writes an explicit recovery decision with a controller-reminder boundary.
- PM final ledger now writes `final_route_wide_gate_ledger.json` and `terminal_human_backward_replay_map.json`; reviewer final backward replay writes `reviews/terminal_backward_replay.json` and opens completion only after terminal replay passes.
- FlowGuard model updates and runtime regressions now catch premature final ledger, final replay before reviewer card, stale/unresolved evidence, missing UI screenshots, old visual asset reuse, and unsafe resume continuation.

### Skipped Steps
- Generalized async FlowGuard officer request/report packets, automatic multi-node traversal beyond the current active-node resolver, old-state import quarantine, and closure-suite lifecycle writing remain future expansion work.


## flowpilot-non-ui-runtime-upgrade - Heartbeat, standards, replay, mutation, and closure invalidation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to execute the first eight non-UI FlowPilot upgrade steps, with heavy model checks delegated to background subagents.
- Status: implementation_verified
- Skill decision: use_flowguard
- Date: 2026-05-05

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/manifest.json`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_continuation_capability_binding.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_crew_rehydration_freshness.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_officer_request_report_loop.md`
- `skills/flowpilot/assets/runtime_kit/cards/reviewer/strict_gate_obligation_review.md`
- `tests/test_flowpilot_router_runtime.py`
- `simulations/flowpilot_resume_model.py`
- `simulations/flowpilot_router_loop_model.py`
- `docs/flowpilot_ten_step_migration_status.json`
- `docs/legacy_prompt_to_cards_matrix.md`
- `docs/legacy_prompt_to_cards_matrix.json`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_resume_model.py simulations\flowpilot_router_loop_model.py simulations\prompt_isolation_model.py scripts\check_install.py scripts\smoke_autopilot.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`: 28 tests
- OK: `python scripts\check_install.py`: 58 runtime cards, legacy matrix, ten-step status, JSON, packet schema, and second backup checks passed
- OK: `python simulations\run_prompt_isolation_checks.py`: 349 states, 348 edges, hazards detected as expected, zero violations
- OK: `python simulations\run_flowpilot_resume_checks.py`: 134 states, 133 edges, hazards detected as expected, zero violations
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`: State Graph ok, 70 sequences, 7446 traces, zero violations; progress review ok with 114 states
- OK by background subagent: `python simulations\run_meta_checks.py`: State Graph, Progress Review, and Loop/Stuck Review all ok, about 5m15s
- OK by background subagent: `python simulations\run_capability_checks.py`: Capability State Graph, Progress Review, and Loop/Stuck Review all ok, about 6m34s
- OK by background subagent: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_control_gates tests.test_flowpilot_defects tests.test_flowpilot_meta_route_sign tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_router_runtime`: 72.8s, no failures
- OK by background subagent: `python scripts\smoke_autopilot.py`: 448s, no failures

### Findings
- Continuation now records manual resume or verified one-minute host heartbeat binding, and heartbeat ticks re-enter resume recovery when the work chain is broken or unknown.
- PM node acceptance plans now require a structured high-standard recheck before worker dispatch.
- Final ledger construction now rebuilds source-of-truth entries from the frozen root contract replay, effective route nodes, child-skill gates, ledgers, and route mutation history.
- Parent backward review failures now mutate the route, preserve superseded history, write stale-evidence records, and restart review from the repair node.
- Terminal backward replay now requires generated review segments plus reviewer and PM decisions for each segment before closure.
- A unit regression exposed that dirty ledgers after terminal replay could still receive the PM closure card. The router now invalidates the route-completion chain before closure and restarts from PM evidence quality instead.

### Skipped Steps
- UI/Cockpit implementation was explicitly excluded by the user.
- Generalized officer packet runtime, old-state import quarantine importer, run-mode policy, route-sign refresh, explicit defect/role-memory closure reconciliation, and final user-report generation remain planned follow-up surfaces.


## flowpilot-final-mode-retirement-identity-install - Final validation and local sync

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to complete the final FlowPilot cleanup steps, delegate heavy regression to background subagents, and sync the local installed skill last.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Implementation Files
- `docs/legacy_prompt_to_cards_matrix.md`
- `docs/legacy_prompt_to_cards_matrix.json`
- `docs/flowpilot_ten_step_migration_status.json`
- `simulations/meta_model.py`
- `simulations/capability_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile scripts\check_install.py simulations\meta_model.py simulations\capability_model.py`
- OK: `python scripts\check_install.py`: run-mode retirement, identity templates, 45-entry legacy matrix, and second backup preservation passed
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`: conformance replay skipped with explicit no-production-adapter reason
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`: conformance replay skipped with explicit no-production-adapter reason
- OK by background subagent: `python simulations\run_startup_pm_review_checks.py`
- OK by background subagent: `python simulations\run_meta_checks.py`: 578661 states, 598832 edges, zero invariant failures, zero stuck states
- OK by background subagent: `python simulations\run_capability_checks.py`: 550011 states, 575470 edges, zero invariant failures, zero stuck states
- OK by background subagent: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime`: 40 tests in 68.237s
- OK by background subagent: `python scripts\smoke_autopilot.py`: ok true; model smoke checks, progress review, and loop/stuck review passed
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed `flowpilot` overwritten from repository source
- OK: `python scripts\audit_local_install_sync.py --json`: repo-owned skill freshness audit passed
- OK: `python scripts\install_flowpilot.py --check --json`: installed `flowpilot` source_fresh true

### Findings
- Active runtime no longer stores or checks `run_mode` or `full_auto`; run modes are present only as a retired legacy-matrix item and as absence assertions in `scripts/check_install.py`.
- Runtime cards and packet/result bodies now carry identity-boundary markers, and packet runtime checks enforce those markers before role-specific reads.
- PM cards and the FlowGuard modeling request template explicitly preserve proactive modeling of reference systems, source objects, migration equivalence, and experiment-derived behavior.
- The legacy matrix should preserve old source section names for traceability even when the new architecture maps them to reduced behavior; the old `Four-Question Startup Gate` now maps to a three-question startup gate with the run-mode question retired.

### Skipped Steps
- UI/Cockpit implementation was excluded by the user.
- No release, remote push, or publication action was taken.
- Production conformance replay adapters for abstract resume and router-loop models remain skipped with explicit reasons.


## flowpilot-startup-boundary-cli-compat - Atomic startup stop boundary and CLI order compatibility

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed another AI got stuck after the three startup answers and also hit a router CLI `--json` ordering mismatch.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/references/protocol.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_activation.md`
- `docs/protocol.md`
- `simulations/prompt_isolation_model.py`
- `simulations/run_prompt_isolation_checks.py`
- `tests/test_flowpilot_router_runtime.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\prompt_isolation_model.py simulations\run_prompt_isolation_checks.py tests\test_flowpilot_router_runtime.py`
- OK by background subagent: `python -m unittest discover -s tests -v`: 69 tests
- OK by background subagent: CLI parse checks for both `--json next` and `next --json`, plus both `--json apply ...` and `apply ... --json`
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`: no missing labels, no safe-graph invariant failures; hazard failures detected as expected
- OK by background subagent: `python simulations\run_startup_pm_review_checks.py`: no missing labels, no safe-graph invariant failures; hazard failures detected as expected
- OK by background subagent: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed `flowpilot` overwritten from repository source
- OK: `python scripts\audit_local_install_sync.py --json`: installed `flowpilot` source_fresh true
- OK: `python scripts\install_flowpilot.py --check --json`: installed dependency check passed

### Findings
- `ask_startup_questions` now atomically records the waiting/stop boundary, so the next turn after user answers can go straight to `record_startup_answers` instead of getting stuck on an internal stop action.
- Existing half-started bootstrap states with `write_startup_awaiting_answers_state` or `stop_for_startup_answers` pending are normalized to the answer-recording boundary.
- Router CLI now accepts `--json` both before and after the subcommand, matching how agents naturally retry the documented example.
- The prompt-isolation FlowGuard model now treats a non-atomic startup question stop boundary as a detected hazard.

### Skipped Steps
- No UI/Cockpit work, release, remote push, or publication action was taken.


## flowpilot-resume-role-rehydration - Live six-role recovery before PM resume

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked whether heartbeat/manual resume immediately restores the six background roles and gives them current-run memory before PM continues.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Prevent resume from treating six `crew_memory/*.json` files as proof that six live role agents exist.
- Ensure heartbeat/manual resume asks the host to restore or spawn all six live roles before PM resume decisions.
- Ensure each restored role receives current-run role memory and context; PM additionally receives resume evidence, frontier, packet/prompt ledgers, route memory, and display-plan context.
- Keep Controller relay-only: it can load state, ask for host rehydration, and relay cards, but cannot infer progress or ask PM for a runway before the rehydration report exists.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/SKILL.md`
- `tests/test_flowpilot_router_runtime.py`
- `simulations/flowpilot_resume_model.py`
- `simulations/run_flowpilot_resume_checks.py`
- `simulations/meta_model.py`
- `simulations/run_meta_checks.py`
- `simulations/capability_model.py`
- `simulations/run_capability_checks.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_resume_model.py simulations\run_flowpilot_resume_checks.py simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py tests\test_flowpilot_router_runtime.py`.
- OK: targeted resume router tests for normal resume, ambiguous resume, manifest card presence, and small skill launcher.
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime`: 51 tests.
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`: no missing labels, no invariant failures.
- OK by background subagent: `python simulations\run_startup_pm_review_checks.py`: no missing labels.
- OK by background subagent: `python simulations\run_card_instruction_coverage_checks.py`: no card graph failures.
- OK by background subagent: `python simulations\run_meta_checks.py`: no missing labels or invariant failures after a longer timeout.
- OK by background subagent: `python simulations\run_capability_checks.py`: no missing labels or invariant failures after a longer timeout.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed skill source fresh.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- Runtime now separates `load_resume_state` from `rehydrate_role_agents`; the former loads current-run files, while the latter requires host evidence for all six live roles.
- `pm.crew_rehydration_freshness` is now reachable between Controller resume reentry and PM resume decision.
- PM resume decisions now require `continuation/crew_rehydration_report.json`, all six roles ready, and PM memory/context rehydration unless the startup answer selected single-agent continuity.
- Missing role memory keeps resume ambiguous; replacement roles can be seeded from common current-run context, and PM still cannot continue the packet loop without explicit recovery evidence.
- The resume, meta, and capability models now require host rehydration, current-run memory injection, and a rehydration report before PM runway work.

### Skipped Steps
- No release, remote push, or publication action was taken.
- No unrelated concurrent agent edits were reverted or normalized.


## flowpilot-display-plan-controller-sync - PM-owned visible plan projection

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that a normal Codex plan can appear before FlowPilot roles exist, then remain misleading after Controller takes over.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Clear any ordinary pre-FlowPilot visible plan as soon as Controller owns the run.
- Restore the visible plan from PM-owned FlowPilot route/node state on startup, resume, route draft, route activation, route mutation, and current-node planning.
- Keep the host-visible plan simple: one `display_plan.json` projection, no chat-history inference, no Controller-invented route items, and no extra status taxonomy.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md`
- `simulations/meta_model.py`
- `simulations/capability_model.py`
- `tests/test_flowpilot_router_runtime.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\meta_model.py simulations\capability_model.py`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_display_plan_is_controller_synced_projection_from_pm_plan`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_sequence_creates_prompt_isolated_run`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime tests.test_flowpilot_packet_runtime`: 51 tests.
- OK by background subagent: `python simulations\run_meta_checks.py`: no invariant failures, no stuck states, no nonterminating components.
- OK by background subagent: `python simulations\run_capability_checks.py`: no invariant failures, no stuck states, no nonterminating components.
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`.
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`: conformance replay skipped with documented reason.
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`.
- OK: `python scripts\smoke_autopilot.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\check_install.py`.

### Findings
- Router now emits a `sync_display_plan` action before resume/startup work when the host visible plan is stale or still reflects ordinary Codex planning.
- If PM has not authored a route plan yet, Controller may only project a waiting-for-PM placeholder and records that it has no authority to invent route items.
- PM route draft, route activation, route mutation, PM resume payloads, and node acceptance planning update `display_plan.json`; Controller only syncs that projection.
- Meta and capability models now require `preflow_visible_plan_cleared` before frozen contract, route work, or post-startup work can proceed.

### Skipped Steps
- No release, remote push, or publication action was taken.
- No unrelated concurrent agent edits were reverted or normalized.


## flowpilot-startup-hard-gates - Banner, task intake, and fresh role startup

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed that a FlowPilot run did not visibly show the startup banner, appeared to plan project-specific UI work before PM route formation, and did not start all six background agents up front.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Prevent the router from marking the startup banner emitted unless the host receives display text it must show.
- Prevent PM route planning from using chat context or stale state instead of a router-owned explicit current user request packet.
- Prevent six-role startup from counting empty slots, old agent ids, or later on-demand subagents as fresh current-task live agents.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/packet_runtime.py`
- `skills/flowpilot/assets/runtime_kit/cards/**/*.md`
- `simulations/prompt_isolation_model.py`
- `simulations/card_instruction_coverage_model.py`
- `tests/test_flowpilot_router_runtime.py`
- `tests/test_flowpilot_packet_runtime.py`
- `scripts/check_install.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py scripts\check_install.py simulations\prompt_isolation_model.py simulations\run_prompt_isolation_checks.py simulations\card_instruction_coverage_model.py tests\test_flowpilot_router_runtime.py tests\test_flowpilot_packet_runtime.py`.
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime`: 49 tests.
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`.
- OK by background subagent: `python simulations\run_flowpilot_resume_checks.py`.
- OK by background subagent: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`.
- OK by background subagent: `python simulations\run_meta_checks.py`.
- OK by background subagent: `python simulations\run_capability_checks.py`.
- OK by background subagent: `python simulations\run_startup_pm_review_checks.py`.
- OK by background subagent: `python simulations\run_release_tooling_checks.py`.
- OK: `python simulations\run_card_instruction_coverage_checks.py`.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `git diff --check`.

### Findings
- `emit_startup_banner` now returns display text/path and the skill launcher requires the host to show `display_text`; a path or flag alone is not enough.
- Startup now has a `record_user_request` boot action that requires `provenance: explicit_user_request`; `user_intake` includes that recorded task plus startup answers.
- `background_agents=allow` now requires six fresh current-run role-agent records before `roles_started` is set; `single-agent` records explicit authorized continuity instead.
- Parallel peer-agent changes added file-backed, envelope-only role output rules to runtime cards and packet runtime. Those changes align with the same prompt-isolation risk and were preserved.
- `scripts\smoke_autopilot.py` timed out in a background wrapper run, but every covered child check was rerun separately and passed.

### Skipped Steps
- No UI/Cockpit implementation, remote push, GitHub release, or publication action was taken.


## flowpilot-controller-route-memory - PM prior path context before route decisions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that PM route/node decisions could be made without a reliable current-run history summary of completed nodes, superseded nodes, stale evidence, review blocks, and experiment/model outputs.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Preserve prompt isolation while ensuring PM does not plan future route work blind to prior route history.
- Keep Controller relay-only: Controller may summarize route-memory indexes and source paths, but must not read sealed packet/result bodies or create acceptance evidence.
- Require PM to read current route-memory files and return `prior_path_context_review` before protected decisions such as route draft, resume decision, node acceptance plan, route mutation, parent segment decision, evidence quality package, final ledger, and closure.

### Implementation Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/manifest.json`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_prior_path_context.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_*.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
- `simulations/prompt_isolation_model.py`
- `simulations/flowpilot_router_loop_model.py`
- `simulations/card_instruction_coverage_model.py`
- `tests/test_flowpilot_router_runtime.py`
- `docs/protocol.md`
- `docs/schema.md`
- `skills/flowpilot/references/protocol.md`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0.
- OK: `python -m py_compile skills/flowpilot/assets/flowpilot_router.py simulations/prompt_isolation_model.py simulations/flowpilot_router_loop_model.py simulations/card_instruction_coverage_model.py tests/test_flowpilot_router_runtime.py`.
- OK: `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json`: no invariant failures, no stuck states, no nonterminating components.
- OK: `python simulations/run_prompt_isolation_checks.py`: no missing labels and hazards detected.
- OK: `python simulations/run_card_instruction_coverage_checks.py`: 59 cards checked, no orphan active cards, no router/manifest errors.
- OK by background subagent: `python simulations/run_meta_checks.py`: no invariant failures, stuck states, or unreachable terminal states.
- OK by background subagent: `python simulations/run_capability_checks.py`: no invariant failures, stuck states, or unreachable terminal states.
- OK: `python simulations/run_flowpilot_resume_checks.py`: heartbeat/manual resume graph passed.
- OK: `python simulations/run_startup_pm_review_checks.py`: startup gate graph passed.
- OK: `python simulations/run_release_tooling_checks.py`: release tooling graph passed.
- OK: `python -m unittest tests.test_flowpilot_router_runtime tests.test_flowpilot_packet_runtime tests.test_flowpilot_card_instruction_coverage -v`: 45 tests.
- OK: `python scripts/check_install.py`.
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`: installed `flowpilot` is fresh against repository source.
- OK: `python scripts/audit_local_install_sync.py --json`: installed repo-owned skills are fresh.
- OK: `python scripts/install_flowpilot.py --check --json`.

### Findings
- A freshness-only invariant was too strong for decisions made before later route changes. The models now track per-decision prior-context usage so a later stale transition does not make an already-valid earlier decision appear invalid.
- The new PM prior path card is router-delivered after capability evidence sync and before route skeleton. Protected PM cards also repeat the history requirement so the obligation is not carried only by earlier chat context.
- Runtime writers reject protected PM decisions that omit `prior_path_context_review`, fail to cite both current route-memory files, or try to treat Controller history as evidence.
- Controller route memory writes `.flowpilot/runs/<run-id>/route_memory/route_history_index.json` and `pm_prior_path_context.json` from route/frontier/ledger metadata only.

### Skipped Steps
- No UI/Cockpit implementation, remote push, GitHub release, or publication action was taken.


## flowpilot-retire-product-understanding-orphan - Retire inactive product-understanding runtime card

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked whether the orphan product-understanding phase card was still needed after the clean router/card rebuild.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Remove an inactive runtime card that could mislead future maintainers into thinking there is a delivered PM phase named `pm.product_understanding`.
- Preserve the active replacement path: `pm.material_understanding` followed by `pm.product_architecture`.
- Avoid touching parallel peer work, especially the active `pm.prior_path_context` card and router support.

### Implementation Files
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_understanding.md`
- `scripts/check_install.py`
- `docs/legacy_prompt_to_cards_matrix.json`
- `docs/flowpilot_clean_rebuild_plan.md`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`: schema 1.0.
- OK by background subagent: `python simulations\run_card_instruction_coverage_checks.py`: no failures and no orphan card files after retiring the inactive card.
- OK by background subagent: `python -m unittest tests.test_flowpilot_card_instruction_coverage -v`: 2 tests.
- OK by background subagent: `python scripts\check_install.py`.
- OK by background subagent: `python simulations\run_meta_checks.py`: zero invariant failures, zero stuck states, zero nonterminating components.
- OK by background subagent: `python simulations\run_capability_checks.py`: zero invariant failures, zero stuck states, zero nonterminating components.
- OK by background subagent: `python scripts\smoke_autopilot.py`: passed, including card instruction coverage, meta checks, capability checks, and install checks.
- OK: `python simulations\run_card_instruction_coverage_checks.py`: `card_count=59`, `active_card_count=55`, `checked_count=59`, `orphan_card_files=[]`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed `flowpilot` overwritten from repository source and `source_fresh=true`.
- OK: `python scripts\audit_local_install_sync.py --json`: installed `flowpilot` and companion repo-owned skill sources fresh.
- OK: `python scripts\install_flowpilot.py --check --json`: dependency check passed.

### Findings
- `pm_product_understanding.md` was not in the manifest or router-delivered active path and duplicated responsibilities now owned by the material-understanding and product-architecture gates.
- The peer-added `pm.prior_path_context` card is active, useful, and intentionally preserved. It explains the current `card_count=59` and `active_card_count=55` after the inactive product-understanding card was removed.
- Historical log lines still mention the former orphan because they describe an earlier validation run; they should remain as audit history rather than be rewritten.

### Skipped Steps
- No UI/Cockpit work, release, remote push, or publication action was taken.


## flowpilot-card-instruction-coverage - Router-return prompt coverage for runtime cards

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that prior route models could miss whether a delivered card actually tells the recipient what to do next.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-05

### Risk Intent
- Prevent valid-looking router state transitions from relying on hidden chat memory or unstated prompt context.
- Ensure every runtime card reminds the recipient of role identity, authorized return shape, and the rule that next FlowPilot action comes from Controller calling `flowpilot_router.py`.
- Preserve prompt isolation by checking the actual runtime-card files, manifest entries, and router-delivered cards rather than only abstract state labels.

### Implementation Files
- `skills/flowpilot/assets/runtime_kit/cards/**/*.md`
- `simulations/card_instruction_coverage_model.py`
- `simulations/run_card_instruction_coverage_checks.py`
- `simulations/card_instruction_coverage_results.json`
- `tests/test_flowpilot_card_instruction_coverage.py`
- `scripts/check_install.py`
- `scripts/smoke_autopilot.py`
- `docs/verification.md`

### Commands
- OK by background subagent: `python -m py_compile simulations\card_instruction_coverage_model.py simulations\run_card_instruction_coverage_checks.py`
- OK by background subagent: `python simulations\run_card_instruction_coverage_checks.py`: `card_count=59`, `active_card_count=54`, `checked_count=59`, no failures; `cards\phases\pm_product_understanding.md` reported as an orphan card file but still checked for identity and router-return wording.
- OK by background subagent: `python simulations\run_prompt_isolation_checks.py`: no missing labels, no invariant failures; hazards detected.
- OK by background subagent: `python -m unittest tests.test_flowpilot_router_runtime -v`: 30 tests.
- OK by background subagent: `python -m unittest tests.test_flowpilot_card_instruction_coverage -v`: 2 tests.
- OK by background subagent: `python scripts\check_install.py`: prompt-manifest card check now includes `next_step_source` and `flowpilot_router.py`.
- OK by background subagent: `python scripts\smoke_autopilot.py`: card instruction coverage, release tooling, startup PM review, meta, and capability checks passed.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`: installed `flowpilot` overwritten from repository source.

### Findings
- The new coverage model reads real card text, manifest entries, and router constants. It rejects missing identity boundaries, wrong recipient roles, missing `required_return`, missing `next_step_source`, missing router-return wording, missing role-appropriate action guidance, and active router cards absent from the manifest.
- Runtime cards now carry a machine-checkable `next_step_source` instruction telling roles not to infer the next FlowPilot action from the card, chat history, or prior prompts.
- `pm_product_understanding.md` remains present as an orphan runtime card file outside the manifest/router active path. It is not delivered by the router, but it is still checked for the same identity and router-return instruction. A later cleanup can either retire it from the runtime kit or formally classify it in the manifest.

### Skipped Steps
- No UI/Cockpit work, release, remote push, or publication action was taken.


## flowpilot-mail-only-controller-file-backed-role-events-20260505 - Require FlowPilot role reports and PM decisions to be file-backed envelopes; make Controller direct text non-authoritative.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that Controller could infer or directly prompt reviewer/PM outside mail-only, file-backed protocol.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-05T15:15:20+00:00
- Ended: 2026-05-05T15:15:20+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python simulations\\run_startup_pm_review_checks.py; python simulations\\run_prompt_isolation_checks.py; python simulations\\run_flowpilot_router_loop_checks.py --json-out simulations\\flowpilot_router_loop_results.json; python skills\\flowpilot\\assets\\run_packet_control_plane_checks.py; python -m pytest tests\\test_flowpilot_router_runtime.py tests\\test_flowpilot_packet_runtime.py; python scripts\\install_flowpilot.py --sync-repo-owned --json; python scripts\\audit_local_install_sync.py --json`

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


## flowpilot-startup-banner-role-launch-audit-20260506 - Audit why a FlowPilot startup transcript appeared not to launch the startup banner or role-start gate after three answers.

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to diagnose a FlowPilot startup transcript involving the prompt-isolated startup banner and six background role startup.
- Status: completed
- Skill decision: use_flowguard_read_only_audit
- Started: 2026-05-06T06:30:26+00:00
- Ended: 2026-05-06T06:30:26+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/prompt_isolation_model.py
- simulations/flowpilot_router_loop_model.py

### Commands
- OK (0.000s): `flowguard import preflight => schema 1.0`
- OK (0.000s): `scripts/audit_local_install_sync.py --json => ok true, installed flowpilot source fresh`
- OK (0.000s): `scripts/check_install.py => ok true`
- OK (0.000s): `pytest tests/test_flowpilot_router_runtime.py -k startup_or_background_agents => 10 passed`
- OK (0.000s): `simulations/run_prompt_isolation_checks.py => ok true`
- OK (0.000s): `simulations/run_flowpilot_router_loop_checks.py => ok true`

### Findings
- Current run bootstrap records banner_emitted=true and roles_started=true; crew_ledger has six live_agent_started role slots for run-20260506-062138.
- The startup banner is display-only; actual live role startup is the later start_role_slots envelope requiring host-spawned agent IDs.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- No production behavior edit was made during this read-only audit.

### Next Actions
- none recorded


## flowpilot-proof-router-20260506 - Implement proof-carrying FlowPilot router checks

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing router/reviewer gate change must prevent self-attested AI claims from bypassing review
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-06T07:59:16+00:00
- Ended: 2026-05-06T07:59:16+00:00
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


## flowpilot-proof-router-20260506 - Implement proof-carrying FlowPilot router checks

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing router/reviewer gate change must prevent self-attested AI claims from bypassing review
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-06T08:29:10+00:00
- Ended: 2026-05-06T08:29:10+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/proof_carrying_checks_model.py
- simulations/run_proof_carrying_checks.py

### Commands
- OK (0.000s): `python -c import flowguard; print(flowguard.SCHEMA_VERSION) => 1.0`
- OK (0.000s): `python simulations/run_proof_carrying_checks.py => ok true`
- OK (0.000s): `python -m py_compile skills/flowpilot/assets/flowpilot_router.py skills/flowpilot/assets/packet_runtime.py simulations/proof_carrying_checks_model.py simulations/run_proof_carrying_checks.py => ok`
- OK (0.000s): `python -m unittest tests.test_flowpilot_router_runtime => 54 passed`
- OK (0.000s): `python -m unittest discover -s tests => 111 passed`
- OK (0.000s): `python simulations/run_meta_checks.py => ok true`
- OK (0.000s): `python simulations/run_capability_checks.py => ok true`
- OK (0.000s): `python simulations/run_prompt_isolation_checks.py => ok true`
- OK (0.000s): `python simulations/run_startup_pm_review_checks.py => ok true`
- OK (0.000s): `python simulations/run_flowpilot_router_loop_checks.py => ok true`
- OK (0.000s): `python simulations/run_router_next_recipient_checks.py => ok true`
- OK (0.000s): `python simulations/run_barrier_equivalence_checks.py => ok true`
- OK (0.000s): `python simulations/run_card_instruction_coverage_checks.py => ok true`
- OK (0.000s): `python simulations/run_defect_governance_checks.py => ok true`
- OK (0.000s): `python simulations/run_user_flow_diagram_checks.py => ok true`
- OK (0.000s): `python scripts/check_install.py => ok true`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json => ok true source_fresh true`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json => ok true source_fresh true`
- OK (0.000s): `python scripts/install_flowpilot.py --check --json => ok true source_fresh true`

### Findings
- Router-owned gates now require proof-carrying audit sidecars and reject self-attested AI claims as proof.
- Startup mechanical checks are router-computed, while user-authenticity/live-agent/heartbeat/Cockpit external facts remain reviewer-required unless host-bound proof exists.
- Packet runtime audits are persisted with mechanical-only router proofs; reviewer still owns result quality and acceptance judgement.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Production conformance replay beyond router runtime tests was not added because the changed proof boundary is covered by runtime tests and existing model regressions.

### Next Actions
- Keep future reviewer-to-router migrations limited to recomputable or host-bound evidence with mechanical_only proof scope.


## flowpilot-startup-display-heartbeat-20260506 - Require visible startup display and host-bound heartbeat

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Startup router changes affect user-visible display gates and scheduled-continuation state.
- Status: completed
- Skill decision: used_flowguard

### Model Files
- simulations/startup_pm_review_model.py
- simulations/flowpilot_router_loop_model.py
- simulations/meta_model.py
- simulations/capability_model.py
- simulations/prompt_isolation_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)" => 1.0`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`
- OK: `python simulations\run_startup_pm_review_checks.py`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py`

### Findings
- Startup banner display now has a visible fenced ASCII banner instead of a plain title line.
- Scheduled continuation now has an explicit `create_heartbeat_automation` router action before startup fact review; applying it requires a real host automation id and current-run host receipt.
- Startup waiting text is recorded as `startup_waiting_state`, so the PM-route placeholder no longer masquerades as a route map.

### Skipped Steps
- No new Cockpit UI implementation was added; Cockpit absence remains a reviewer-checked chat fallback until the product UI exists.

### Next Actions
- Keep host automation creation as a router action with receipt-backed apply payloads instead of treating local continuation files as live heartbeat proof.


## flowpilot-startup-control-contracts-20260506 - Startup answer receipts, sealed repair routing, and cancel flow

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Router startup/control-plane changes affect user-answer interpretation, payload contracts, reviewer blocker routing, sealed repair handoff, and lifecycle stop behavior.
- Status: completed
- Skill decision: used_flowguard

### Risk Intent Brief
- Prevent Controller from guessing missing router payload fields or repairing sealed role-owned content.
- Preserve AI natural-language interpretation while making the interpretation reviewable against the user's original reply.
- Allow startup reviewer blockers to become PM-routed facts rather than router protocol failures.
- Ensure user-requested stop/cancel leaves the run in an explicit stopped state instead of a live controller wait state.
- Keep heartbeat/banner edits from concurrent work intact and avoid treating local files or self-attestation as host proof.

### Planned Checks
- Add or update FlowGuard startup-control checks before production router changes.
- Run targeted router unit tests and existing FlowPilot simulation runners after implementation.

### Model Files
- simulations/flowpilot_startup_control_model.py
- simulations/run_flowpilot_startup_control_checks.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)" => 1.0`
- OK: `python -B simulations\run_flowpilot_startup_control_checks.py`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py`

### Findings
- Startup answers now support AI interpretation only with a raw-reply receipt and reviewer alignment check.
- Router actions now expose payload contracts for startup answers, role slots, heartbeat binding, and display receipts.
- Reviewer `passed: false` startup fact reports are legal block reports and do not become control-plane failures.
- Router repair details are sealed into target-role repair packets; Controller receives only blocker id and packet path/hash.
- User stop/cancel events now put the run into a terminal lifecycle state and prevent further route work.

### Skipped Steps
- Production conformance replay adapter for the new abstract startup-control model was not added; runtime tests and existing meta/capability simulations covered executable paths.


## flowpilot-main-branch-consolidation-20260506 - Local branch consolidation protocol preservation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Consolidating local branches onto `main` exposed one stale branch with unique protocol-governance content.
- Status: completed
- Skill decision: used_flowguard_lightly

### Risk Intent Brief
- Preserve useful local branch changes without replaying stale branch files over newer router, template, and simulation work.
- Avoid deleting a local branch before its unique current-node authorization and PM review/modeling package rules were represented on `main`.
- Keep installed FlowPilot skill content synchronized with the repository after protocol-reference edits.

### Model Files
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)" => 1.0`
- OK: `python simulations\run_meta_checks.py` completed with `graph.ok: true`, zero invariant failures, and zero missing labels in `simulations/results.json`.
- OK: `python simulations\run_capability_checks.py` completed with `graph.ok: true`, zero invariant failures, and zero missing labels in `simulations/capability_results.json`.

### Findings
- `codex/pm-review-modeling-packages` was too stale to merge wholesale, but its still-useful protocol concepts were missing from the current protocol text.
- `docs/protocol.md` and `skills/flowpilot/references/protocol.md` now carry explicit current-node authorization rules and PM-scoped review/modeling package rules.

### Skipped Steps
- No new FlowGuard model was created because the production router state machine was not changed; existing meta and capability simulations were rerun against the preserved protocol boundary.


## flowpilot-startup-banner-restore-20260506 - Restore large ASCII startup banner

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Startup banner display text is user-visible FlowPilot runtime data.
- Status: completed
- Skill decision: skip_with_reason

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)" => 1.0`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_banner_action_and_result_are_user_visible`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The change only replaces the runtime startup banner text with the preserved large FlowPilot ASCII banner.
- The router display-confirmation path, startup ordering, and heartbeat/control state machines were not changed.

### Skipped Steps
- No new FlowGuard model was created because no state transition, frontier, heartbeat, packet, or approval flow changed.


## flowpilot-output-contract-registry - Add FlowPilot output contract registry and prompt propagation so PM-selected task contracts reach roles and router checks before role output

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing control-plane change affects packet dispatch, report schema, controller envelope boundaries, and repeated repair loops
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-06T12:19:49+00:00
- Ended: 2026-05-06T12:19:49+00:00
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


## flowpilot-output-contract-registry - Add FlowPilot PM output contract registry and packet/result propagation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing protocol change: PM task assignment, packet contracts, result self-checks, reviewer gates, and model regression for prompt contract propagation
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T12:52:44+00:00
- Ended: 2026-05-06T12:52:44+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_output_contract_model.py
- simulations/card_instruction_coverage_model.py

### Commands
- OK (0.000s): `python simulations/run_output_contract_checks.py --json-out simulations/flowpilot_output_contract_results.json`
- OK (0.000s): `python simulations/run_card_instruction_coverage_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_resume_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_router_loop_checks.py`
- OK (0.000s): `python simulations/run_prompt_isolation_checks.py`
- OK (0.000s): `python -m unittest tests.test_flowpilot_output_contracts tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`

### Findings
- Output contract propagation must be represented as registry selection, packet envelope/body repetition, result self-check, reviewer validation, and card delivery ordering.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Conformance replay for the new abstract output-contract model: no production adapter exists for this narrow prompt-contract state model; production coverage is provided by router/runtime tests and card coverage checks.

### Next Actions
- Extend registered contracts when new task families are introduced instead of allowing ad hoc PM report requirements.
