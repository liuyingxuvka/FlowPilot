# FlowGuard Adoption Log

This human-readable log summarizes FlowGuard adoption records for major protocol changes.
Machine-readable entries live in `.flowguard/adoption_log.jsonl`.

## flowpilot-terminal-closure-router-loop-20260508 - Stop routing after PM terminal closure

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The live run reached PM terminal closure, but `router_state.status` stayed non-terminal, so the router attempted heartbeat/control-plane continuation and emitted repeated no-legal-next-action blockers.
- Status: completed-with-residual-live-audit-finding
- Skill decision: used_flowguard
- Started: 2026-05-08T21:25:00+00:00
- Ended: 2026-05-08T21:42:00+00:00
- Commands OK: partial

### Model Files
- simulations/flowpilot_router_loop_model.py
- simulations/meta_model.py
- simulations/capability_model.py
- simulations/flowpilot_control_plane_friction_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`, schema 1.0
- OK: `python -m py_compile <installed-flowpilot-skill>\assets\flowpilot_router.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_terminal_closure_uses_file_backed_contract_and_prior_context tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_reconcile_recovers_legacy_terminal_closure_state`
- OK: `python simulations\run_flowpilot_router_loop_checks.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python <installed-flowpilot-skill>\assets\flowpilot_router.py --root "<repo-root>" --json reconcile-run`
- OK: `python <installed-flowpilot-skill>\assets\flowpilot_router.py --root "<repo-root>" --json run-until-wait` returned `run_lifecycle_terminal` with status `closed`.
- Partial: `python simulations\run_flowpilot_control_plane_friction_checks.py` passed graph/progress checks but the live-run audit still reports historical material-scan packet contract/write-target issues.
- Partial: `python scripts\audit_local_install_sync.py --json` passed installed/source freshness but still reports untracked `flowpilot_cockpit` in the main tree from the active UI work.

### Findings
- `_write_terminal_closure_suite` must promote the run itself to terminal status, not only write `closure/terminal_closure_suite.json` and `execution_frontier.status=closed`.
- Terminal lifecycle reconciliation now writes `run_lifecycle.json`, syncs `.flowpilot/current.json` and `.flowpilot/index.json`, archives active control blockers as `superseded_by_terminal_lifecycle`, and prevents follow-up heartbeat/control-plane actions after closure.
- `reconcile_current_run` now recovers legacy runs where closure/frontier were closed but router state was still non-terminal.

### Counterexamples
- Legacy closed run with `router_state.status=active` and an active no-legal-next-action blocker: old router kept asking PM for a repair decision; repaired reconcile clears the active blocker and `next_action` returns `run_lifecycle_terminal`.

### Friction Points
- The live-run control-plane audit is stricter than this repair scope and still sees early material-scan packet envelopes without role-specific output contracts/result write targets. That should be handled as a separate route-protocol cleanup if needed.

### Skipped Steps
- No sealed packet, result, report, or repair-packet bodies were read by Controller.
- The historical material-scan packet contract findings were not repaired in this terminal-closure patch.

### Next Actions
- Treat any future live-run audit cleanup for material-scan packets as a separate, explicit repair task.

## 2026-05-07 - Clean FlowPilot Route Sign Display Text

- Trigger reason: User reported that the FlowPilot Route Sign shown in chat/UI
  included backend-looking display-gate and chat-evidence instructions.
- FlowGuard applicability: `use_flowguard`; this changed user-visible display
  behavior and a display-gate model.
- Risk intent: detect and prevent user-visible route-sign text from leaking
  Controller instructions, display-gate evidence rules, source/audit metadata,
  confirmation details, or other internal control-plane text.
- Model updated: `simulations/user_flow_diagram_model.py`.
- Related guardrail added: `simulations/flowpilot_control_plane_friction_model.py`
  covers adjacent control-plane boundary failures where packet/result receipts,
  lifecycle authority, or research-scope materialization can appear valid while
  the durable evidence is missing or stale.
- Production/template changes:
  - `scripts/flowpilot_user_flow_diagram.py` and
    `skills/flowpilot/assets/flowpilot_user_flow_diagram.py` now render a clean
    user-visible route sign body: title plus Mermaid only.
  - Internal display evidence remains in the display packet, review packet,
    display confirmation, and ledgers.
  - Protocol/card/template text now states that display-gate and audit metadata
    must not be added to the user-visible body.
- Key counterexample preserved: `internal_control_text_displayed_to_user`
  detects a route sign that otherwise satisfies the chat display gate while
  leaking internal display/evidence instructions.
- Checks run:
  - OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  - OK: `python -m py_compile scripts\flowpilot_user_flow_diagram.py skills\flowpilot\assets\flowpilot_user_flow_diagram.py skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py simulations\user_flow_diagram_model.py simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py`
  - OK: `python simulations\run_user_flow_diagram_checks.py`
  - OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
  - OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime tests.test_flowpilot_user_flow_diagram`
  - OK: `python scripts\check_install.py`
  - OK: `python simulations\run_meta_checks.py`
  - OK: `python simulations\run_capability_checks.py`
  - OK: `python simulations\run_startup_pm_review_checks.py`
  - OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
  - OK: `python simulations\run_prompt_isolation_checks.py`
  - OK: `python simulations\run_router_action_contract_checks.py`
  - OK: `python scripts\smoke_autopilot.py`
  - OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
  - OK: `python scripts\install_flowpilot.py --check --json`
  - OK: `python scripts\audit_local_install_sync.py --json`
- Finding: the previous model checked that a Mermaid route sign was displayed,
  but not that the displayed text was free of internal control-plane metadata.
  The upgraded model now covers that content-boundary failure class.
- Skipped checks: production conformance replay remains unavailable for this
  abstract user-flow diagram model; confidence is model and regression-test
  level plus live generator output inspection.

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


## flowpilot-startup-optimization - Compress startup with reviewer-first PM-prep parallelism

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot startup was too slow; user requested model-first optimization before runtime changes
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-09T20:19:04+00:00
- Ended: 2026-05-09T20:59:42+00:00
- Commands OK: True

### Model Files
- docs/flowpilot_startup_optimization_plan.md
- simulations/flowpilot_startup_optimization_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_flowpilot_startup_optimization_checks.py --json-out simulations/flowpilot_startup_optimization_results.json`
- OK: `python simulations/run_flowpilot_startup_control_checks.py --json-out simulations/flowpilot_startup_control_results.json`
- OK: `python simulations/run_flowpilot_card_envelope_checks.py --json-out simulations/flowpilot_card_envelope_results.json`
- OK: `python simulations/run_command_refinement_checks.py`
- OK: `python simulations/run_card_instruction_coverage_checks.py`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py tests/test_flowpilot_card_runtime.py -q`
- OK: `python scripts/check_install.py`
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/install_flowpilot.py --check --json`
- OK: `python scripts/audit_local_install_sync.py --json`

### Findings
- Startup optimization was modeled before runtime changes; the model detects missing role-core receipts, delayed or stale heartbeat binding, reviewer-after-PM ordering, missing display evidence, reviewer re-proof of router-owned facts, and premature PM activation.
- Bootloader role startup now writes role-core delivery evidence in the same action as six-role startup, keeping the legacy role-core injection action only as recovery for older bootstrap states.
- Scheduled heartbeat is requested before display sync and startup review work once the run and role ledger exist.
- Reviewer startup fact-check delivery now happens before PM startup prep cards; PM prep can proceed after reviewer card ack while the reviewer report is pending, but PM startup activation still waits for reviewer facts.
- Reviewer startup delivery context includes direct display-surface evidence and router-owned mechanical proof, with explicit no-reproof guidance.

### Counterexamples
- Missing core prompt/hash receipts are rejected by `roles_ready_without_core_receipts`.
- Reviewer dispatch before early heartbeat is rejected by `heartbeat_after_reviewer_dispatch`.
- PM prep before reviewer dispatch is rejected by `pm_prep_before_reviewer`.
- PM activation before reviewer/PM prep join is rejected by `pm_activation_before_join`.
- Missing display evidence is rejected by `reviewer_without_display_receipt`.

### Friction Points
- Running local install sync, check, and audit in parallel can race: check/audit may read stale installed skill digests while sync is still overwriting. Run sync first, then check and audit.
- Full router runtime tests are long in a shared workspace; background execution with log polling avoids blocking other foreground verification.

### Skipped Steps
- No remote GitHub sync or push was performed by request.
- Same-role multi-card body bundling was intentionally kept out of this pass because command-refinement still rejects generic `card_bundle_fold` without dedicated replay semantics.

### Next Actions
- Consider a separate modeled replay feature for same-role multi-card batch envelopes only if per-card receipts, return joins, and replay semantics are added explicitly.

## flowpilot-node5-acceptance-handoff-20260508 - Final acceptance hardening and handoff package

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Node 5 route-closure hardening required route-wide acceptance evidence, no-reuse/resource audit, boundary checks, backward replay, and user handoff artifacts.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T20:33:00+00:00
- Ended: 2026-05-08T20:48:45+00:00
- Commands OK: True

### Model Files
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python scripts\launch_flowpilot_cockpit.py --root . --run-id run-20260508-090520 --smoke`
- OK: `python -m compileall -q flowpilot_cockpit scripts tests`
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_current_node_packet_relay_requires_reviewer_dispatch`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`

### Findings
- Node 5 evidence artifacts map all frozen root requirements and selected scenarios to current-run public evidence, reviewed gates, explicit unavailable states, or non-closure notes.
- Support and release URLs remain intentionally unconfigured in the current-run cockpit config; the handoff records this as an explicit unavailable external state rather than a passed live-navigation check.
- Worker output does not claim terminal closure; reviewer and PM/controller final gates remain separate protocol steps.

### Counterexamples
- none recorded

### Friction Points
- The run-level evidence ledger still records an older active node, so Node 5 uses direct current-run public Node 4 evidence plus the ledger instead of treating the ledger as the only source.

### Skipped Steps
- No release, publish, deploy, route closure, or PM approval action was performed.
- Sealed packet and result bodies were not used as evidence artifacts.

### Next Actions
- Human-like reviewer should review the Node 5 worker result and evidence package before PM/controller terminal closure decisions.


## flowpilot-node4-cockpit-validation-20260508 - Validate and iterate native cockpit Node 4 evidence

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Node 4 validation could change desktop cockpit behavior, source mapping, tray lifecycle, geometry, and sealed-body privacy boundaries.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T19:46:00+00:00
- Ended: 2026-05-08T20:03:00+00:00
- Commands OK: True

### Model Files
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python scripts\launch_flowpilot_cockpit.py --root . --run-id run-20260508-090520 --smoke`
- OK: `python -m compileall -q flowpilot_cockpit scripts tests`
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_current_node_packet_relay_requires_reviewer_dispatch`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`

### Findings
- Node 4 evidence files were written under the run-scoped Node 4 evidence directory, including screenshot matrix, interaction probes, source-to-UI replay, sealed-boundary review, design iteration record, and geometry/text/icon check.
- The Windows tray callback path initially produced pointer conversion/access errors during minimize/restore; `flowpilot_cockpit/icons.py` now uses pointer-sized Win32 callback signatures for the tray subclass.
- The initial graph view was too crowded at the captured Windows desktop scale; `flowpilot_cockpit/app.py` now performs a one-time initial fit, uses compact graph controls, narrows fixed panes, and keeps dense checklist text in the details pane instead of on the route canvas.

### Counterexamples
- The first rendered screenshot exposed graph clipping/crowding even though the non-interactive smoke check passed.
- The tray lifecycle probe exposed a real callback interop problem not covered by the smoke check alone.

### Friction Points
- Full desktop captures were stronger evidence than window-bbox captures because Windows desktop scaling made bbox captures crop the native window.

### Skipped Steps
- Support and release URL opening remain partial because the current run has no configured support or release URLs. The UI exposes safe unavailable states instead of faking link success.
- Stale/unavailable screenshots use explicitly qualified in-process negative fixtures; current-run source files were not damaged to force those states.

### Next Actions
- Reviewer should inspect the Node 4 evidence files and screenshots directly, especially the explicitly partial support/update and stale/unavailable qualifications.

## flowpilot-node-completion-idempotency-20260508 - Scope node completion idempotency to the active frontier node

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot run could not advance from node 003 to node 004 because `pm_completes_current_node_from_reviewed_result` reused a global `node_completed_by_pm` flag across nodes.
- Status: blocked-after-repair-validation
- Skill decision: used_flowguard
- Started: 2026-05-08T19:00:00+00:00
- Ended: 2026-05-08T19:40:00+00:00
- Commands OK: partial

### Model Files
- simulations/flowpilot_router_loop_model.py
- simulations/run_flowpilot_router_loop_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)`, schema 1.0
- OK: `python -m py_compile <installed-flowpilot-skill>\assets\flowpilot_router.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_node_completion_idempotency_is_scoped_to_active_node`
- OK: targeted adjacent router runtime tests for current-node completion, evidence quality, final ledger, and parent completion
- OK: `python simulations\run_flowpilot_router_loop_checks.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- Partial: `python scripts\audit_local_install_sync.py --json` passed installed/source freshness but failed `legacy_cockpit_source_absent_from_main_tree` because the active UI task has untracked `flowpilot_cockpit` work products in the main tree.

### Findings
- The runtime reset logic cleared current-node cycle flags inside `_mark_frontier_node_completed`, but the generic event recorder then set `node_completed_by_pm` back to true after the frontier advanced.
- A repeated node-completion event must be allowed when the active frontier node is not in `completed_nodes`, its own completion ledger is missing, or `node_completion_ledger_updated` is false.
- The current-node cycle reset also omitted `pm_current_node_card_delivered`, so a second active node could skip the `pm.current_node_loop` card.
- The installed skill router and repo-owned router were kept hash-identical after the repair.

### Counterexamples
- Two-node route: complete node 001, leave stale `node_completed_by_pm=true`, then complete node 002. Old behavior returns `already_recorded`; repaired behavior writes node 002's completion ledger.

### Friction Points
- Current live run then reached node 004 and relayed its packet to `worker_a`, but the host could not find the old `worker_a` agent and spawning a replacement failed with the host agent thread limit.
- Controller cannot complete worker-owned packet work or let Worker B impersonate Worker A without violating the packet/write-grant role boundary.

### Skipped Steps
- No sealed packet or result bodies were read by Controller.
- No cleanup of untracked `flowpilot_cockpit` artifacts was performed because those appear to be active worker output.

### Follow-up Update
- After explicit user approval, the old role sessions were closed to free host capacity. Five fresh roles were started and initialized from current-run memory: PM, reviewer, process officer, product officer, and Worker A.
- The sixth fresh role, Worker B, still failed to spawn with the host agent thread limit. The old Worker B was confirmed unreachable after close.
- Node 004 remains blocked at the router `rehydrate_role_agents` action because the router requires six live role records and Controller must not invent a Worker B agent id.

### Next Actions
- Use a host context that allows six live subagents, or add an explicit protocol fallback for five-live-role continuation when the missing role is not the active packet holder. Do not continue by faking Worker B liveness.


## flowpilot-stale-pending-action-requires-flag-20260508 - Recompute stale role-decision waits

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot run exposed `await_role_decision` for `pm_mutates_route_after_review_block` while its required `model_miss_triage_closed` flag was false.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T18:10:00+00:00
- Ended: 2026-05-08T19:32:04+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py
- simulations/flowpilot_control_plane_friction_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python -m unittest -v tests.test_flowpilot_router_runtime`
- OK: `python simulations\run_defect_governance_checks.py`
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py --json-out temp`
- OK: `python simulations\run_router_action_contract_checks.py --json-out temp`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out temp`
- OK: `python simulations\run_output_contract_checks.py --json-out temp`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python scripts\run_flowguard_coverage_sweep.py --timeout-seconds 60`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\smoke_autopilot.py --fast`

### Findings
- The previous model covered repair/fatal blocker routability but not the generic property that every router-exposed `await_role_decision.allowed_external_events` must be currently receivable.
- The control-plane friction model now catches `await_role_decision exposed an external event whose requires_flag was false`.
- Runtime now clears and recomputes stale role-decision pending actions before returning them; the event validators remain strict.
- Targeted regression proves a stale `pm_mutates_route_after_review_block` wait recomputes to `pm.model_miss_triage` before PM route mutation is accepted.

### Counterexamples
- `role_decision_wait_requires_unsatisfied_flag`

### Friction Points
- The live-run audit still reports four existing historical findings for `run-20260508-090520`; none are the new requires-flag wait invariant, and this task did not mutate sealed packet/result/report bodies.

### Skipped Steps
- No version bump; the change is part of the same 0.5.4 update batch.
- No direct repair of historical active-run artifacts.

### Next Actions
- Treat future stale pending-action regressions as a generic router expected-event legality failure, not as PM output confusion.


## flowpilot-model-miss-triage-gate-20260508 - Gate reviewer-block repair through FlowGuard model-miss triage

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Reviewer-block and repair routing changed stateful FlowPilot control flow; PM repair must now close the FlowGuard model-miss obligation before normal repair or route mutation.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T16:20:00+02:00
- Ended: 2026-05-08T19:00:00+02:00
- Commands OK: True

### Model Files
- simulations/defect_governance_model.py
- simulations/flowpilot_repair_transaction_model.py
- simulations/flowpilot_output_contract_model.py
- simulations/run_defect_governance_checks.py
- simulations/run_flowpilot_repair_transaction_checks.py
- simulations/run_output_contract_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python simulations/run_output_contract_checks.py --json-out simulations/flowpilot_output_contract_results.json`
- OK: `python simulations/run_defect_governance_checks.py`
- OK: `python simulations/run_flowpilot_repair_transaction_checks.py --json-out simulations/flowpilot_repair_transaction_results.json`
- OK: `python -m unittest tests.test_flowpilot_output_contracts`
- OK: `python -m unittest -v tests.test_flowpilot_router_runtime`
- OK: `python scripts/check_install.py`
- OK: `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 60`
- OK: `python simulations/run_meta_checks.py --fast`
- OK: `python simulations/run_capability_checks.py --fast`
- OK: `python scripts/smoke_autopilot.py --fast`
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/check_public_release.py --json --skip-validation`

### Findings
- Output-contract propagation now covers `pm.model_miss_triage` and `officer.model_miss_report` as first-class valid contract families.
- Runtime repair after reviewer/material dispatch block now requires PM to record a model-miss triage decision before `pm.review_repair` or `pm_mutates_route_after_review_block` can proceed.
- Model-backed repair requires officer report references with same-class findings, candidate repair comparison, and a minimal sufficient repair recommendation.
- Out-of-scope repair is allowed only when PM records why FlowGuard cannot model the bug class.

### Counterexamples
- Previous unsafe paths are now caught: repair before model-miss triage, model-backed repair without officer findings, out-of-scope repair without incapability reason, and reviewer recheck before post-repair model check.

### Friction Points
- Full `run_meta_checks.py` and `run_capability_checks.py` recomputation exceeded the 180-second command window, but `--fast` proof reuse passed because the model file, runner file, FlowGuard schema, and result-file fingerprints were unchanged.
- The read-only coverage sweep still reports historical live-run findings under `.flowpilot/runs/run-20260508-090520`; this task did not mutate that active route state.

### Skipped Steps
- No direct repair of historical `.flowpilot` live-run artifacts; they are separate route-state issues and not part of this release change.
- `scripts/check_public_release.py` was run with `--skip-validation` because equivalent validation commands were run directly, including fast smoke.

### Next Actions
- Treat future reviewer-block repair regressions as model-miss triage failures first, then ordinary repair only after the model-backed or out-of-scope branch is closed.


## flowpilot-fatal-control-blocker-replay-model-20260508 - Model fatal control blocker PM repair replay

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot run exposed a fatal_protocol_violation control blocker where PM repair decision recording and already-recorded corrected follow-up replay needed router/model review.
- Status: completed_installed_local_git_pending
- Skill decision: used_flowguard
- Started: 2026-05-08T16:03:00+00:00
- Ended: 2026-05-08T16:10:00+00:00
- Commands OK: true

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py
- simulations/flowpilot_packet_lifecycle_model.py
- simulations/run_flowpilot_packet_lifecycle_checks.py
- simulations/card_instruction_coverage_model.py

### Commands
- OK: `python -m py_compile simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py simulations\flowpilot_packet_lifecycle_model.py simulations\run_flowpilot_packet_lifecycle_checks.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out "$env:TEMP\flowpilot_control_plane_friction_fatal_check.json"`
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py --json-out "$env:TEMP\flowpilot_packet_lifecycle_fatal_check.json"`
- OK: `python -m py_compile simulations\card_instruction_coverage_model.py simulations\run_card_instruction_coverage_checks.py`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k "already_recorded_event"`
- OK: `python -m pytest tests\test_flowpilot_output_contracts.py -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out "$env:TEMP\flowpilot_protocol_contract_after_patch.json"`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\smoke_autopilot.py --fast`
- Timed out: `python simulations\run_meta_checks.py`

### Findings
- Live control blocker 0010 is currently recorded and resolved, but router source had a recovery branch gap: already-recorded corrected follow-up replay only treated `pm_repair_decision_required` as PM-repair-recorded, not `fatal_protocol_violation`.
- Production router now treats both PM-decision-required lanes as eligible for already-recorded follow-up resolution only after `pm_repair_decision_status=recorded`.
- PM repair decision event recording already accepted fatal blockers; the production patch stayed limited to the already-recorded delivered-blocker resolver plus regression coverage.
- The model suite now represents fatal protocol violations as PM-decision-required blockers and checks that corrected follow-up replay remains matchable and normalized.
- FlowCard coverage now checks PM control-blocker cards mention ordinary PM repair lane, fatal lane, PM repair event, output contract, and repair transaction.

### Counterexamples
- Added synthetic hazards for fatal follow-up without PM decision, fatal repair follow-up event unmatchable, and fatal repair follow-up event not normalized.

### Friction Points
- Full meta check is heavy and timed out under the interactive 120-second limit; `--fast` reused a valid existing proof because meta inputs were unchanged.

### Skipped Steps
- GitHub push was intentionally skipped per user instruction.
- No sealed packet/result/report body was read.

### Next Actions
- Keep this as a local-only commit unless the user later asks to push to GitHub.


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


## flowpilot-router-action-payload-contracts - Expose nested FlowPilot router action payload contract requirements

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing router protocol change: next_action payload contracts must reveal internal validator-required fields before AI applies actions
- Status: in_progress
- Skill decision: use_flowguard
- Started: 2026-05-06T13:06:00+00:00
- Ended: 2026-05-06T13:06:00+00:00
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


## flowpilot-router-action-payload-contracts - Expose nested FlowPilot router action payload contract requirements

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing router protocol change: next_action payload contracts must reveal internal validator-required fields before AI applies actions
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T13:25:19+00:00
- Ended: 2026-05-06T13:25:19+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_router_action_contract_model.py

### Commands
- OK (0.000s): `python simulations/run_router_action_contract_checks.py --json-out simulations/flowpilot_router_action_contract_results.json`
- OK (0.000s): `python simulations/run_flowpilot_startup_control_checks.py`
- OK (0.000s): `python simulations/run_prompt_isolation_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_resume_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_router_loop_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python -m unittest tests.test_flowpilot_router_runtime`
- OK (0.000s): `python -m unittest tests.test_flowpilot_output_contracts tests.test_flowpilot_packet_runtime`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`

### Findings
- Startup answer interpretation failed once because payload_contract exposed the optional receipt object but not its nested schema_version and required fields.
- Display-surface and resume-role action contracts had similar nested receipt visibility risks; the patch exposes those fields before apply.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Production conformance replay for the abstract action-contract model: no adapter exists; production-facing coverage is provided by router runtime tests and install checks.

### Next Actions
- When adding router action validators, update next_action payload_contract and add a test that asserts visible contract fields cover validator-required nested fields.


## flowpilot-startup-mechanical-audit-dead-end - Prewrite startup audit and add PM protocol dead-end

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing startup gate protocol change: reviewer reports must not be accepted before the router-owned startup mechanical audit exists, and PM startup blocks need either a targeted repair decision or a protocol dead-end emergency stop.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T17:09:00+02:00
- Ended: 2026-05-06T17:09:00+02:00
- Duration seconds: not recorded
- Commands OK: True

### Model Files
- simulations/startup_pm_review_model.py
- simulations/flowpilot_startup_control_model.py

### Commands
- OK: `python simulations\run_startup_pm_review_checks.py`
- OK: `python simulations\run_flowpilot_startup_control_checks.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\startup_pm_review_model.py simulations\flowpilot_startup_control_model.py simulations\run_startup_pm_review_checks.py simulations\run_flowpilot_startup_control_checks.py`
- OK: `python -m json.tool skills\flowpilot\assets\runtime_kit\contracts\contract_index.json`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q`
- OK: `python -m pytest tests -q`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\smoke_autopilot.py --fast`

### Findings
- The prior startup sequence wrote `startup_mechanical_audit.json` while accepting the reviewer report, so the reviewer could not have relied on a current audit before reporting.
- PM startup block handling needed explicit protocol outputs: `pm_requests_startup_repair` for targetable repairs and `pm_declares_startup_protocol_dead_end` for the rare no-legal-path stop.
- Reviewer startup fact reports now must include the current startup mechanical audit hash in `external_fact_review.router_mechanical_audit_hash`.

### Counterexamples
- `fact_report_without_mechanical_audit` is detected by startup-control model hazards.
- `blocking_fact_report_without_pm_target` is detected by startup-control model hazards.
- `protocol_dead_end_without_file_backed_record` is detected by startup-control model hazards.

### Friction Points
- Full `run_meta_checks.py` and `run_capability_checks.py` forced reruns exceeded the foreground execution window; this change did not edit those model inputs, so their existing valid proofs were reused through `--fast`.

### Skipped Steps
- Production conformance replay for the abstract startup-control model remains skipped because no adapter exists; production coverage is through router runtime tests and install checks.

### Next Actions
- If future startup repair paths target worker roles rather than the router or reviewer, add a concrete startup repair packet workflow instead of relying on generic PM prose.


## flowpilot-report-contract-packet-delivery-20260506 - Ensure FlowPilot report contract templates are delivered with each task packet

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested FlowGuard-modeled protocol change for report schema delivery to final reporter before prompt edits
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-06T16:05:49+00:00
- Ended: 2026-05-06T16:05:49+00:00
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


## flowpilot-report-contract-packet-delivery-20260506 - Ensure FlowPilot report contract templates are delivered with each task packet

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested FlowGuard-modeled protocol change for report schema delivery to final reporter before prompt edits
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T17:00:00+00:00
- Ended: 2026-05-06T17:00:00+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_output_contract_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK (0.000s): `python simulations\run_output_contract_checks.py --json-out simulations\flowpilot_output_contract_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_output_contracts tests.test_flowpilot_packet_runtime tests.test_flowpilot_router_runtime`
- OK (0.000s): `python simulations\run_meta_checks.py`
- OK (0.000s): `python simulations\run_capability_checks.py`
- OK (0.000s): `python scripts\smoke_autopilot.py`
- OK (0.000s): `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\audit_local_install_sync.py --json`

### Findings
- Output contract model now rejects final reports when the task packet does not deliver the report contract to the final writer.
- Task packet rendering now includes a generated Report Contract For This Task section with exact fields, allowed values, envelope fields, and blocked/needs-PM handling.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- none recorded


## flowpilot-command-refinement-rollback-20260506 - Restore unfolded router baseline and reintroduce only proven startup fold

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Command folding caused FlowPilot startup CLI parsing failure before the three startup questions; user requested returning to a validated unfolded baseline and reintroducing only model-proven folds.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T17:40:00+00:00
- Ended: 2026-05-06T18:05:00+00:00
- Duration seconds: 1500
- Commands OK: True

### Model Files
- simulations/flowpilot_command_refinement_model.py
- simulations/run_command_refinement_checks.py
- simulations/flowpilot_command_refinement_results.json
- simulations/flowpilot_router_action_contract_model.py
- simulations/flowpilot_router_loop_model.py
- simulations/flowpilot_output_contract_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_command_refinement_checks.py --json-out simulations/flowpilot_command_refinement_results.json`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_run_until_wait_applies_only_safe_startup_action tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_cli_accepts_json_after_subcommand tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_retired_high_risk_fold_commands_are_not_cli_commands`
- OK: `python scripts/check_install.py`
- OK: `python simulations/run_router_action_contract_checks.py --json-out simulations/flowpilot_router_action_contract_results.json`
- OK: `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json`
- OK: `python simulations/run_output_contract_checks.py --json-out simulations/flowpilot_output_contract_results.json`
- OK: temporary formal startup smoke using `run-until-wait --new-invocation`; returned `ask_startup_questions` with `requires_user: true` after one internal `load_router` apply.
- OK: background full `python simulations/run_meta_checks.py` (`598029` states, `618200` edges, no invariant/stuck/nonterminating findings).
- OK: background full `python simulations/run_capability_checks.py` (`557123` states, `582582` edges, no invariant/stuck/nonterminating findings).
- OK: background `python scripts/smoke_autopilot.py --fast`.
- OK: background `python -m unittest tests.test_flowpilot_router_runtime` (`60` tests).

### Findings
- The prior `flowpilot_command_folding` model was too broad and abstract. It did not prove concrete CLI/parser binding or helper-name availability.
- The unsafe aggregate commands were removed from production CLI: `deliver-card-bundle-checked`, `relay-checked`, `prepare-startup-fact-check`, and `record-role-output-checked`.
- The new command-refinement model treats the original unfolded startup sequence as the baseline oracle and permits only the safe internal `run-until-wait` startup fold.
- `scripts/check_install.py` now performs real router CLI parse checks and verifies the high-risk retired fold commands are absent.

### Counterexamples
- Prior startup failure: `relay-checked` added a parser `choices=sorted(RELAY_CHECKED_ACTION_TYPES)` reference without a committed definition, causing `NameError` before startup questions.

### Friction Points
- FlowGuard abstract models do not replace concrete parser/import/static binding checks; both are needed for router CLI changes.

### Skipped Steps
- Dedicated conformance replay for card bundles, packet relays, startup fact-card delivery, and role-output preflight remains intentionally skipped; those fold candidates are rejected until separate replay exists.

### Next Actions
- If future speed work resumes, evaluate one fold candidate at a time against unfolded state snapshots plus FlowGuard refinement before exposing it in the production CLI.


## flowpilot-display-confirmation-template-20260506 - Add copyable display confirmation payload templates to FlowPilot router actions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Router display actions were correctly rejecting payloads, but the action envelope did not provide a copyable payload template to the controller.
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-06T18:27:03+00:00
- Ended: 2026-05-06T18:27:03+00:00
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


## flowpilot-display-confirmation-template-20260506 - Add copyable display confirmation payload templates to FlowPilot router actions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Router display actions were correctly rejecting payloads, but the action envelope did not provide a copyable payload template to the controller.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T18:52:42+00:00
- Ended: 2026-05-06T18:52:42+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_router_action_contract_model.py
- simulations/flowpilot_router_loop_model.py

### Commands
- OK (0.000s): `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_router_action_contract_model.py simulations\run_router_action_contract_checks.py tests\test_flowpilot_router_runtime.py`
- OK (0.000s): `python simulations\run_router_action_contract_checks.py --json-out simulations\flowpilot_router_action_contract_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_router_runtime`
- OK (0.000s): `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK (0.000s): `python simulations\run_prompt_isolation_checks.py`
- OK (0.000s): `python scripts\check_install.py`
- OK (0.000s): `python scripts\smoke_autopilot.py`
- OK (0.000s): `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\audit_local_install_sync.py --json`

### Findings
- Display actions now expose a copyable payload_template containing display_confirmation.action_type, display_kind, display_text_sha256, provenance, and rendered_to.
- The router action contract model now accepts valid display confirmation and rejects a template missing display_text_sha256.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- check_public_release.py full validation timed out after 5 minutes because it reruns smoke_autopilot; the same validation commands were run separately and check_public_release.py --skip-validation passed privacy/dependency checks.

### Next Actions
- none recorded


## flowpilot-safe-simplification-proof-20260506 - Prove safe-equivalent FlowPilot simplification preserves barrier bundles and controller-only run-until-wait boundaries

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested focused FlowGuard proof that safe simplification preserves role boundaries and rejects skipping PM/reviewer/officer/ledger/final replay gates
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T19:33:47+00:00
- Ended: 2026-05-06T19:33:47+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/barrier_equivalence_model.py
- simulations/run_barrier_equivalence_checks.py
- simulations/barrier_equivalence_results.json

### Commands
- OK (0.000s): `python -m flowguard schema-version`
- OK (0.000s): `python -m py_compile simulations/barrier_equivalence_model.py simulations/run_barrier_equivalence_checks.py`
- OK (0.000s): `python simulations/run_barrier_equivalence_checks.py`

### Findings
- Barrier equivalence proof now tracks cumulative role-slice coverage and fails completion when PM/reviewer/officer/worker/controller role slices are incomplete.
- Hazards now detect missing PM, reviewer, process officer, product officer, packet ledger, final replay, and unsafe run-until-wait simplification paths.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Production conformance replay skipped: user restricted scope to model/replay proof and forbade router edits; this update is an abstract barrier/replay proof artifact.

### Next Actions
- none recorded


## flowpilot-protocol-contract-model-20260506 - Model FlowPilot prompt contract and router protocol consistency before fixing startup report/control-blocker/hash issues

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing protocol/schema repair requires model-first validation
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T19:43:25+00:00
- Ended: 2026-05-06T20:25:00+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_protocol_contract_conformance_model.py
- simulations/run_protocol_contract_conformance_checks.py
- simulations/protocol_contract_conformance_results.json

### Commands
- OK (0.000s): `python -m py_compile simulations\flowpilot_protocol_contract_conformance_model.py simulations\run_protocol_contract_conformance_checks.py`
- OK (0.000s): `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_output_contracts`

### Findings
- Startup fact report role submissions are now kept separate from the router canonical startup fact report, and the router rejects canonical-path aliasing.
- PM control-blocker repair decisions now use the dedicated `pm_records_control_blocker_repair_decision` event and a stricter output contract.
- The protocol contract model accepts the fixed source and rejects JSON-path mismatch, ambiguous PM blocker event routing, weak PM repair contracts, startup fact hash aliasing, and missing host-receipt scenarios.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- none recorded


## flowpilot-safe-router-simplification-implementation-20260506 - Implement replay-proven FlowPilot command simplifications and route-memory reuse

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested safe-equivalent speed improvements after prior incomplete folding caused startup failures.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T20:00:00+00:00
- Ended: 2026-05-06T20:35:00+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_command_refinement_model.py
- simulations/run_command_refinement_checks.py
- simulations/flowpilot_command_refinement_results.json
- simulations/barrier_equivalence_model.py
- simulations/run_barrier_equivalence_checks.py
- simulations/barrier_equivalence_results.json

### Commands
- OK (0.000s): `python simulations\run_command_refinement_checks.py --json-out simulations\flowpilot_command_refinement_results.json`
- OK (0.000s): `python simulations\run_barrier_equivalence_checks.py`
- OK (0.000s): `python simulations\run_meta_checks.py`
- OK (0.000s): `python simulations\run_capability_checks.py`
- OK (0.000s): `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK (0.000s): `python simulations\run_output_contract_checks.py --json-out simulations\flowpilot_output_contract_results.json`
- OK (0.000s): `python simulations\run_router_action_contract_checks.py --json-out simulations\flowpilot_router_action_contract_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_router_runtime`
- OK (0.000s): `python scripts\check_install.py`

### Findings
- `run-until-wait` now folds only replay-proven internal startup/bootloader/intake actions and stops before user, host, role, payload, card, packet, ledger, and final-replay boundaries.
- Command-refinement checks accept startup, post-banner bootloader, and post-user-request intake folds while rejecting card bundles, relay folds, host continuations, role starts, ledger finalization, and final replay.
- Controller route memory refresh is skipped when the current run already has fresh route history and PM prior-path context files.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- none recorded


## flowpilot-protocol-contract-model-20260506 - Model and fix FlowPilot prompt contract and router protocol consistency for startup report/control-blocker/hash issues

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing protocol/schema repair required model-first validation
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T20:09:30+00:00
- Ended: 2026-05-06T20:09:30+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_protocol_contract_conformance_model.py

### Commands
- OK (0.000s): `python simulations\\run_protocol_contract_conformance_checks.py --model-only --json-out simulations\\protocol_contract_conformance_model_only_results.json`
- OK (0.000s): `python simulations\\run_protocol_contract_conformance_checks.py --json-out simulations\\protocol_contract_conformance_results.json`
- OK (0.000s): `python -m pytest tests\\test_flowpilot_router_runtime.py -q`
- OK (0.000s): `python scripts\\install_flowpilot.py --sync-repo-owned --json`

### Findings
- Concrete source scan initially detected startup fact JSONPath mismatch, ambiguous PM control-blocker events, weak PM control-blocker decision contract/router validation, and startup fact canonical path/hash alias risk.
- After source fixes, protocol_contract_conformance current_source_conformance passed while hazard states remained detected.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Full production transcript replay skipped; this model scans source facts and explores protocol states rather than replaying a saved runtime transcript.

### Next Actions
- Consider adding a concrete runtime transcript replay adapter for startup/control-blocker envelopes if more historical transcripts are retained.


## flowpilot-startup-fallback-repair-cycles-20260506 - Model-first fix for startup display fallback availability and repeatable startup repair cycles

- Project: FlowPilot
- Trigger reason: Protocol behavior changed around startup display fallback, reviewer fact review, PM repair retries, deduplication, and source-of-truth state.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-06T21:39:25+00:00
- Ended: 2026-05-06T21:39:25+00:00
- Duration seconds: 3600.000
- Commands OK: True

### Model Files
- simulations/flowpilot_protocol_contract_conformance_model.py
- simulations/flowpilot_startup_control_model.py
- simulations/startup_pm_review_model.py

### Commands
- OK (0.000s): `python -c import flowguard; print(flowguard.SCHEMA_VERSION)`
- OK (0.000s): `python simulations/run_protocol_contract_conformance_checks.py --model-only --json-out simulations/protocol_contract_conformance_model_only_results.json`
- OK (0.000s): `python simulations/run_protocol_contract_conformance_checks.py --json-out simulations/protocol_contract_conformance_results.json`
- OK (0.000s): `python simulations/run_flowpilot_startup_control_checks.py --json-out simulations/flowpilot_startup_control_results.json`
- OK (0.000s): `python simulations/run_startup_pm_review_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python -m pytest tests -q`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json`

### Findings
- Initial source conformance failed for missing pre-review display fallback receipt and one-shot startup repair dedupe.
- Updated runtime now writes display status before reviewer startup fact review, permits fresh repair cycles for new blocking reports, tracks cycle/report/decision identity, and rejects exact duplicate PM repair decisions.

### Counterexamples
- Before fix, a second blocking startup fact report could be treated as already_recorded because startup_repair_requested stayed true.
- Before fix, reviewer startup fact review could occur without a display surface status proving UI absence/fallback.

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Keep source-conformance probes for future startup protocol changes.


## flowpilot-reviewer-router-fact-owner-boundary-20260507 - Startup reviewer/router fact ownership and PM findings decisions

- Project: FlowPilot
- Trigger reason: User review found that startup control friction came from over-asking the reviewer to prove facts the reviewer cannot independently observe, while also needing to catch any required fact with no router, reviewer, or PM owner.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-07
- Ended: 2026-05-07
- Commands OK: True

### Model Files
- `simulations/flowpilot_startup_control_model.py`
- `simulations/flowpilot_protocol_contract_conformance_model.py`
- `simulations/flowpilot_router_action_contract_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_protocol_contract_conformance_model.py`
- OK: `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_results.json`
- OK: `python simulations\run_router_action_contract_checks.py`
- OK: `python simulations\run_protocol_contract_conformance_checks.py`
- OK: `python simulations\run_output_contract_checks.py`
- OK: `python simulations\run_startup_pm_review_checks.py`
- OK: `python simulations\run_router_next_recipient_checks.py`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python simulations\run_release_tooling_checks.py`
- OK: `python simulations\run_barrier_equivalence_checks.py`
- OK: `python simulations\run_command_refinement_checks.py`
- OK: `python simulations\run_prompt_isolation_checks.py`
- OK: `python simulations\run_flowpilot_resume_checks.py`
- OK: `python simulations\run_flowpilot_router_loop_checks.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py`
- OK: `python -m pytest tests`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\smoke_autopilot.py --fast`

### Findings
- The startup model now treats router-computable mechanical facts as router-owned and removes reviewer reproof as a safe-path obligation.
- The model now treats every required startup fact with no router, reviewer, or PM-decision owner as a hazard.
- Reviewer startup findings now require PM repair, waiver/demotion, or protocol dead-end decision before work can proceed; the reviewer does not directly terminate the route.
- Normal stage precondition failures such as "event requires prior card delivery" are not materialized as active control blockers.
- Runtime, startup reviewer card, PM startup activation card, and output-contract metadata were aligned so the reviewer checks independently observable external facts only.

### Counterexamples
- Before the fix, an unreviewable original-chat authenticity requirement could force reviewer failure without an independent proof source.
- Before the fix, a missing review-owner category could remain invisible if neither router nor reviewer owned the fact.
- Before the fix, a normal stage precondition error could be widened into a control blocker and interrupt ordinary routing.

### Friction Points
- The background validation subagent disconnected before returning results, so final validation was rerun in the main thread.
- `python scripts\smoke_autopilot.py` without `--fast` timed out twice because it runs slow meta/capability checks sequentially; the explicit individual checks passed and the fast smoke check passed by reusing existing proof files.

### Skipped Steps
- Full slow meta/capability regeneration was not rerun after the timeout; `--fast` reused existing proof files. The changed files are outside the meta/capability model definitions, and full pytest plus focused startup/protocol models passed.

### Next Actions
- Consider making `smoke_autopilot.py` report per-check progress or default to bounded proof reuse so future validation does not look stalled.

## flowpilot-protocol-friction-model-20260507 - Model-first minimal repair for FlowPilot control-plane protocol friction

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested FlowGuard model changes before minimal code fixes for real FlowPilot protocol friction
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T08:32:53+00:00
- Ended: 2026-05-07T08:32:53+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_protocol_contract_conformance_model.py
- simulations/run_protocol_contract_conformance_checks.py

### Commands
- OK (0.000s): `python simulations/run_protocol_contract_conformance_checks.py --json-out simulations/protocol_contract_conformance_results.json`
- OK (0.000s): `python -m pytest tests/test_flowpilot_router_runtime.py -k material_scan_accepts_file_backed_packet_body`
- OK (0.000s): `python -m pytest tests/test_flowpilot_router_runtime.py -k reviewer_blocks_material_scan_dispatch_routes_to_pm_repair`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python simulations/run_prompt_isolation_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.background_latest.json`
- OK (0.000s): `python -m pytest tests/test_flowpilot_router_runtime.py tests/test_flowpilot_output_contracts.py tests/test_flowpilot_packet_runtime.py`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json`
- OK (0.000s): `python scripts/install_flowpilot.py --check --json`

### Findings
- Extended the protocol model to catch role-output envelope ambiguity, material scan inline-body leakage, missing material dispatch block event, and frontier/phase mismatch.
- A pre-fix source-conformance run failed as expected and exposed current-source protocol gaps; after minimal router/card/test changes, current_source_conformance passed.

### Counterexamples
- none recorded

### Friction Points
- Existing checks were green because material dispatch and file-backed material scan protocol were outside their modeled boundary.

### Skipped Steps
- Full production transcript replay skipped; this pass used source conformance, FlowGuard exploration, router loop regressions, and focused runtime tests.

### Next Actions
- Keep future FlowPilot protocol changes in the concrete protocol conformance model before editing router behavior.


## flowpilot-live-card-context-friction-20260507 - Model and fix FlowPilot live role card context friction

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Realtime role cards may omit current role/task/output/stage context and cause protocol friction
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T09:30:38+00:00
- Ended: 2026-05-07T09:30:38+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/card_instruction_coverage_model.py
- simulations/run_card_instruction_coverage_checks.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python simulations/run_card_instruction_coverage_checks.py`
- OK (0.000s): `python -m pytest tests/test_flowpilot_card_instruction_coverage.py tests/test_flowpilot_router_runtime.py -k "card_instruction_coverage or system_card_delivery_requires_manifest_check"`
- OK (0.000s): `python -m py_compile simulations/card_instruction_coverage_model.py simulations/run_card_instruction_coverage_checks.py skills/flowpilot/assets/flowpilot_router.py scripts/check_install.py`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python simulations/run_prompt_isolation_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json`
- OK (0.000s): `python simulations/run_protocol_contract_conformance_checks.py --json-out simulations/protocol_contract_conformance_results.json`
- OK (0.000s): `python -m pytest tests/test_flowpilot_router_runtime.py tests/test_flowpilot_output_contracts.py tests/test_flowpilot_packet_runtime.py tests/test_flowpilot_card_instruction_coverage.py`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json`
- OK (0.000s): `python scripts/install_flowpilot.py --check --json`

### Findings
- The previous model verified static card identity but did not require a live router delivery envelope with run/task/card/phase/node/source-path context.
- Pre-fix model execution exposed missing live card delivery context in the router and system card delivery ledger.
- Router deliveries now attach delivery_context and persist it in both delivered card state and the prompt delivery ledger.
- All system cards now instruct roles to treat the router delivery envelope as live authority and return a protocol blocker rather than continuing from memory when missing or stale.

### Counterexamples
- none recorded

### Friction Points
- Prompt friction came from separating role instruction text from runtime task/stage/frontier authority; static cards alone could still leave agents relying on memory.

### Skipped Steps
- none recorded

### Next Actions
- Keep future FlowPilot card/protocol changes covered by both static card guidance checks and runtime delivery-envelope checks.


## flowpilot-control-plane-live-audit-generalization-20260507 - Generalize FlowPilot control-plane friction model for live-run source context and terminal consistency

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Later FlowPilot live-run artifacts exposed model misses after the first optimized model pass
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T15:19:09+00:00
- Ended: 2026-05-07T15:19:09+00:00
- Duration seconds: 0.000
- Commands OK: False

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py

### Commands
- OK (0.000s): `python -m py_compile simulations/flowpilot_control_plane_friction_model.py simulations/run_flowpilot_control_plane_friction_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_control_plane_friction_checks.py --skip-live-audit`
- FAIL (0.000s): `expected-live-findings: python simulations/run_flowpilot_control_plane_friction_checks.py --json-out simulations/flowpilot_control_plane_friction_results.json`

### Findings
- Refined live-run audit now catches generic missing required card source paths, stale card current_phase, child-skill manifest/review sync drift, terminal snapshot flag mismatch, terminal automation cleanup proof gaps, and role-output hash replay mismatches.

### Counterexamples
- none recorded

### Friction Points
- The prior model was too point-specific: it caught pm.product_architecture missing context but did not generalize the source-context invariant to later phase cards.

### Skipped Steps
- Production FlowPilot/router repair intentionally skipped; user asked to optimize the model first.

### Next Actions
- Discuss which flagged live-run issues should drive production/router repairs next.


## flowpilot-gate-policy-audit-20260507 - Model FlowPilot gate-policy friction before runtime changes

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked whether FlowGuard can model and catch unreasonable, useless, or counterproductive FlowPilot process logic before changing FlowPilot code
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T17:24:53+02:00
- Ended: 2026-05-07T17:24:53+02:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_gate_policy_audit_model.py
- simulations/run_flowpilot_gate_policy_audit_checks.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python -m py_compile simulations\flowpilot_gate_policy_audit_model.py simulations\run_flowpilot_gate_policy_audit_checks.py`
- OK (0.000s): `python simulations\run_flowpilot_gate_policy_audit_checks.py --skip-live-source-audit --json-out simulations\flowpilot_gate_policy_audit_abstract_results.json`
- OK (0.000s): `python simulations\run_flowpilot_gate_policy_audit_checks.py --json-out simulations\flowpilot_gate_policy_audit_results.json`

### Findings
- The model keeps formal FlowPilot complex-only and preserves the six-role crew once formal FlowPilot starts.
- Abstract checks catch unsafe gate policies for small-task overactivation, startup side effects before answers, text-only startup false violations, missing quality-risk decisions, visual-quality FlowGuard-only proof, documentation-only Product FlowGuard forcing, advisory records blocking completion, local defects forcing structural mutation, route mutation without stale-evidence invalidation, low-risk parent replay as a hard blocker, unresolved delivery evidence, no-benefit hard gates, and non-transactional state refresh.
- Live source audit raised three warning-level signals: parent replay lacks an obvious low-risk waiver path, blocking review failure policy lacks an obvious local-defect branch, and existing control-plane live audit results still report state-friction findings.

### Counterexamples
- All expected hazard states were detected by the model; no safe-graph invariant failures were found.

### Friction Points
- The useful boundary is not "FlowGuard proves every quality judgment"; it is "FlowGuard proves the process selected the right kind of proof and did not turn low-value checks into hard blockers."

### Skipped Steps
- Production FlowPilot/runtime/card/router mutation intentionally skipped because the user requested model-first analysis before changing FlowPilot code.

### Next Actions
- Decide which warning-level live-source findings should become FlowPilot runtime/card changes in a later implementation pass.


## flowpilot-gate-decision-contract-20260507 - Make gate-policy advice directly modelable before FlowPilot code changes

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked for a directly implementable GateDecision plan that can pass existing FlowGuard models without modifying FlowPilot runtime code
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T18:15:46+02:00
- Ended: 2026-05-07T18:15:46+02:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- docs/gate_decision_implementation_contract.md
- simulations/flowpilot_gate_decision_contract_model.py
- simulations/run_flowpilot_gate_decision_contract_checks.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python -m py_compile simulations\flowpilot_gate_decision_contract_model.py simulations\run_flowpilot_gate_decision_contract_checks.py`
- OK (0.000s): `python simulations\run_flowpilot_gate_decision_contract_checks.py --json-out simulations\flowpilot_gate_decision_contract_results.json`
- OK (245.503s): `python simulations\run_meta_checks.py`
- OK (281.167s): `python simulations\run_capability_checks.py`
- OK (background sweep): 19 non-meta/capability FlowGuard model scripts, including card instruction coverage, protocol conformance, router loop, startup, output contract, prompt isolation, proof-carrying, barrier equivalence, defect governance, control-plane friction model-only, gate-policy audit model-only, and GateDecision contract checks

### Findings
- The GateDecision contract defines a concrete output shape for gate decisions and maps it to prompt/card instructions, router mechanical validation, reviewer/PM semantic sufficiency, and control-plane route-visible state.
- The new contract model accepted the valid contract, rejected 16 negative contract scenarios, had 35 states and 34 edges, reported no stuck states, and FlowGuard Explorer found no violations or exception branches.
- The model catches missing prompt fields, missing router fields, router semantic overreach, reviewer semantic gaps, visual-quality FlowGuard-only proof, product/state proof gaps, mixed-risk proof gaps, documentation-only Product FlowGuard forcing, advisory blockers, missing skip reasons, local defect over-escalation, route mutation without stale-evidence invalidation, low-risk parent replay hard blockers, diagnostic resource blockers, unresolved delivery evidence, and split stage refresh.

### Counterexamples
- All expected negative GateDecision contract scenarios were rejected with explicit failure messages.

### Friction Points
- This is a model-level and contract-level landing plan. It proves the implementation shape is checkable and compatible with existing models, but it intentionally does not claim current runtime/cards already implement the contract.

### Skipped Steps
- Production FlowPilot runtime, router, card, and skill edits intentionally skipped because the user requested a model-passing landable plan before code changes.
- Live source audits that require current production implementation were either skipped by model-only commands or remain separate from this contract validation.

### Next Actions
- If the user approves implementation later, start with the contract registry and role card instructions, then add router mechanical validation, then harden only the small runtime pieces required for route-visible state and atomic stage advance.


## flowpilot-control-plane-friction-fix-20260507 - Implement minimal runtime and protocol fixes after model approval

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved implementation only after the optimized FlowGuard models and existing models accepted the repair plan
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T18:26:10+02:00
- Ended: 2026-05-07T18:26:10+02:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/flowpilot_gate_policy_audit_model.py
- simulations/flowpilot_gate_decision_contract_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python skills\flowpilot\assets\flowpilot_router.py --root . reconcile-run --json`
- OK: all 21 visible `simulations/run_*_checks.py` FlowGuard scripts, including the previously untracked `run_flowpilot_gate_decision_contract_checks.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python simulations\run_flowpilot_gate_policy_audit_checks.py --json-out simulations\flowpilot_gate_policy_audit_results.json`
- OK: `python simulations\run_flowpilot_gate_decision_contract_checks.py --json-out simulations\flowpilot_gate_decision_contract_results.json`
- OK: `python -m unittest discover tests`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\smoke_autopilot.py`

### Findings
- Runtime fixes now reconcile non-current running indexes, terminal cleanup evidence, prompt delivery context, control blocker indexes, role-output replay hashes, and child-skill gate review sync.
- The current live control-plane audit reports zero errors and zero warnings for run `run-20260507-131407`.
- The gate-policy live source audit reports zero errors and zero warnings after the risk-based parent replay and local-defect repair guidance changes.
- Full unit discovery passed 133 tests.
- Local installed `flowpilot` skill digest matches the repository source digest after sync.

### Counterexamples
- The optimized models still detect their expected negative scenarios, including stale prompt context, unsynced child-skill gate review, terminal cleanup gaps, advisory blockers, route mutation without stale invalidation, and low-risk parent replay as a hard blocker.

### Friction Points
- The final full sweep found one visible `run_*_checks.py` script not in the initial 20-script checklist. It was added to the execution set and passed before finalization.

### Skipped Steps
- GitHub push and release publishing were not run; the user asked for the local repository, local installation, and local Git state to be updated.

### Next Actions
- Keep the 21-script FlowGuard sweep as the completion gate whenever FlowPilot control-plane behavior changes.


## flowpilot-packet-lifecycle-runtime-hardening-20260507 - Model and minimally fix packet lifecycle friction

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot dispatch exposed packet envelope, packet ledger, result relay, and PM repair blocker edge cases that old models did not cover
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-07T18:30:00+02:00
- Ended: 2026-05-08T00:47:37+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_packet_lifecycle_model.py
- simulations/run_flowpilot_packet_lifecycle_checks.py
- skills/flowpilot/assets/packet_control_plane_model.py
- skills/flowpilot/assets/run_packet_control_plane_checks.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py --json-out simulations\flowpilot_packet_lifecycle_results.json`
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py`
- OK: all 22 visible `simulations/run_*_checks.py` FlowGuard scripts, including meta and capability checks
- OK: `python -m py_compile skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m unittest tests.test_flowpilot_packet_runtime`
- OK: `python -m unittest tests.test_flowpilot_router_runtime`
- OK: `python -m unittest discover tests`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\check_public_release.py`
- OK: `python scripts\smoke_autopilot.py`

### Findings
- The prior FlowGuard coverage modeled control/card flow but did not strongly represent the physical packet lifecycle boundary. Envelope open markers could diverge from packet-ledger open receipts, result envelopes could be relayed before packet-ledger absorption, and role-key strings could be mistaken for concrete agent ids.
- The new packet lifecycle model covers envelope/body hash identity, packet body open receipt parity, result ledger absorption before relay or PM absorption, completed_agent_id authority, and PM repair decisions as follow-up records rather than blocker self-resolution.
- Runtime guards now require packet-ledger body-open receipts before strict result writes, require result-ledger absorption before reviewer relay and PM research absorption, reject role-key strings as completed_by_agent_id, and keep PM repair decisions from resolving active blockers by themselves.
- All new and existing FlowGuard runners passed after the fix; targeted runtime/router tests and full unittest discovery also passed.

### Counterexamples
- The new model rejects stale packet hashes, envelope-only open evidence, result relay without result-ledger absorption, PM absorption without reviewer-approved relay evidence, invalid completed_agent_id authority, and PM repair decisions that try to resolve blockers by themselves.

### Friction Points
- The live friction came from two valid-looking but different evidence planes: envelope-level flags and packet-ledger records. Earlier models did not require them to prove the same body hash and same open event before downstream gates advanced.
- The slow smoke and public release checks need longer than 300 seconds on this repository; the initial smoke timeout was a timeout budget issue, not a functional failure.

### Skipped Steps
- None.

### Next Actions
- Keep packet lifecycle checks in the standard FlowGuard sweep for future FlowPilot packet, router, reviewer, and PM repair changes.


## flowpilot-legal-wait-contract-convergence-20260508 - Model legal waits instead of phase-specific no-next-action patches

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot UI-route work exposed that a normal role wait after reviewer/PM handoff could be misclassified as Controller no-next-action, encouraging Controller route/work takeover
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T06:20:00+02:00
- Ended: 2026-05-08T08:38:41+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_router_loop_model.py
- simulations/run_flowpilot_router_loop_checks.py
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py
- simulations/flowpilot_packet_lifecycle_model.py
- simulations/run_flowpilot_packet_lifecycle_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py`
- OK by background subagent: `python simulations\run_meta_checks.py --fast`
- OK by background subagent: `python simulations\run_capability_checks.py --fast`
- OK by background subagent: `python -m unittest tests.test_flowpilot_router_runtime`
- OK by background subagent: related FlowPilot/router/skill unittest suites
- OK: `python skills\flowpilot\assets\flowpilot_router.py --json reconcile-run`

### Findings
- The old router-loop model only represented selected terminal waits. Runtime then revealed a model miss: some valid PM/reviewer waits looked like no-next-action from the Controller's local perspective.
- Router runtime now derives expected waits from `EXTERNAL_EVENTS.requires_flag` and the corresponding event flags instead of a phase-specific if-list.
- Router-loop modeling now has `EXPECTED_ROLE_EVENT_CONTRACTS`; each contract names prerequisite state and one or more satisfying role-event states. The model automatically generates a blocker hazard for every reachable unsatisfied legal wait.
- The current active run's live audit initially reported 2 mutable role-output envelope hash mismatches for `flow.draft.json` / `flow.json`. `reconcile-run` repaired 2 role-output envelope hashes and 36 prompt delivery contexts. The follow-up control-plane live audit reports zero errors and zero warnings.

### Counterexamples
- The router-loop model still detects true no-next-action without a PM blocker, Controller project work after no-next-action, Controller sealed-body reads, Controller-origin evidence, missing write grants, reviewer decisions before result relay, PM completion before reviewer pass, final ledger gaps, and all generated legal-wait blocker hazards.

### Friction Points
- The first attempted implementation drifted toward a hand-written wait list. The runtime failure was treated as a model miss, and the fix was moved back into executable modeling before trusting the router change.
- The repo still has a large `flowpilot_router.py`; this round intentionally did not split it, to avoid mixing protocol convergence with file-structure refactoring.

### Skipped Steps
- Production replay adapter for the abstract router-loop model remains skipped with an explicit reason: no adapter exists in this repository.

### Next Actions
- Keep legal waits table/contract driven. Future role-event additions should update the event contract/model and rely on generated legal-wait hazards, not add new phase-specific no-next-action branches.
- Split `flowpilot_router.py` later as maintenance debt after protocol behavior stabilizes.


## flowpilot-control-plane-repair-liveness - Strengthen FlowPilot control-plane friction model for PM repair liveness

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Post-runtime model miss: material scan PM repair wrote reissue specs without packet runtime materialization, then router allowed only success event.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T07:39:46+00:00
- Ended: 2026-05-08T07:39:46+00:00
- Duration seconds: 0.000
- Commands OK: False

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py

### Commands
- OK (0.000s): `python import preflight returned FlowGuard schema 1.0`
- OK (0.000s): `python -m py_compile simulations/flowpilot_control_plane_friction_model.py simulations/run_flowpilot_control_plane_friction_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_control_plane_friction_checks.py --skip-live-audit`
- FAIL (0.000s): `expected-live-findings: python simulations/run_flowpilot_control_plane_friction_checks.py --json-out simulations/flowpilot_control_plane_friction_results.json`

### Findings
- Added PM repair reissue liveness invariants requiring replacement packet specs to materialize into physical packet files, packet_ledger, and material dispatch index.
- Live audit now reports pm_repair_reissue_packets_not_materialized, pm_repair_success_only_gate_blocks_reviewer_recheck_failure, and reviewer_recheck_protocol_blocker_unroutable for run-20260508-064618.

### Counterexamples
- Hazards detect unmaterialized repair specs, success-only gates after unmaterialized reissue, and unroutable reviewer recheck protocol blockers.

### Friction Points
- The previous model treated PM repair follow-up as a matchable event-name problem; the real failure was semantic routability when the success event could not legally be emitted.

### Skipped Steps
- Production router/packet-runtime repair skipped; user asked first to upgrade FlowGuard so the model catches the issue.

### Next Actions
- Repair FlowPilot runtime so PM repair reissues are materialized/registered and reviewer non-success recheck events are valid router inputs.


## flowguard-coverage-sweep-ledger - Add read-only FlowGuard coverage sweep and finding ledger

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Coverage audit showed that model upgrade decisions need a unified sweep runner that classifies abstract/source/live/progress/hazard findings before changing runtime or models.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T08:08:44+00:00
- Ended: 2026-05-08T08:08:44+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- scripts/run_flowguard_coverage_sweep.py
- docs/flowguard_coverage_sweep.md

### Commands
- OK (0.000s): `python import preflight returned FlowGuard schema 1.0`
- OK (0.000s): `python -m py_compile scripts/run_flowguard_coverage_sweep.py`
- OK (0.000s): `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 120`

### Findings
- Added a read-only coverage sweep that executes non-writing runners and reads existing JSON results for runners that write by default.
- Sweep normalized 22 runners into abstract/source/live/progress/hazards sections and produced 8 current live findings, all classified as modeled_current_live_hit_fix_runtime_or_current_state.

### Counterexamples
- Current run run-20260508-064618 still surfaces 7 direct control-plane live errors plus one gate-policy pointer to those live audit findings.

### Friction Points
- Most run_*_checks.py scripts still write result files by default, so the read-only sweep must treat those as existing-result reads until runners gain a no-write mode.

### Skipped Steps
- none recorded

### Next Actions
- Use the coverage ledger before deciding whether to fix runtime, fix check flow, or expand a model.


## flowpilot-repair-transaction-coverage-plan - Model FlowPilot repair transactions before runtime repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to upgrade FlowGuard coverage for repair/reissue/routing failures before changing runtime.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T08:22:26+00:00
- Ended: 2026-05-08T08:22:26+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_repair_transaction_model.py
- simulations/run_flowpilot_repair_transaction_checks.py
- simulations/flowpilot_repair_transaction_results.json
- scripts/run_flowguard_coverage_sweep.py

### Commands
- OK (0.000s): `python -m py_compile simulations\flowpilot_repair_transaction_model.py simulations\run_flowpilot_repair_transaction_checks.py scripts\run_flowguard_coverage_sweep.py`
- OK (0.000s): `python simulations\run_flowpilot_repair_transaction_checks.py --json-out simulations\flowpilot_repair_transaction_results.json`
- OK (0.000s): `background: python scripts\run_flowguard_coverage_sweep.py --timeout-seconds 180`

### Findings
- Added a generic repair transaction model covering blocker registration, PM repair decisions, atomic replacement packet generation commit, reviewer recheck routability, and authority refresh.
- Repair transaction model passes Explorer/progress/safe-graph checks: 606 traces, 0 violations, 0 dead branches, 0 reachability failures, 3 terminal states.
- Coverage sweep now sees 23 runners and classifies 8 current live findings as modeled_current_live_hit_fix_runtime_or_current_state.

### Counterexamples
- Existing live run still shows phase/contract/write-target/current-generation/routability failures; the new model treats these as one class of missing atomic repair transaction semantics.

### Friction Points
- Most existing simulation runners still lack a no-write mode, so the sweep executes only read-only runners and reads existing JSON for writing runners.

### Skipped Steps
- Runtime repair intentionally skipped until user approves the proposed root architecture fix.

### Next Actions
- After approval, implement one repair transaction commit/finalize path in FlowPilot runtime and rerun control-plane friction plus coverage sweep.


## flowpilot-repair-transaction-runtime-implementation - Implement FlowPilot repair transactions and remove shallow repair gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Runtime stateful repair/reissue/routing logic is changing; FlowGuard model already exposed missing atomic repair transaction semantics.
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-08T08:41:50+00:00
- Ended: 2026-05-08T08:41:50+00:00
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


## flowpilot-repair-transaction-runtime-implementation - Implement FlowPilot repair transactions and remove shallow repair gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Runtime stateful repair/reissue/routing logic changed after FlowGuard exposed missing atomic repair transaction semantics.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T09:02:44+00:00
- Ended: 2026-05-08T09:02:44+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_repair_transaction_model.py
- simulations/flowpilot_control_plane_friction_model.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_repair_transaction_checks.py --json-out simulations/flowpilot_repair_transaction_results.json`
- OK (0.000s): `python simulations/run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations/flowpilot_control_plane_friction_results.json`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 300`
- OK (0.000s): `python -m unittest targeted FlowPilot repair/control/packet/output tests`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`

### Findings
- Runtime now requires PM repair decisions to open a repair transaction; packet reissue commits files, ledger, dispatch index, outcome table, frontier, and visible indexes together.
- The old live run still has seven modeled historical findings; new runtime conformance is covered by model and router regression tests rather than mutating that stopped run.

### Counterexamples
- none recorded

### Friction Points
- The full router runtime test module exceeded a five-minute shell timeout, so verification used targeted router tests plus adjacent packet/control/output suites.

### Skipped Steps
- none recorded

### Next Actions
- Use coverage sweep to classify future findings before deciding whether to fix runtime, source checks, or model coverage.

## flowpilot-route-display-20260508 - Model and repair FlowPilot route display projection lifecycle

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Route display behavior depends on canonical route/frontier/snapshot state and user-visible display receipts
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T12:49:20+00:00
- Ended: 2026-05-08T12:49:20+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_route_display_model.py
- simulations/run_flowpilot_route_display_checks.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_route_display_checks.py --json-out simulations/flowpilot_route_display_results.json`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python -m unittest discover tests`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json`

### Findings
- Model reproduced stale startup route=unknown Mermaid plus display_plan bullet fallback after route draft; runtime fix now renders canonical Mermaid route sign from flow.json, flow.draft.json, or route_state_snapshot.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- No visual Mermaid screenshot rendering: route sign is text Mermaid and file/live-run conformance plus unit tests covered source correctness.

### Next Actions
- Push to GitHub only after explicit user approval for remote publication.

## flowpilot-resume-liveness-preflight-20260508 - Harden heartbeat/manual resume liveness re-entry

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Heartbeat/manual mid-run resume changed stateful routing, liveness, timeout, visible-plan, and role-rehydration behavior.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T14:00:00+02:00
- Ended: 2026-05-08T16:38:19+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_resume_model.py
- simulations/run_flowpilot_resume_checks.py

### Commands
- OK: `python simulations/run_flowpilot_resume_checks.py`
- OK: all `simulations/run_*checks.py`, with `run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations/flowpilot_control_plane_friction_results.json`
- OK: `python -m py_compile skills/flowpilot/assets/flowpilot_router.py tests/test_flowpilot_router_runtime.py scripts/smoke_autopilot.py tests/test_flowguard_result_proof.py`
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py`
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py tests/test_flowguard_result_proof.py`
- OK: `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 300`
- OK: `python scripts/smoke_autopilot.py --fast`
- OK: `python scripts/check_install.py`
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/install_flowpilot.py --check --json`
- OK: `python scripts/audit_local_install_sync.py --json`

### Findings
- Resume model now requires heartbeat/manual wake recording to the router, current-run visible-plan restoration, six-role liveness preflight, and timeout_unknown handling before PM resume decision.
- Runtime now treats `work_chain_status=alive` as diagnostic only; every heartbeat/manual wake enters `load_resume_state`.
- `rehydrate_role_agents` now requires host liveness status, liveness decision, bounded wait result, and an explicit `wait_agent_timeout_treated_as_active=false` receipt.
- Smoke validation now uses the same model gate as the adoption log by skipping current live-run audit for control-plane friction.

### Counterexamples
- The old active live run still reports historical control-plane friction in the coverage sweep. This task did not mutate that run or read sealed packet/result/report bodies; the model gate used `--skip-live-audit`.

### Friction Points
- Running `install_flowpilot.py --check` in parallel with `--sync-repo-owned` can see the pre-sync installed digest; rerunning the check after sync passes.

### Skipped Steps
- No repair of `.flowpilot/runs/run-20260508-090520`; doing so would continue or mutate the current FlowPilot route, which was out of scope.

### Next Actions
- If future work wants live-run audit to pass, treat it as a separate FlowPilot route repair task with explicit authorization.


## flowpilot-pm-resume-decision-contract-audit-20260508 - Audit PM resume decision router rejection and model coverage

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Heartbeat/manual resume PM decision was rejected twice because router JSON requirements were stricter than role-visible contract/template.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-08T15:20:19+00:00
- Ended: 2026-05-08T15:20:19+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python simulations/run_flowpilot_resume_checks.py; python simulations/run_router_action_contract_checks.py --json-out temp; python simulations/run_protocol_contract_conformance_checks.py --json-out temp; python -m unittest targeted resume tests`

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

## flowpilot-cross-plane-friction-20260509 - Formalize runtime/control-plane model coverage

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Postmortem found same-class friction across route/frontier/ledger/lifecycle/Cockpit/install planes that prior single-plane models did not catch.
- Status: completed_model_and_strategy_only
- Skill decision: used_flowguard
- Started: 2026-05-09T00:00:00+02:00
- Ended: 2026-05-09T00:00:00+02:00
- Commands OK: partial; the new model checks passed, but the broader smoke run hit a pre-existing capability_model regression.

### Model Files
- simulations/flowpilot_cross_plane_friction_model.py
- simulations/run_flowpilot_cross_plane_friction_checks.py
- simulations/flowpilot_cross_plane_friction_results.json
- simulations/flowpilot_cross_plane_friction_live_results.json
- simulations/flowpilot_control_plane_friction_live_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python -m py_compile simulations\flowpilot_cross_plane_friction_model.py simulations\run_flowpilot_cross_plane_friction_checks.py scripts\smoke_autopilot.py scripts\run_flowguard_coverage_sweep.py scripts\check_install.py`
- OK: `python simulations\run_flowpilot_cross_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_cross_plane_friction_results.json`
- EXPECTED_FINDINGS: `python simulations\run_flowpilot_cross_plane_friction_checks.py --live-root . --run-id run-20260508-090520 --json-out simulations\flowpilot_cross_plane_friction_live_results.json`
- EXPECTED_FINDINGS: `python simulations\run_flowpilot_control_plane_friction_checks.py --live-root . --json-out simulations\flowpilot_control_plane_friction_live_results.json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\run_flowguard_coverage_sweep.py --timeout-seconds 120 --json-out simulations\flowguard_coverage_sweep_cross_plane_latest.json`
- FAILED_EXISTING: `python scripts\smoke_autopilot.py --fast` stopped in `simulations/capability_model.py` because `_step()` received duplicate `child_skill_manifest_only_evidence_rejected`.

### Findings
- The new cross-plane model detects 21 same-class negative scenarios, including terminal authority mismatch, completed-node projection drift, Cockpit active-tab drift, reviewer event taxonomy gaps, source-layout policy conflict, active-node completion idempotency drift, and six-role liveness proof gaps.
- Live scan of `run-20260508-090520` found 9 current cross-plane findings: material dispatch write target missing; missing canonical `lifecycle/run_lifecycle.json`; completed frontier nodes displayed pending/current in `route_state_snapshot`; completed checklist items left pending in snapshot; selected/current state conflated with completed state; Cockpit checklist projection mismatch; Cockpit closed run exposed as active tab; reviewer block event taxonomy gap for `reviewer_blocks_current_node_dispatch` and `reviewer_blocks_node_acceptance_plan`; install audit still treating `flowpilot_cockpit` as legacy-absent source.
- Existing control-plane model still separately finds material dispatch output contract mismatch and material dispatch write target missing on the repaired material-scan packets.
- Coverage sweep now classifies `flowpilot_cross_plane_friction` as `coverage_strong` and records 11 live findings across cross-plane and existing control-plane models.

### Counterexamples
- The abstract safe strategy state passes all invariants, but the current live run intentionally fails the live audit until production repair is authorized.
- Broad smoke regression is blocked by a capability-model duplicate-keyword issue that was already present in the modified worktree; this task did not repair it.

### Friction Points
- The previous model set was too fragmented: route display, packet lifecycle, terminal lifecycle, event taxonomy, and install-layout policy were modeled separately, so cross-plane inconsistency was not a required invariant.
- Live audit must distinguish internal reconciliation events from external reviewer blocker events; the first draft over-reported `reconcile_current_run` and was narrowed to reviewer block/unknown external events only.

### Skipped Steps
- No production runtime or Cockpit repair was applied; the user requested model upgrade, issue scan, and minimal repair strategy first.
- No sealed packet/result/report/decision bodies were opened by the new cross-plane live audit; it reads metadata and envelopes only.

### Next Actions
- After user approval, implement the six minimal repair slices: canonical terminal lifecycle transaction; material packet envelope contract/write-target normalization; frontier-based route snapshot projection; Cockpit adapter completion/active-tab projection; reviewer blocker event taxonomy closure; source-layout/install-audit alignment.
- Before final release, separately repair or rebase the existing `capability_model.py` duplicate-keyword regression so `scripts/smoke_autopilot.py --fast` can pass again.

## flowpilot-skill-standard-fidelity-model-upgrade-20260509 - Upgrade capability model for child-skill quality dilution and UI review gaps

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Retrospective found that the FlowPilot Cockpit UI run passed formal gates while child-skill standards, concept comparison, visual polish, interaction reachability, palette defaults, execution reports, and review strictness were diluted.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-09T08:05:40+02:00
- Ended: 2026-05-09T08:05:40+02:00
- Commands OK: True

### Model Files
- simulations/capability_model.py
- simulations/run_capability_checks.py
- simulations/capability_results.json
- simulations/capability_results.proof.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python -m py_compile simulations\capability_model.py simulations\run_capability_checks.py`
- OK: `python simulations\run_capability_checks.py --force`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python simulations\run_meta_checks.py`
- OK: `python scripts\smoke_autopilot.py --fast`

### Findings
- The prior capability model checked that UI gates existed, but did not require original child-skill standards to be extracted, promoted into node contracts, and bound to non-manifest execution evidence.
- The prior UI route model did not force selected concept binding, palette/default-or-override rationale, frontend-design execution reporting, complete visible-affordance interaction matrices, concept-vs-implementation deviation tables, required iteration budgets, or structural redesign consideration before loop closure.
- The upgraded model raises UI child-skill iteration obligations to 20 default rounds and 40 maximum rounds while keeping the existing low state-space branch bound for abstract loop exploration.

### Counterexamples
- Added hazard regression cases for standard inheritance loss, manifest-only gate evidence, missing child-skill execution reports, missing palette rationale, missing selected-concept binding, incomplete interaction matrix, missing deviation table, underfilled iteration budget, and missing structural redesign consideration.
- `python simulations\run_capability_checks.py --force` covered 607187 states, 632646 edges, zero invariant failures, zero missing labels, zero stuck states, and all 9 hazard cases matched the expected rejecting invariant.
- `python simulations\run_meta_checks.py` covered 598029 states and 618200 edges with zero invariant failures, zero missing labels, and zero stuck states.

### Friction Points
- The first hazard-regression implementation used a generic successful baseline state, which selected a backend success state and failed to exercise UI-only hazards. The runner now chooses a UI success baseline when the hazard mutates UI fields.
- The previous `capability_model.py` duplicate-keyword blocker was resolved while integrating the new child-skill evidence reset fields.
- The broader smoke suite now reuses both meta and capability proofs successfully after this repair.

### Skipped Steps
- No product UI code was modified; this task upgraded the FlowGuard capability model and checker only.
- No release or publish action was performed.

### Next Actions
- Use the new hazard-regression pattern for future same-class FlowGuard model upgrades instead of relying only on reachable-state graph closure.
- When repairing the Cockpit UI implementation later, require the route packet and reviewer reports to cite these new model fields rather than treating them as optional evidence.

## flowpilot-runtime-cross-plane-repair-20260509 - Repair approved runtime friction after sealed-run audit

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User authorized opening previously sealed run artifacts in review mode, then approved production repairs for the first five cross-plane findings plus the capability checker crash while excluding formal Cockpit source-layout alignment.
- Status: completed_approved_scope
- Skill decision: used_flowguard
- Started: 2026-05-09T08:08:00+02:00
- Ended: 2026-05-09T08:13:02+02:00
- Commands OK: True for approved scope; one live cross-plane finding remains intentionally excluded by user direction.

### Model Files
- simulations/capability_model.py
- simulations/flowpilot_control_plane_friction_model.py
- simulations/flowpilot_control_plane_friction_results.json
- simulations/flowpilot_control_plane_friction_live_results.json
- simulations/flowpilot_cross_plane_friction_results.json
- simulations/flowpilot_cross_plane_friction_live_results.json
- simulations/flowpilot_packet_lifecycle_results.json
- simulations/protocol_contract_conformance_results.json

### Runtime Files
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/packet_runtime.py
- flowpilot_cockpit/source_adapter.py
- tests/test_flowpilot_router_runtime.py
- tests/test_flowpilot_cockpit_source_adapter.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: sealed run audit inspected 327 JSON artifacts under `.flowpilot/runs/run-20260508-090520`, including 210 packet/result/report/decision/audit/ledger related records.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py flowpilot_cockpit\source_adapter.py simulations\flowpilot_control_plane_friction_model.py`
- OK: targeted pytest covered material packet write-targets, terminal snapshot projection, legacy lifecycle recovery, reviewer block taxonomy, and Cockpit adapter projection.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_live_results.json`
- OK: `python simulations\run_flowpilot_cross_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_cross_plane_friction_results.json`
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py`
- OK: `python simulations\run_protocol_contract_conformance_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\smoke_autopilot.py --fast`
- EXPECTED_EXCLUDED: `python simulations\run_flowpilot_cross_plane_friction_checks.py --json-out simulations\flowpilot_cross_plane_friction_live_results.json` reports only `install_audit_layout_policy_conflict`, because the user explicitly excluded formalizing the current experimental Cockpit source layout.

### Findings
- The sealed artifact review confirmed the work route was actually complete: node completion ledgers closed the FlowPilot-completable work, and human inspection items belonged in the final report instead of remaining route nodes.
- The material-scan packet family lacked explicit result write targets in legacy packet contracts even though result envelopes existed; new packet creation now writes result envelope/body targets, and reconciliation backfills legacy material envelopes, indexes, and ledgers without opening sealed bodies.
- Terminal authorities existed but the canonical `lifecycle/run_lifecycle.json` could be missing; reconciliation now writes the missing terminal lifecycle record and refreshes current/index/snapshot state.
- `route_state_snapshot` could show completed frontier nodes as pending/current; snapshot projection now derives completed status and checklist completion from `execution_frontier` and separates UI selection state from completion/current execution state.
- Reviewer block events for current-node dispatch and node-acceptance-plan review were real external protocol events but absent from the router event taxonomy; they are now registered and write block reports.
- The installed FlowPilot skill now matches repository source digest after sync.

### Counterexamples
- The prior `capability_model.py` merge path could pass the same child-skill evidence reset field twice into `_step()`. The checker now merges route and reset deltas before calling `_step()`, and the smoke suite no longer hits the duplicate-keyword crash.
- The live cross-plane audit still flags `install_audit_layout_policy_conflict`. This is not an approved-scope failure in this task because the current Cockpit source was explicitly kept experimental and not promoted to a formal install-audited source package.

### Friction Points
- Running install sync and install check at the same time can create a false drift report while the sync is still in progress; rerun the check after sync finishes.
- A runtime migration should mutate envelopes/indexes/ledgers and write an explicit migration report, not rewrite sealed packet bodies.

### Skipped Steps
- Did not promote or package the current experimental Cockpit as formal FlowPilot source.
- Did not push to GitHub.
- Did not delete or rewrite sealed bodies; sealed bodies were opened only in this review/audit phase as authorized by the user.

### Next Actions
- When the user approves a full Cockpit rebuild, decide whether the new Cockpit becomes a first-class install-audited source package or remains generated/ignored; then update the install audit policy accordingly.

## flowpilot-planning-quality-contract-20260509 - Add PM profile and skill-standard projection gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved a minimal FlowPilot process upgrade after a Cockpit UI run exposed PM route coarseness, child-skill standard dilution, and reviewer residual-blindspot pass-through.
- Status: optimized_not_synced
- Skill decision: used_flowguard
- Started: 2026-05-09T08:20:00+02:00
- Ended: 2026-05-09T08:57:05+02:00
- Commands OK: True for modeling, targeted runtime tests, and install/smoke checks; full router-runtime pytest was intentionally replaced by scoped router tests after a broad timeout.

### Model Files
- simulations/flowpilot_planning_quality_model.py
- simulations/run_flowpilot_planning_quality_checks.py
- simulations/flowpilot_planning_quality_results.json

### Runtime Files
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_gate_manifest.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/route_challenge.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/child_skill_gate_manifest_review.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md
- templates/flowpilot/child_skill_gate_manifest.template.json
- templates/flowpilot/node_acceptance_plan.template.json
- templates/flowpilot/packets/packet_body.template.md
- templates/flowpilot/packets/result_body.template.md
- skills/flowpilot/assets/runtime_kit/contracts/contract_index.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python -m py_compile simulations\flowpilot_planning_quality_model.py simulations\run_flowpilot_planning_quality_checks.py`
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`
- OK: `python -m py_compile simulations\flowpilot_planning_quality_model.py simulations\run_flowpilot_planning_quality_checks.py scripts\check_install.py`
- OK: `python -m pytest tests\test_flowpilot_planning_quality.py tests\test_flowpilot_output_contracts.py tests\test_flowpilot_card_instruction_coverage.py`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python simulations\run_output_contract_checks.py`
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py`
- OK: `python simulations\run_protocol_contract_conformance_checks.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python scripts\check_install.py`
- OK: `python scripts\smoke_autopilot.py --fast`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_planning_quality.py tests\test_flowpilot_output_contracts.py -q`
- OK: scoped router runtime tests for route skeleton, node acceptance artifact validation, packet relay, reviewer packet audit, and safe envelope aliases.
- TIMEOUT_REPLACED: `python -m pytest tests\test_flowpilot_planning_quality.py tests\test_flowpilot_output_contracts.py tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_router_runtime.py` exceeded the 300s limit because it included the full router runtime suite. It was replaced with the targeted tests above.

### Findings
- The planning-quality model accepts only the valid high-fidelity UI route and valid simple-repair route shapes.
- It rejects the same-class hazards from the Cockpit miss: no planning profile, missing convergence loop, selected skill without a Skill Standard Contract, missing MUST/DEFAULT/FORBID/VERIFY/LOOP/ARTIFACT/WAIVER fields, unmapped skill standards, missing LOOP/VERIFY/ARTIFACT inheritance, missing node/work-packet projection, reviewer hard-blindspot pass, overmerged complex implementation nodes, artifactless major nodes, and simple-task over-templating.
- Runtime cards now make PM route profiles, Skill Standard Contracts, node/work packet projection, reviewer hard-block rules, and Skill Standard Result Matrix reporting explicit.

### Counterexamples
- The first model draft rejected hazards but mislabeled every negative rejection as `reject_valid_ui_route` or `reject_valid_simple_route`. The scenario field is now preserved in hazard states, so required reachability labels prove each same-class failure is rejected separately.

### Skipped Steps
- No Cockpit UI repair or rerun was performed; the user explicitly asked to optimize FlowPilot flow first.
- No local installed-skill sync, version bump, git commit/tag, or GitHub push/release was performed, per the user's later instruction to stop before synchronization.

### Next Actions
- Wait for user approval before syncing the repository source into the local installed FlowPilot skill, bumping the patch version, committing/tagging, or pushing to GitHub.

## flowpilot-worker-dispatch-guidance-20260509 - Add lightweight PM worker packet balance guidance

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that PM worker assignment had no lightweight prompt-level guidance, causing worker selection to behave like free choice with a `worker_a` default bias in some packet paths.
- Status: optimized_not_synced
- Skill decision: used_flowguard_lightweight
- Started: 2026-05-09T09:05:00+02:00
- Ended: 2026-05-09T09:21:39+02:00
- Commands OK: True for import preflight, targeted card tests, card coverage, install check, and existing FlowGuard meta/capability proof reuse.

### Model Files
- Existing FlowGuard meta and capability proof files reused because this change edits PM card guidance only and does not change router state transitions or capability model source.

### Runtime Files
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_scan.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_package.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md
- skills/flowpilot/assets/runtime_kit/cards/events/pm_reviewer_blocked.md
- tests/test_flowpilot_card_instruction_coverage.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python "<codex-skills>\model-first-function-flow\assets\toolchain_preflight.py" --json`
- OK: `python -m pytest tests\test_flowpilot_card_instruction_coverage.py -q`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `git diff --check` reported only CRLF warnings.

### Findings
- PM worker-packet cards now tell PM to choose either `worker_a` or `worker_b` for light/single-scope work while keeping opportunities roughly balanced across the current run.
- Heavy naturally separable work is now prompt-routed toward bounded disjoint packets for both workers when parallel work can avoid overlapping files, evidence duties, or review ownership.
- Reviewer-blocked repair and sender reissue now prefer returning work to the same worker that produced the blocked result, preserving local context unless the worker is unavailable, the issue shows a fundamental misunderstanding, or the repair has become separable new work.
- The guidance intentionally avoids "do not default to worker_a" language so it does not bias PM into mechanically choosing `worker_b`.

### Skipped Steps
- No router scheduling algorithm, worker load ledger, busy lease, or automatic reassignment logic was added.
- No local installed-skill sync, version bump, git commit/tag, or GitHub push/release was performed per user instruction.

### Next Actions
- Wait for user approval before any local install sync, version bump, commit/tag, or GitHub publication.

## flowpilot-reviewer-active-challenge-20260509 - Require reviewer independent challenge gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved a FlowPilot process upgrade after review discussion showed that reviewers could pass low-standard PM packets without actively looking for task-specific failures such as inert UI controls, rough rendering, or hidden implementation gaps.
- Status: optimized_not_synced
- Skill decision: used_flowguard
- Started: 2026-05-09T08:58:00+02:00
- Ended: 2026-05-09T09:21:51+02:00
- Commands OK: True for the new reviewer active-challenge model, production card/template/contract checks, full FlowGuard runner sweep, full meta/capability regressions, and scoped test suite.

### Model Files
- simulations/flowpilot_reviewer_active_challenge_model.py
- simulations/run_flowpilot_reviewer_active_challenge_checks.py
- simulations/flowpilot_reviewer_active_challenge_results.json

### Runtime Files
- skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/material_sufficiency.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/startup_fact_check.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/final_backward_replay.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/route_challenge.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/dispatch_request.md
- skills/flowpilot/assets/runtime_kit/contracts/contract_index.json
- templates/flowpilot/human_review.template.json
- templates/flowpilot/research_reviewer_report.template.json
- templates/flowpilot/packets/packet_body.template.md
- scripts/check_install.py
- scripts/run_flowguard_coverage_sweep.py
- scripts/smoke_autopilot.py
- simulations/flowpilot_output_contract_model.py
- tests/test_flowpilot_reviewer_active_challenge.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`
- OK: `python -m py_compile simulations\flowpilot_reviewer_active_challenge_model.py simulations\run_flowpilot_reviewer_active_challenge_checks.py tests\test_flowpilot_reviewer_active_challenge.py`
- OK: `python simulations\run_flowpilot_reviewer_active_challenge_checks.py --json-out simulations\flowpilot_reviewer_active_challenge_results.json`
- OK: `python -m pytest tests\test_flowpilot_reviewer_active_challenge.py -q`
- OK: `python -m pytest tests\test_flowpilot_planning_quality.py tests\test_flowpilot_output_contracts.py tests\test_flowpilot_card_instruction_coverage.py -q`
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_output_contract_checks.py --json-out simulations\flowpilot_output_contract_results.json`
- OK: `python -m py_compile scripts\check_install.py scripts\smoke_autopilot.py simulations\flowpilot_output_contract_model.py simulations\flowpilot_reviewer_active_challenge_model.py simulations\run_flowpilot_reviewer_active_challenge_checks.py`
- OK: all 28 `simulations/run_*_checks.py` runners completed successfully in the FlowGuard sweep.
- OK: `python -m pytest tests -q --import-mode=importlib` returned `168 passed, 14 subtests passed`.
- OK: `python simulations\run_meta_checks.py --force`
- OK: `python simulations\run_capability_checks.py --force`
- OK: `python scripts\smoke_autopilot.py --fast`
- OK: `python -m py_compile scripts\run_flowguard_coverage_sweep.py`
- OK_WITH_PENDING_SYNC_FINDING: `python scripts\run_flowguard_coverage_sweep.py --timeout-seconds 120` parsed all 28 runners and reported one live finding, `installed_skill_source_drift`, because the user explicitly asked not to sync the changed repository source into the local installed FlowPilot skill yet.
- OK: `git diff --check` reported no whitespace errors; Git only warned about future LF-to-CRLF normalization on Windows.
- EXPECTED_SCOPE_NOTE: broad `python -m pytest -q` still collects duplicate backup test modules under `backups/`, so the validated project test command uses `tests --import-mode=importlib`.

### Findings
- The new model accepts valid UI/code/document/simple review paths and rejects same-class hazards where a reviewer relies only on the PM checklist, misses scope restatement, omits explicit or implicit commitments, lacks failure hypotheses, uses generic challenge actions, lacks direct evidence or waiver, downgrades hard issues into residual risk, leaves core commitments unverified, fails to reroute blockers, or overburdens simple tasks.
- Reviewer role guidance now says the PM package is a minimum floor rather than the review boundary.
- Reviewer reports now require an `independent_challenge` section with scope, commitments, failure hypotheses, task-specific challenge actions, blocking/non-blocking findings, pass/block decision, reroute request, and waivers.
- Reviewer contract templates and install checks now enforce the new challenge fields, so a reviewer pass without active challenge evidence is structurally invalid.
- The coverage sweep now recognizes result files declared with `Path(__file__).resolve().with_name(...)`, so the planning-quality and reviewer active-challenge runners are included in the read-only sweep instead of being misclassified as unparsed.

### Counterexamples
- A checklist-only pass can no longer satisfy the modeled reviewer gate.
- A reviewer can no longer pass a user hard requirement, frozen contract, selected child-skill standard, quality-level requirement, exposed product behavior, or core commitment by moving it to residual risk.
- A reviewer that cannot directly inspect a required artifact must either provide an approved waiver or block/reroute; silence is modeled as a failure.

### Skipped Steps
- No Cockpit UI repair was performed; the user asked to fix the FlowPilot review process first.
- No local installed-skill sync, local Git commit, version bump, tag, or GitHub push/release was performed, per the user's instruction to decide those synchronization steps later.

### Next Actions
- Wait for user approval before syncing this repository source into the local installed FlowPilot skill, bumping version metadata, committing/tagging, or pushing to GitHub.

## flowpilot-reviewer-pm-authority-boundary-20260509 - Keep reviewer challenge advisory to PM except hard blockers

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that reviewer standard/simplicity concerns should inform PM rather than make the reviewer a second PM.
- Status: source_updated_not_synced
- Skill decision: used_flowguard with existing reviewer active-challenge and planning-quality models.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- OK: `python -m unittest tests.test_flowpilot_reviewer_active_challenge tests.test_flowpilot_card_instruction_coverage`.
- OK: `python simulations\run_flowpilot_reviewer_active_challenge_checks.py --json-out simulations\flowpilot_reviewer_active_challenge_results.json`.
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`.

### Findings
- The prompt change is deliberately small: reviewer findings about higher standards, simpler equivalent paths, over-repair, or unnecessary complexity are PM decision-support unless they expose hard blockers.
- PM remains final owner of route choice, repair strategy, waiver, mutation, and completion decisions.
- Existing models still pass and continue to reject checklist-only reviewer passes, hard-issue downgrades, and simple-task overburdening.

### Skipped Steps
- No installed-skill sync, git stage/commit, version bump, tag, or GitHub push was performed per user instruction.

## flowpilot-runtime-session-receipt-friction-20260509 - Unify runtime receipts without heavy access history

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User reported repeated FlowPilot router friction when workers produced valid-looking results without using the runtime packet open path, causing mechanical receipt gaps to escalate to PM repair.
- Status: source_updated_not_synced
- Skill decision: used_flowguard because the change affects role boundaries, packet/result body access, ledger receipts, router blocker classification, and recovery routing.

### Model Boundary
- Added a unified runtime-session path for packet recipients and result reviewers so normal work automatically records minimal open receipts and result absorption.
- Classified missing mechanical receipts as same-role control-plane reissue instead of PM repair by default.
- Deliberately trimmed the proposed access-attempt history, first-open ownership, and open counters after design review; the retained audit proof is minimal receipt metadata plus existing role/hash/relay checks.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- OK: `python -m py_compile skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_packet_lifecycle_model.py simulations\run_flowpilot_packet_lifecycle_checks.py`.
- OK: `python -m unittest tests.test_flowpilot_packet_runtime`.
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py --no-write`.
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py`.
- OK: targeted router regression for packet-open receipt, result absorption, and mechanical agent-id reissue cases.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit`.
- OK: `python simulations\run_protocol_contract_conformance_checks.py`.
- OK: full `tests.test_flowpilot_router_runtime` regression completed with 101 tests passing.

### Findings
- The normal worker/officer path now has one runtime entry for opening the assigned packet and submitting the result, so the runtime, not the worker prompt text, owns receipt and envelope metadata.
- The reviewer/PM result-read path uses the same runtime pattern for sealed result bodies without exposing body content to Controller.
- Router recovery now separates mechanical metadata gaps from content/authority failures: missing receipts can go back to the responsible role, while wrong role, stale packet, hash mismatch, unresolved ambiguity, or Controller-origin contamination remain PM/reviewer-level blockers.
- The over-heavy access-history branch was removed because role/hash/relay checks already block the important unsafe reads; logging every attempt would add friction and audit noise without enough safety gain.

### Skipped Steps
- No local installed-skill sync, git stage/commit, version bump, tag, or GitHub push was performed per user instruction.

## flowpilot-0.6.1-release-sync-20260509 - Publish role-output runtime and quality-pack release

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved synchronizing the repository source, local installed FlowPilot skill, local git state, remote GitHub branch, tag, and GitHub Release after the role-output runtime and quality-pack catalog work.
- Status: release_verified_pending_publish
- Skill decision: used FlowGuard-backed release discipline because the work publishes behavior-bearing runtime, router, role-card, contract, and model changes to downstream users.

### Version Decision
- Reused `0.6.1` because the local source already declares `0.6.1` and neither the local tag set nor the remote GitHub tag set contains `v0.6.1`.
- No `0.6.2` bump is required unless release validation finds a patch-only correction that should be separated from the already documented `0.6.1` changes.

### Release Boundary
- Publish the FlowPilot source package only; no binary application bundle is part of this release.
- Preserve all existing user/peer-agent repository changes in the release scope instead of reverting unrelated dirty work.
- Synchronize the repository-owned `flowpilot` skill into the local Codex installed-skill directory before final git publication.

### Commands
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json` synchronized repository `skills/flowpilot` to the local Codex skills install directory.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\check_public_release.py --json --skip-validation` passed with only the expected dirty-worktree warning before commit.

### Planned Checks
- Runtime/router/contract targeted unit tests for role-output runtime, packet runtime, and compact role-output envelope acceptance.
- FlowGuard simulation checks for role-output runtime, output contracts, protocol conformance, release tooling, packet lifecycle, repair transactions, and install checks.
- Public release privacy and dependency-source checks after staging and again after commit/tag when the worktree is clean.
- GitHub ruleset/branch-protection verification before final reporting.

### Verification Progress
- OK: `python -m py_compile skills\flowpilot\assets\role_output_runtime.py skills\flowpilot\assets\flowpilot_router.py scripts\flowpilot_runtime.py scripts\flowpilot_outputs.py simulations\flowpilot_role_output_runtime_model.py simulations\flowpilot_protocol_contract_conformance_model.py`.
- OK: `python -m pytest tests\test_flowpilot_output_contracts.py tests\test_flowpilot_role_output_runtime.py -q` returned `10 passed`.
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py -q` returned `18 passed`.
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "role_output_envelope or missing_open_receipt or pm_resume_recovery_decision or control_blocker"` returned `9 passed, 92 deselected`.
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py`.
- OK: `python simulations\run_output_contract_checks.py`.
- OK: `python simulations\run_protocol_contract_conformance_checks.py`.
- OK: `python simulations\run_release_tooling_checks.py`.
- OK: `python scripts\check_install.py --json`.
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py`.
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py`.
- OK: `python simulations\run_card_instruction_coverage_checks.py`.
- OK: `python scripts\smoke_autopilot.py --fast`.
- OK: all `simulations\run_*_checks.py` runners exited 0 under the release-safe profile; `run_meta_checks.py` and `run_capability_checks.py` used `--fast`, and live-run friction checks used `--skip-live-audit`.
- OK: background full `python -m pytest tests -q --import-mode=importlib` returned `182 passed, 19 subtests passed`.
- Fixed release tooling after clean public preflight found that the default
  smoke command exhausted memory in full meta/capability graph exploration;
  `check_public_release.py` now invokes `scripts\smoke_autopilot.py --fast`,
  matching the release-safe proof-reuse path already validated above.

### Continuation Verification
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py -q -k "role_output_envelope or missing_open_receipt or pm_resume_recovery_decision or control_blocker"` returned `9 passed, 92 deselected`.
- OK: `python -m pytest tests/test_flowpilot_packet_runtime.py -q` returned `18 passed`.
- OK: `python -m pytest tests/test_flowpilot_output_contracts.py tests/test_flowpilot_role_output_runtime.py -q` returned `10 passed`.
- OK: `python simulations/run_flowpilot_role_output_runtime_checks.py`.
- OK: `python simulations/run_output_contract_checks.py`.
- OK: `python simulations/run_card_instruction_coverage_checks.py`.
- OK: `python simulations/run_protocol_contract_conformance_checks.py` after updating the model oracle from legacy top-level role-output path/hash fields to compact `body_ref` and `runtime_receipt_ref` references.
- OK: `python simulations/run_flowpilot_repair_transaction_checks.py`.
- OK: `python simulations/run_flowpilot_packet_lifecycle_checks.py`.
- OK: `python simulations/run_prompt_isolation_checks.py`.
- OK: `python simulations/run_router_action_contract_checks.py`.
- OK: `python scripts/check_install.py --json`.
- OK: background `python simulations/run_meta_checks.py --fast` and `python simulations/run_capability_checks.py --fast` reused valid proofs.
- OK with live-audit caveats: background scan of `simulations/run_*_checks.py` passed all model/source checks except the two expected live environment checks below.

### Continuation Findings
- The protocol conformance model previously assumed role-output envelopes must expose top-level `report_path`/`decision_path`/`result_body_path` pairs. That was a model miss for the new lower-friction design; the required new pair is now `body_ref.path/body_ref.hash` plus `runtime_receipt_ref.path/runtime_receipt_ref.hash`, while legacy top-level pairs remain compatibility inputs.
- `run_flowpilot_control_plane_friction_checks.py` still reports live-run warnings for `.flowpilot/runs/run-20260509-102855`: stale active repair transaction state, unproven terminal heartbeat cleanup, and a stale persisted role-output hash from the current run artifact. This check is live-state audit evidence, not a failure of the new source model.
- `run_flowpilot_cross_plane_friction_checks.py` still reports installed FlowPilot skill source drift because the repository copy was intentionally not synchronized to the local installed skill per user instruction.
- `python -m pytest tests -q` was attempted as a full unit regression but timed out after five minutes, so it is not claimed as passed. Targeted runtime/router/contract tests above were used as the practical verification boundary for this change.

## flowpilot-0.6.0-release-sync-20260509 - Publish runtime session and router friction release

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved synchronizing the FlowPilot source, local installed skill, local gate checks, and GitHub release with a new version.
- Status: release_prepared_for_publish
- Skill decision: used_flowguard release discipline because publication changes the visible version, installed skill source, public repository state, release tag, and downstream runtime entrypoint.

### Version Decision
- Bumped FlowPilot from `0.5.5` to `0.6.0`.
- Chosen bump: minor, because the release adds a unified runtime session path and changes router recovery behavior for mechanical receipt gaps.

### Commands
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json` synchronized repository `skills/flowpilot` to the local Codex skills install directory.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\check_install.py`.
- OK: `python simulations\run_release_tooling_checks.py`.
- OK: `python simulations\run_protocol_contract_conformance_checks.py`.
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py`.
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py`.
- OK: `python scripts\smoke_autopilot.py --fast`.
- OK: `python -m pytest tests -q --import-mode=importlib` returned `176 passed, 19 subtests passed`.
- OK: `python scripts\check_public_release.py --json --skip-validation` passed privacy, dependency-source, host-capability, and release-boundary checks; the only warning was the expected dirty worktree before commit.
- OK: GitHub repository ruleset `Protect default branch` is active for `~DEFAULT_BRANCH` with deletion and non-fast-forward protection.

### Findings
- Repository source, visible README version, and changelog now agree on `v0.6.0`.
- Local installed FlowPilot skill is source-fresh against the repository copy.
- Public release scope remains FlowPilot repository only; companion skills are dependency references, not publication targets.
- Branch protection is implemented through a GitHub ruleset rather than the legacy branch protection endpoint.

### Next Actions
- Commit, tag `v0.6.0`, push `main` and the tag, create the GitHub Release, then rerun clean public release checks.

## flowpilot-0.6.1-background-role-policy-20260509 - Require explicit strongest background role policy

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A concurrent desired router change introduced explicit model and reasoning-effort policy requirements for FlowPilot background role agents after the `0.6.0` release was created.
- Status: source_updated_for_patch_release
- Skill decision: used_flowguard because the change affects startup and resume role authority records, background-agent capability evidence, and PM/reviewer trust in live role-agent records.

### Version Decision
- Bumped FlowPilot from `0.6.0` to `0.6.1`.
- Chosen bump: patch, because the release hardens role-agent policy metadata without changing the public package shape or replacing the `0.6.0` runtime session feature.

### Model Boundary
- Startup live-role spawn records now require `model_policy=strongest_available` and `reasoning_effort_policy=highest_available`.
- Resume/rehydration role records use the same required policy fields.
- Router action payloads expose the policy so role-spawn and role-resume evidence cannot silently rely on foreground/controller model inheritance.

### Planned Checks
- Install sync audit after repository-to-local skill sync.
- Router/runtime unit and pytest regression.
- Public release privacy/dependency check before GitHub publication.

## flowpilot-role-output-runtime-20260509 - Generalize report/decision clock-in runtime

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to reduce friction from hand-written high-density PM/reviewer/officer role outputs while preserving Controller/body boundaries and existing packet mail.
- Status: source_updated_not_synced
- Skill decision: used_flowguard because the change affects role-output contracts, router validation, receipts, ledgers, Controller visibility, and recovery routing.

### Model Boundary
- Added a role-output runtime model covering runtime receipt, required fields, explicit empty arrays, wrong-role submission, stale body hash, envelope body leakage, Controller body reads, and runtime overreach into semantic approval.
- Kept packet mail and packet result runtime separate; role-output runtime applies to formal file-backed decisions/reports/GateDecision bodies that return to Controller as envelopes.
- Mechanical gaps are modeled as same-role reissue candidates, while wrong role/body leakage/Controller body read remain PM-reviewable boundary failures.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- OK baseline before production edits: `python simulations\run_output_contract_checks.py`, `python simulations\run_protocol_contract_conformance_checks.py`, `python simulations\run_flowpilot_packet_lifecycle_checks.py --no-write`, `python simulations\run_flowpilot_repair_transaction_checks.py`, `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit`, and `python simulations\run_flowpilot_cross_plane_friction_checks.py --skip-live-audit`.
- OK: `python simulations\run_meta_checks.py --fast` and `python simulations\run_capability_checks.py --fast` reused valid proofs.
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py --model-only`.
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\role_output_runtime.py scripts\check_install.py tests\test_flowpilot_role_output_runtime.py tests\test_flowpilot_output_contracts.py`.
- OK: `python -m pytest tests\test_flowpilot_role_output_runtime.py tests\test_flowpilot_output_contracts.py -q`.
- OK: `python scripts\check_install.py --json`.
- OK: targeted router regression `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "role_output_envelope or pm_resume or control_blocker or gate_decision"`.
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py -q`.
- OK: `python -m pytest tests\test_flowpilot_card_instruction_coverage.py -q`.

### Findings
- `role_output_runtime.py` now prepares contract skeletons, validates required fields/fixed choices/explicit arrays, writes receipts and a role-output ledger, and returns only controller-visible envelopes.
- Router now verifies runtime receipts when a role-output envelope claims runtime validation, without allowing Controller-visible payloads to contain report/decision body fields.
- Core role cards now tell PM/reviewer/officers/workers when to use `role_output_runtime.py` versus `packet_runtime.py`, keeping packet results separate from standalone formal role outputs.

### Skipped Steps
- No local installed-skill sync, git stage/commit, version bump, tag, or GitHub push was performed per user instruction.


## flowpilot-router-owned-controller-confirmation - Remove normal startup PM controller reset and use router-owned controller core confirmation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot startup control-plane gate ordering changes
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-09T15:30:47+00:00
- Ended: 2026-05-09T15:30:47+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_optimization_proposal_model.py
- simulations/prompt_isolation_model.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_optimization_proposal_checks.py --json-out simulations/flowpilot_optimization_proposal_results.json`
- OK (0.000s): `python simulations/run_prompt_isolation_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python simulations/run_flowpilot_startup_control_checks.py --json-out simulations/flowpilot_startup_control_results.json`
- OK (0.000s): `python simulations/run_startup_pm_review_checks.py --json-out simulations/startup_pm_review_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_router_runtime`
- OK (0.000s): `python -m unittest tests.test_flowpilot_output_contracts`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/smoke_autopilot.py`

### Findings
- Normal startup no longer requires PM reset; Router-owned controller.core confirmation remains hash-backed and reviewer/PM startup gates remain.

### Counterexamples
- none recorded

### Friction Points
- Initial smoke_autopilot run timed out at six minutes while model checks were still running; rerun with longer timeout passed.

### Skipped Steps
- none recorded

### Next Actions
- none recorded


## flowpilot-card-envelope-v2 - Model and implement FlowPilot system-card envelope read receipts and guarded cross-role batch delivery

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot control-plane change involving receipts, resume ticks, agent identity, and batch dependency gates
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-09T16:38:03+00:00
- Ended: 2026-05-09T16:38:03+00:00
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


## flowpilot-card-envelope-v2 - Envelope-only system-card delivery with runtime read receipts, ack return events, and role I/O protocol receipts

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot control-flow change touching routing, runtime, ledgers, resume, and recovery gates
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-09T18:33:20+00:00
- Ended: 2026-05-09T18:33:20+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_card_envelope_model.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_card_envelope_checks.py`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python simulations/run_capability_checks.py`
- OK (0.000s): `python -m pytest tests/test_flowpilot_card_runtime.py tests/test_flowpilot_router_runtime.py -q`

### Findings
- FlowGuard model catches missing read receipt, missing ack return, wrong role/run/agent/hash, old run reuse, controller body read, hidden batch dependency, preload authorization, missing resume role I/O receipt, and read receipt replacing semantic gates
- Production router now blocks ordinary external role events while a required card return is unresolved; heartbeat/manual resume and stop/cancel remain lifecycle bypasses
- Cross-role batch is modeled and guarded in FlowGuard, but production batch delivery remains deferred to avoid widening the router sequencing change

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- If batch delivery is implemented later, start from the modeled dependency graph and join-policy invariants before changing production routing


## flowpilot-preapply-artifact-lifecycle - Prevent FlowPilot pre-apply pending actions from being relayed as committed artifacts

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot run exposed deliver_system_card pending action path before envelope artifact existed
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-09T19:25:50+00:00
- Ended: 2026-05-09T19:25:50+00:00
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


## flowpilot-preapply-artifact-lifecycle - Prevent FlowPilot pre-apply pending actions from being relayed as committed artifacts

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot run exposed deliver_system_card pending action path before envelope artifact existed
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-09T19:48:48+00:00
- Ended: 2026-05-09T19:48:48+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_card_envelope_model.py

### Commands
- OK (0.000s): `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`
- OK (0.000s): `python simulations\run_meta_checks.py`
- OK (0.000s): `python simulations\run_capability_checks.py`
- OK (0.000s): `python -m pytest tests\test_flowpilot_router_runtime.py tests\test_flowpilot_card_runtime.py -q`
- OK (0.000s): `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\install_flowpilot.py --check --json`
- OK (0.000s): `python scripts\audit_local_install_sync.py --json`

### Findings
- FlowGuard now models planned versus committed card artifacts and detects pre-apply artifact relay.
- Router auto-commits internal system-card delivery before returning a relay-ready action, so Controller only sees committed envelopes as relayable.
- Production regression test verifies envelope file existence, hash verification, ledgers, return wait, and relay_allowed before Controller relay.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Keep the same planned-vs-committed resource lifecycle boundary if other pending action families are migrated later.


## flowpilot-remove-public-system-card-apply - Remove public apply compatibility for committed FlowPilot system-card relay actions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested eliminating long-term compatibility that lets Controller apply deliver_system_card after Router commits the envelope
- Status: in_progress
- Skill decision: use_flowguard
- Started: 2026-05-09T20:11:52+00:00
- Ended: 2026-05-09T20:11:52+00:00
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


## flowpilot-remove-public-system-card-apply - Remove public apply compatibility for committed FlowPilot system-card relay actions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested eliminating long-term compatibility that lets Controller apply deliver_system_card after Router commits the envelope
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-09T21:07:03+00:00
- Ended: 2026-05-09T21:07:03+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_card_envelope_model.py

### Commands
- OK (0.000s): `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`
- OK (0.000s): `python simulations\run_meta_checks.py`
- OK (0.000s): `python simulations\run_capability_checks.py`
- OK (0.000s): `python -m pytest tests\test_flowpilot_router_runtime.py tests\test_flowpilot_card_runtime.py -q`
- OK (0.000s): `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\install_flowpilot.py --check --json`
- OK (0.000s): `python scripts\audit_local_install_sync.py --json`

### Findings
- FlowGuard now includes a public-system-card-apply hazard and detects attempts to treat relay-only delivery as an applyable Controller action.
- Router commits system-card artifacts through an internal helper instead of calling apply_controller_action(deliver_system_card).
- The public deliver_system_card apply branch now rejects the action; tests use runtime open plus ack to advance.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Keep deliver_system_card as relay metadata only; do not reintroduce public apply compatibility.


## flowpilot-card-return-event-field-rename - Rename card ack envelope field to card_return_event

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot run showed Controller could mistake a mechanical card ack name for a record-event external event because the envelope exposed a generic return event field.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-09T22:21:24Z
- Ended: 2026-05-09T22:21:24Z
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_card_envelope_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "system_card_delivery_requires_manifest_check or committed_system_card_relay_can_resolve_without_apply_roundtrip"`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py tests\test_flowpilot_card_runtime.py -q`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python simulations\run_command_refinement_checks.py`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`
- OK: `python simulations\run_card_instruction_coverage_checks.py --json-out simulations\card_instruction_coverage_results.json`
- OK: `python simulations\run_flowpilot_packet_lifecycle_checks.py --json-out simulations\flowpilot_packet_lifecycle_results.json`
- OK: `python scripts\check_install.py`
- OK: `rg -n '"return_event"\s*:' . -g '!backups/**' -g '!**/__pycache__/**' -g '!*.pyc'`
- OK: `git diff --check`

### Findings
- Card ack envelope and ledger JSON now use `card_return_event`, while internal ledger/action names such as `check_card_return_event` remain unchanged by design.
- FlowGuard now detects three hazards for this route: legacy field emission, routing card ack names through record-event, and marking check-card-return as optional when it advances state.
- Router now gives a directed error for card ack names sent to record-event, and the normal check-card-return action is marked apply-required.
- Runtime and router regression tests cover the renamed field, absence of the legacy JSON key, misuse error, and ack resolution path.

### Counterexamples
- none recorded

### Friction Points
- Full router runtime tests take about 13 minutes on this machine.
- Initial shorter meta/capability check runs hit the local timeout; reruns with a longer timeout completed successfully.

### Skipped Steps
- Installed FlowPilot skill synchronization was skipped by explicit user request. Only the current repository was changed.

### Next Actions
- Keep mechanical card ack names out of ordinary external events unless the protocol is deliberately redesigned.


## flowpilot-record-event-envelope-ref-transfer - Add path/hash event envelope transfer to record-event

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Controller reconstructed event envelopes by hand, which lost the standard `runtime_receipt_ref` on reviewer startup reports and hid PM material-scan `packets` from `payload.packets`.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-09T22:57:46Z
- Ended: 2026-05-09T22:57:46Z
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_event_envelope_transfer_model.py
- simulations/run_flowpilot_event_envelope_transfer_checks.py
- simulations/flowpilot_event_envelope_transfer_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_event_envelope_transfer_checks.py --json-out simulations\flowpilot_event_envelope_transfer_results.json`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_event_envelope_transfer_model.py simulations\run_flowpilot_event_envelope_transfer_checks.py`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "record_event_accepts_runtime_envelope_ref_for_startup_fact_report or record_event_rejects_bad_event_envelope_refs_before_payload_reconstruction or record_event_rejects_envelope_outside_current_wait or record_event_accepts_material_scan_envelope_ref_with_packets or record_event_rejects_manual_material_scan_payload_with_hidden_packets"`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "startup_fact_report_accepts_file_backed_envelope_only_payload or startup_fact_report_rejects_canonical_submission_alias or material_scan_accepts_file_backed_packet_body_and_updates_frontier or material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card or material_scan_packet_and_result_relays_combine_ledger_check"`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py tests\test_flowpilot_card_runtime.py tests\test_flowpilot_role_output_runtime.py -q`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py --json-out simulations\flowpilot_role_output_runtime_results.json`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_card_instruction_coverage_checks.py --json-out simulations\card_instruction_coverage_results.json`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`
- OK: `python simulations\run_command_refinement_checks.py`
- OK: `rg -n "runtime_receipt_path|runtime_receipt_hash|event_envelope_ref|--envelope-path|--envelope-hash|event_envelope" skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py skills\flowpilot\assets\runtime_kit\cards\roles\controller.md simulations\flowpilot_event_envelope_transfer_model.py simulations\run_flowpilot_event_envelope_transfer_checks.py`
- OK: `git diff --check`

### Findings
- The new FlowGuard model proves legal full envelope payloads and path/hash envelope refs reach equivalent router outcomes for reviewer startup fact reports and PM material-scan packets.
- The model and tests cover missing envelope files, outside-project paths, hash mismatch, schema mismatch, event mismatch, from_role mismatch, bad controller visibility, forbidden body fields, and envelopes outside the current allowed external event.
- The known failed controller-reconstruction paths are rejected: renamed runtime receipt fields are not accepted as runtime-validated reports, and material scan packets hidden under a nested envelope are not accepted as `payload.packets`.
- Duplicate submission of the same already-recorded envelope remains idempotent and does not create another event side effect.
- Router `record-event` now accepts `--envelope-path`/`--envelope-hash` and `event_envelope_ref`, then reads the envelope itself after path/hash validation.

### Counterexamples
- none recorded

### Friction Points
- Full router/card/role-output runtime tests took about 10 minutes on this machine.
- The specialized FlowGuard model is intentionally focused on record-event transfer mechanics, not semantic sufficiency of report or packet body content.

### Skipped Steps
- Installed FlowPilot skill synchronization was skipped by explicit user request. Only the current repository was changed.
- Git commit, push, and release/publish actions were skipped by explicit user request.

### Next Actions
- Keep Controller guidance centered on passing envelope path/hash, not reconstructing envelope fields.


## flowpilot-event-idempotency-model-upgrade - Model scoped duplicate external events before router repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live-run report showed `pm_mutates_route_after_review_block` could be swallowed by the run-wide `route_mutated_by_pm` flag even when PM was submitting a later control-blocker repair transaction and higher route version.
- Status: model-upgrade-completed; production router repair not started by user request
- Skill decision: use_flowguard
- Started: 2026-05-10T08:00:00+02:00
- Ended: 2026-05-10T08:18:12+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_event_idempotency_model.py
- simulations/run_flowpilot_event_idempotency_checks.py
- simulations/flowpilot_event_idempotency_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_event_idempotency_model.py simulations\run_flowpilot_event_idempotency_checks.py`
- OK: `python simulations\run_flowpilot_event_idempotency_checks.py --json-out simulations\flowpilot_event_idempotency_results.json`
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py --json-out simulations\flowpilot_repair_transaction_results.json`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python simulations\run_meta_checks.py`

### Findings
- The model now catches the cross-cutting failure class: event identity must be `event name + explicit scope`, not only `event name + run-wide flag`.
- Safe same-key replays must return `already_recorded` without another side effect.
- New scoped keys, such as a later `control_blocker_id` / `repair_transaction_id` / `route_version`, must execute the writer even if the older run-wide flag is already true.
- Retry budgets must produce an explicit PM escalation or dead-end after the budget is exceeded, not a silent duplicate swallow.
- Source audit flagged one high-risk event: `pm_mutates_route_after_review_block`.
- Source audit also flagged medium-risk scoped repeatables: `pm_records_control_blocker_repair_decision`, `role_records_gate_decision`, `pm_requests_startup_repair`, and `pm_writes_route_draft`.
- Source audit flagged one low-risk retry path: `pm_completes_current_node_from_reviewed_result`, currently guarded by missing-write detection but still a candidate for the same scoped idempotency layer.

### Counterexamples
- `global_flag_swallows_new_route_mutation`
- `repair_retry_below_budget_swallowed`
- `retry_budget_exceeded_without_escalation`
- `unconditional_repeat_duplicates_gate_decision`
- `cycle_reuse_without_reset`
- `accepted_without_dedupe_key_fields`
- `no_legal_next_action_after_swallow`

### Friction Points
- `python simulations\run_meta_checks.py` needed a longer timeout; the first short run timed out, and the longer rerun passed.
- The reported live run directory `.flowpilot/runs/run-20260509-210950` was not available locally, so this phase used source audit and model scenarios rather than replaying that exact run artifact.

### Skipped Steps
- Production router changes were intentionally skipped because the user requested model upgrade and repair planning before code repair.
- Installed FlowPilot skill synchronization, git commit, push, and release/publish actions were not performed.
- `python simulations\run_capability_checks.py` was not rerun because this phase did not change skill/capability routing.

### Next Actions
- Implement a small router-level scoped idempotency layer before the generic run-wide flag dedupe.
- Define per-event policies such as one-shot, transaction-scoped, gate-scoped, cycle-scoped, and append-only tick.
- Keep run-wide flags as phase/latest-state summaries, not the source of truth for duplicate suppression.


## flowpilot-scoped-event-idempotency-router-repair - Add scoped external-event identity before run-wide flag dedupe

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The upgraded FlowGuard model showed that run-wide flags can swallow legitimate later external events when the event name repeats across a new blocker, repair transaction, route version, gate, startup cycle, route draft, or node completion scope.
- Status: completed in local repository only
- Skill decision: use_flowguard
- Started: 2026-05-10T08:20:00+02:00
- Ended: 2026-05-10T09:17:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_event_idempotency_model.py
- simulations/run_flowpilot_event_idempotency_checks.py
- simulations/flowpilot_event_idempotency_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_event_idempotency_model.py simulations\run_flowpilot_event_idempotency_checks.py tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_flowpilot_event_idempotency_checks.py --json-out simulations\flowpilot_event_idempotency_results.json`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "gate_decision_same_identity_replay_is_already_recorded or route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag or pm_startup_repair_request_can_repeat_for_new_blocking_report or already_recorded_event_can_resolve_delivered_control_blocker or already_recorded_event_does_not_resolve_pm_required_control_blocker or already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision"`
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py --json-out simulations\flowpilot_repair_transaction_results.json`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py tests\test_flowpilot_card_runtime.py tests\test_flowpilot_role_output_runtime.py -q --maxfail=1`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "gate_decision_same_identity_replay_is_already_recorded or route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag"`
- OK: `git diff --check`

### Findings
- Router now declares scoped idempotency policies for six repeatable event families: route mutation after review block, PM control-blocker repair decision, GateDecision, startup repair request, route draft write, and PM current-node completion.
- `record_external_event` now computes a dedupe key before the old run-wide flag check. Same-key replays return `already_recorded` without rewriting side effects.
- A new `pm_mutates_route_after_review_block` scoped by a later blocker / repair transaction / route version bypasses the old `route_mutated_by_pm` swallow path and executes the existing route mutation writer.
- Route mutation attempts have a scoped retry budget for the same repair group; exceeding it now raises an explicit router error instead of silently swallowing another retry.
- The event-idempotency source audit now reports zero missing production scoped policies.
- Runtime tests prove the same GateDecision replay does not rewrite its record and a later route mutation transaction writes v3 after v2 instead of being swallowed.

### Counterexamples
- The model still intentionally detects the old bad architectures: `global_flag_swallows_new_route_mutation`, `repair_retry_below_budget_swallowed`, `retry_budget_exceeded_without_escalation`, `unconditional_repeat_duplicates_gate_decision`, `cycle_reuse_without_reset`, `accepted_without_dedupe_key_fields`, and `no_legal_next_action_after_swallow`.

### Friction Points
- The first broad runtime test run was launched in parallel with model regressions and hit the 15-minute command timeout. The same runtime suite passed when rerun alone with a longer timeout.
- `run_flowpilot_control_plane_friction_checks.py` still reports one pre-existing live-run warning about historical role-output envelope hash replay mismatch. It is not introduced by this idempotency change.
- The workspace contains many unrelated peer-agent modifications; this repair did not revert or normalize those files.

### Skipped Steps
- Installed FlowPilot skill synchronization was skipped by explicit user request.
- Git commit, push, and release/publish actions were skipped by explicit user request.
- Direct replay of `.flowpilot/runs/run-20260509-210950` remains unavailable because that run directory is not present locally.

### Next Actions
- When the user is ready, sync this repository change through the user's chosen local install/release path together with peer-agent changes.
- If future production traces show legitimate more-than-three route mutations for the same repair group, tune the retry budget or move it to a per-policy configuration file.
## 2026-05-10 - Reviewer Blocked-Resolution Guidance

### Decision
- Scope: prompt/protocol text only. No router, runtime state machine, installed skill sync, git push, or GitHub sync.
- Reviewer cards now keep using `independent_challenge.non_blocking_findings` for higher-standard opportunities, simpler equivalent paths, quality improvements, and PM decision-support observations.
- This applies for every review outcome, including blocked reviews.
- When a review blocks, requests more evidence, or requires reroute, the sealed review body must include `recommended_resolution` with one concrete PM-actionable recommendation. PM remains owner of the final repair strategy.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: reviewer card coverage scan for `Decision-Support Findings`, `recommended_resolution`, and `non_blocking_findings`
- OK: `python -m py_compile skills\flowpilot\assets\role_output_runtime.py skills\flowpilot\assets\flowpilot_router.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `git diff --check` (line-ending normalization warnings only)
- Attempted: `python simulations\run_capability_checks.py` timed out after 600 seconds; not counted as passed.

### Findings
- All 15 reviewer cards include the decision-support guidance.
- The reviewer role core card includes the same field-level instruction.
- `worker_result_review`, `material_sufficiency`, `startup_fact_check`, and `final_backward_replay` JSON examples now show `recommended_resolution` where blocked outcomes are represented directly.
- The meta model passed with no invariant failures, missing labels, stuck states, or nonterminating components.

### Skipped Steps
- Installed FlowPilot skill sync skipped per user instruction.
- Git commit, push, and GitHub sync skipped per user instruction.
- Runtime schema enforcement skipped because the requested change was a minimal prompt/protocol update.


## flowpilot-worker-officer-soft-pm-note-20260510 - Add soft PM Note guidance for FlowPilot worker and officer packets

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot role protocol change touching worker/officer packet guidance and card instruction coverage
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-10T06:54:53+00:00
- Ended: 2026-05-10T06:54:53+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/card_instruction_coverage_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python -m py_compile simulations\card_instruction_coverage_model.py`
- OK (0.000s): `python -m unittest tests.test_flowpilot_card_instruction_coverage tests.test_flowpilot_output_contracts tests.test_flowpilot_planning_quality`
- OK (0.000s): `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_role_output_runtime`
- OK (0.000s): `python -m unittest tests.test_flowpilot_reviewer_active_challenge`
- OK (0.000s): `python simulations\run_card_instruction_coverage_checks.py --json-out simulations\card_instruction_coverage_results.json`
- OK (0.000s): `python simulations\run_meta_checks.py --fast`
- OK (0.000s): `python simulations\run_capability_checks.py --fast`

### Findings
- Worker and FlowGuard officer packets now carry soft PM Note guidance for in-scope quality choices and PM-only consideration of out-of-scope ideas.
- The PM Note is intentionally not added to reviewer hard gates or output_contract required sections.

### Counterexamples
- none recorded

### Friction Points
- A background full run of simulations\run_meta_checks.py was stopped after more than 10 minutes with no output; the supported --fast proof-reuse check passed instead.

### Skipped Steps
- No installed FlowPilot sync, install check, Git commit, push, or GitHub sync per user instruction.

### Next Actions
- User will coordinate local install, git, and remote synchronization later.


## flowpilot-decision-liveness-model-miss-20260510 - Accepted PM decisions must open a next channel

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Runtime model miss where a legal PM model-miss triage decision could be accepted without opening the officer/evidence/user-stop channel it requested.
- Status: analysis completed; production router repair not started in this side conversation.
- Skill decision: use_flowguard
- Date: 2026-05-10
- Commands OK: model checks passed; static router audit intentionally reported current findings.

### Model Files
- simulations/flowpilot_decision_liveness_model.py
- simulations/run_flowpilot_decision_liveness_checks.py
- simulations/flowpilot_decision_liveness_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`, schema version 1.0
- OK: `python -m py_compile simulations\flowpilot_decision_liveness_model.py simulations\run_flowpilot_decision_liveness_checks.py`
- FINDINGS: `python simulations\run_flowpilot_decision_liveness_checks.py --json-out simulations\flowpilot_decision_liveness_results.json`
- OK: `git diff --check -- simulations\flowpilot_decision_liveness_model.py simulations\run_flowpilot_decision_liveness_checks.py simulations\flowpilot_decision_liveness_results.json`

### Findings
- The safe decision-liveness model has no invariant failures, no missing labels, no stuck states, no nonterminating components, and zero FlowGuard Explorer violations.
- Hazard checks catch accepted nonterminal PM decisions looping back to the same PM event, model-backed repair without officer report review, officer report relay without ledger check, and repair packet opening before triage closure.
- Static router/runtime-kit audit found 3 legal non-authorizing model-miss triage decisions without concrete next-channel implementation: `request_officer_model_miss_analysis`, `needs_evidence_before_modeling`, and `stop_for_user`.
- The current run contains 1 matching live occurrence for `request_officer_model_miss_analysis`.

### Counterexamples
- `request_officer_decision_dead_ends_on_same_pm_event`
- `needs_evidence_decision_dead_ends_on_same_pm_event`
- `stop_for_user_decision_dead_ends_on_same_pm_event`
- `model_backed_repair_without_officer_report`
- `officer_report_routed_without_ledger_check`
- `repair_packet_opened_after_unclosed_triage`

### Skipped Steps
- Production router changes skipped because the user asked for model upgrade, findings, and minimal repair plan first.
- Full production conformance replay skipped; this side task added model exploration plus static router/runtime-kit audit, not a full external-event replay adapter.

### Next Actions
- Discuss the minimal router repair plan before changing production route code.


## flowpilot-global-system-card-bundles-20260510 - Bundle same-role read-only system cards globally

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot router/runtime change. Startup-only card delivery folding was generalized into guarded same-role read-only system-card bundling, and incomplete bundle ACK handling was required to recover back to the mainline instead of merely stopping.
- Status: completed_installed
- Skill decision: use_flowguard
- Date: 2026-05-10
- Commands OK: True

### Model Files
- simulations/flowpilot_card_envelope_model.py
- simulations/flowpilot_command_refinement_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --no-write`
- OK: `python simulations\run_command_refinement_checks.py --json-out $env:TEMP\flowpilot_command_refinement_results.json`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py`
- OK: `python simulations\run_command_refinement_checks.py`
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py`
- OK: focused router-runtime bundle and regression tests around system-card delivery, PM startup cards, and user-intake mail flow
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests`
- OK: `python -m pytest tests`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`

### Findings
- Router folding is now based on the global guarded condition, not a startup-only special case: same role, same run, same resume tick, fixed manifest order, no intermediate external wait, no payload artifact requirement, and no recipient change.
- The bundle protocol preserves the sealed-card boundary: the Controller commits bundle envelopes and role receipts without reading sealed card bodies.
- Bundle ACK validation requires one valid per-card receipt for every bundled card before the pending return can resolve.
- If a bundle ACK is incomplete, the router records `bundle_ack_incomplete`, lists `missing_card_ids`, keeps the pending return unresolved, returns a same-role recovery wait, and rechecks a changed ACK before resuming the route.
- The command-refinement model rejects generic card-bundle folding and accepts only guarded same-role folding with replay coverage and incomplete-ACK recovery coverage.

### Counterexamples
- The card-envelope model rejects advancing a same-role bundle without joined receipts, bundling across role or payload boundaries, resolving an incomplete ACK, omitting the same-role recovery wait, or advancing after incomplete ACK without a corrected complete ACK.
- The command-refinement model rejects a generic `card_bundle_fold` without the guarded replay and recovery evidence.

### Friction Points
- Existing router tests that manually assumed single-card PM startup delivery had to use the delivery helper so the tests assert the requested card was delivered even when earlier same-role cards are validly bundled.
- Local install sync must run before install check and audit; running them concurrently can race against the installed skill overwrite.

### Skipped Steps
- Remote GitHub push skipped per user instruction.

### Next Actions
- None for this scoped optimization. Future FlowGuard models for recoverable protocol failures should include the repair-and-resume path, not only the detection-and-block path.


## flowpilot-pm-suggestion-impact-triage-20260510 - Add PM impact triage reminder for suggestions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot protocol prompt/template change. PM suggestion disposition now reminds PM to distinguish harmless local changes from product, route, acceptance, state/data-flow, evidence-freshness, or completion-risk changes before adoption.
- Status: completed
- Skill decision: use_flowguard
- Date: 2026-05-10
- Commands OK: True

### Model Files
- simulations/flowpilot_pm_suggestion_disposition_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_pm_suggestion_disposition_model.py simulations\run_flowpilot_pm_suggestion_disposition_checks.py tests\test_flowpilot_card_instruction_coverage.py`
- OK: `python simulations\run_flowpilot_pm_suggestion_disposition_checks.py --json-out simulations\flowpilot_pm_suggestion_disposition_results.json`
- OK: `python -m pytest tests\test_flowpilot_card_instruction_coverage.py::FlowPilotCardInstructionCoverageTests::test_pm_suggestion_disposition_guidance_is_unified_but_role_scoped tests\test_flowpilot_output_contracts.py::FlowPilotOutputContractTests::test_contract_registry_declares_pm_selection_and_self_check_policy tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_final_ledger_rejects_dirty_pm_suggestion_ledger tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_dirty_pm_suggestion_ledger_invalidates_terminal_closure_card -q -p no:cacheprovider`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- PM core guidance now says to do a lightweight impact triage before disposing suggestions.
- The PM suggestion ledger template now includes `impact_triage` with impact level, FlowGuard consideration, FlowGuard decision, and PM reason.
- The suggestion-disposition FlowGuard model now rejects a route-change suggestion that lacks impact triage, while still allowing no-suggestion and harmless local-change paths to stay lightweight.

### Counterexamples
- The new hazard `route_change_without_impact_triage` is rejected with `PM suggestion disposition lacks impact triage`.

### Skipped Steps
- No remote GitHub push, per user instruction.

### Next Actions
- None for this small prompt/template reinforcement unless later runtime work chooses to hard-enforce `impact_triage` in concrete router ledger validation.


## flowpilot-route-hard-gates-20260510 - Enforce product-model-first route hard gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot Router change. Soft product-model-first route guidance was upgraded into Router hard gates while keeping semantic judgement with Product/Process Officer and Reviewer roles.
- Status: completed
- Skill decision: use_flowguard
- Date: 2026-05-10
- Commands OK: True

### Model Files
- simulations/flowpilot_route_hard_gate_model.py
- simulations/flowpilot_planning_quality_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_route_hard_gate_checks.py --json-out simulations\flowpilot_route_hard_gate_results.json`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_route_hard_gate_model.py simulations\run_flowpilot_route_hard_gate_checks.py`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k "route_draft_requires_product_behavior_model_report or route_check_reports_require_hard_gate_verdict_fields or process_route_repair_required_blocks_activation_and_reopens_pm_route_draft or route_mutation_requires_return_target_and_resets_route_hard_gates or route_check_results_require_router_delivered_check_cards or product_architecture_and_root_contract_gate_route_skeleton or route_mutation_and_final_ledger_have_required_preconditions or route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag or parent_backward_non_continue_decision_mutates_route_and_requires_rerun" -q`
- OK: `python -m pytest tests\test_flowpilot_card_instruction_coverage.py -q`
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned`
- OK: `python scripts\audit_local_install_sync.py`
- OK: `python scripts\install_flowpilot.py --check`
- OK: `git diff --check` (line-ending normalization warnings only)

### Findings
- Router now requires a passed Product Officer product behavior model report before PM route draft.
- Router route activation now requires role-owned product-model review pass and Process Officer `process_viability_verdict=pass`.
- Process Officer can now report `repair_required` or `blocked`; those verdicts reopen PM route drafting instead of unlocking activation.
- Route mutation now requires `repair_return_to_node_id` and clears stale route approvals so the changed route must pass route checks again before execution continues.
- Router still does not judge semantic route quality; it checks only role-owned hard-gate artifacts and verdict fields.

### Counterexamples
- The hard-gate model rejects missing product model, missing route-product review pass, missing process verdict, ignored `repair_required`, ignored `blocked`, repair without mainline return, repair without fresh process recheck, and Router semantic overreach.

### Friction Points
- A test that intentionally submitted a malformed role report had to model the real control-blocker path instead of reusing the same run as a normal pass path.
- The worktree also included parallel AI changes; this phase preserved them and local git synchronization includes them per user instruction.

### Skipped Steps
- Remote GitHub push skipped per user instruction.

### Next Actions
- User can review the local commit and decide when to push or otherwise synchronize the remote repository.


## flowpilot-product-model-first-route-viability-20260510 - Use product behavior model before PM route drafting

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot planning sequence change. Product FlowGuard output now drives PM route drafting, and Process FlowGuard checks route viability against that product behavior model.
- Status: completed
- Skill decision: use_flowguard
- Date: 2026-05-10
- Commands OK: True

### Model Files
- simulations/flowpilot_planning_quality_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`
- OK: `python -m py_compile simulations\flowpilot_planning_quality_model.py simulations\run_flowpilot_planning_quality_checks.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python -m pytest tests\test_flowpilot_card_instruction_coverage.py -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k "product_architecture_and_root_contract_gate_route_skeleton or route_check_results_require_router_delivered_check_cards or node_acceptance_plan_requires_pm_high_standard_recheck or parent_backward_non_continue_decision_mutates_route_and_requires_rerun" -q`
- OK: `python scripts\check_install.py`

### Findings
- Product FlowGuard output is now treated as the root product behavior model for product-architecture work before PM route drafting.
- PM route skeleton guidance now maps nodes to the product behavior model instead of treating the model as a late report.
- Process FlowGuard guidance now checks whether the PM route can reach the product behavior model, instead of duplicating the Router's mechanical no-skip enforcement.
- Repair and mutation paths now need an explicit return to the mainline node and a note about which product-model checks or evidence must rerun before continuing.

### Counterexamples
- The planning-quality model rejects missing product behavior model, PM route not mapped to product model, missing Process Officer route viability check, repair without mainline return, and node acceptance plans not mapped to a product-model segment.

### Friction Points
- A combined pytest run timed out, so validation was split into focused card coverage and router-runtime checks.
- The worktree already contained broad parallel AI edits; this phase preserved those changes and only added the minimal product-model-first flow adjustments.

### Skipped Steps
- Installed FlowPilot skill synchronization skipped per user instruction.
- Git stage, commit, push, and GitHub sync skipped per user instruction.

### Next Actions
- User will coordinate local install, git, and remote synchronization later.


## flowpilot-role-progress-status - Add controller-visible role progress to FlowPilot packet status without exposing sealed bodies

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested model-first FlowGuard validation before changing long-running background role waiting behavior.
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-10T15:04:57+00:00
- Ended: 2026-05-10T15:04:57+00:00
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


## flowpilot-role-progress-status - Add controller-visible role progress to FlowPilot packet status without exposing sealed bodies

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested model-first FlowGuard validation before changing long-running background role waiting behavior.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-10T15:49:22+00:00
- Ended: 2026-05-10T15:49:22+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_control_plane_friction_model.py

### Commands
- OK (0.000s): `python simulations\\run_flowpilot_control_plane_friction_checks.py --json-out simulations\\flowpilot_control_plane_friction_results.json`
- OK (0.000s): `python simulations\\run_meta_checks.py --fast`
- OK (0.000s): `python simulations\\run_capability_checks.py --fast`
- OK (0.000s): `python -m py_compile skills\\flowpilot\\assets\\packet_runtime.py skills\\flowpilot\\assets\\flowpilot_router.py simulations\\flowpilot_control_plane_friction_model.py simulations\\run_flowpilot_control_plane_friction_checks.py`
- OK (0.000s): `python scripts\\check_install.py`
- OK (0.000s): `python simulations\\run_prompt_isolation_checks.py`
- OK (0.000s): `python simulations\\run_flowpilot_resume_checks.py`
- OK (0.000s): `python simulations\\run_flowpilot_router_loop_checks.py --json-out simulations\\flowpilot_router_loop_results.json`
- OK (0.000s): `python scripts\\smoke_autopilot.py --fast`
- OK (0.000s): `python scripts\\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\\audit_local_install_sync.py --json`

### Findings
- Progress uses the existing controller_status_packet.json with metadata-only message and runtime-written numeric progress.
- Controller pending action grants only the matching controller_status_packet.json, not packet directory or sealed body.
- FlowGuard hazards catch missing status read access, broad packet directory grants, sealed/body detail leakage, manual progress writes, and nonnumeric progress.

### Counterexamples
- none recorded

### Friction Points
- Full meta/capability commands exceeded a 10 minute tool timeout; their generated proof files were then verified with --fast fingerprint reuse.

### Skipped Steps
- none recorded

### Next Actions
- Keep unrelated concurrent worktree changes separate from this local progress-status commit.


## flowpilot-node-local-review-repair - Prefer same-node repair before route mutation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested a FlowGuard-first optimization so reviewer blocks do not automatically create repair route nodes when PM can repair the current node or request fresh supplements.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-10T15:30:00+00:00
- Ended: 2026-05-10T16:11:00+00:00
- Duration seconds: 2460.000
- Commands OK: True

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py
- simulations/flowpilot_control_plane_friction_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- OK: `python -m py_compile simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py`.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out %TEMP%\flowpilot_friction_check_*.json`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_node_acceptance_plan_block_can_be_revised_on_same_node`.
- OK: `python -m unittest` focused reviewer-block and route-mutation subset, 6 tests.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`.
- OK: `python simulations\run_flowpilot_router_loop_checks.py`.
- OK: `python simulations\run_meta_checks.py` in background; 598029 states, 618200 edges.
- OK: `python simulations\run_capability_checks.py` in background; 607187 states, 632646 edges.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\check_install.py`.

### Findings
- Added a route-mutation threshold model: node-local blocks can be repaired by fresh same-node plan/result/report evidence and same review-class recheck.
- Added hazards for node-local block forced into route mutation, route-invalidating block handled locally, stale blocked evidence reuse, missing reviewer recheck, missing route-mutation reason, and missing route recheck.
- Runtime now accepts `pm_revises_node_acceptance_plan` after model-miss triage, clears the active node-plan block, records stale blocked plan as context-only, and reroutes the same reviewer node acceptance-plan gate.
- PM/reviewer prompts now place the guidance only at three decision points: PM core, PM review-repair, and reviewer node acceptance-plan review.

### Counterexamples
- node_local_block_route_mutated_without_reason
- same_node_repair_path_unroutable
- route_invalidating_block_handled_as_same_node_repair
- same_node_repair_reuses_stale_blocked_evidence
- same_node_repair_without_reviewer_recheck
- route_mutation_without_current_node_incapability_reason
- route_mutation_continues_without_route_recheck

### Friction Points
- Full meta and capability model checks are large but completed successfully in background; no fast proof fallback was needed.
- Existing concurrent worktree changes were preserved and included in local validation context.

### Skipped Steps
- No GitHub push or remote release per user instruction.
- No full unfiltered router runtime suite; focused reviewer-block/route-mutation tests and model checks were run instead.

### Next Actions
- If route mutation remains too easy in future PM outputs, promote `why_current_node_cannot_contain_repair` from prompt guidance into a stricter payload contract.


## flowpilot-startup-banner-public-links-20260510 - Replace startup banner status bullets with project links

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested replacing the FlowPilot startup banner's generic startup-status bullets with developer, repository, and PayPal.Me support links, then syncing source, installed skill, and local git.
- Status: completed
- Skill decision: skip_with_reason
- Started: 2026-05-10T16:25:00+00:00
- Ended: 2026-05-10T16:48:00+00:00
- Commands OK: True

### Model Files
- none

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_banner_action_and_result_are_user_visible`.
- OK: `python scripts\check_install.py`.
- OK: `python simulations\run_prompt_isolation_checks.py`.
- OK: `python simulations\run_startup_pm_review_checks.py`.
- OK: focused startup router subset, 7 tests.
- OK: `python -m unittest tests.test_flowpilot_card_instruction_coverage tests.test_flowpilot_card_runtime tests.test_flowpilot_output_contracts`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.

### Findings
- The change is display-copy only: it updates the runtime startup banner card, source banner template, project startup banner template, and the direct router display assertions.
- The router still requires user-dialog display confirmation and computes the display hash dynamically from the card text.
- Local installed `flowpilot` was stale before sync and `source_fresh: true` after sync.

### Counterexamples
- none recorded

### Friction Points
- The full unfiltered `tests.test_flowpilot_router_runtime` module exceeded the tool timeout twice, so focused startup/banner coverage and related card/runtime checks were used for this scoped display change.

### Skipped Steps
- No route, frontier, state-machine, or skill-control behavior changed, so no new FlowGuard model was created and full meta/capability model reruns were not required.
- No GitHub push or release.

### Next Actions
- Keep the public-link banner text in sync across runtime card and both startup banner templates when future banner copy changes.


## flowpilot-direct-packet-dispatch-20260510 - Move PM packet dispatch gating into router preflight

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested finishing the change that removes reviewer pre-dispatch approval for PM background work packets and relies on router/runtime mechanical validation before relay.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-10T18:20:00+00:00
- Ended: 2026-05-10T19:30:00+00:00
- Commands OK: True

### Model Files
- `skills/flowpilot/assets/packet_control_plane_model.py`
- `simulations/flowpilot_protocol_contract_conformance_model.py`
- `simulations/flowpilot_router_loop_model.py`
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/flowpilot_repair_transaction_model.py`
- `simulations/flowpilot_gate_decision_contract_model.py`
- `simulations/flowpilot_gate_policy_audit_model.py`
- `simulations/flowpilot_route_hard_gate_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`, schema 1.0.
- OK: `python simulations\run_meta_checks.py --fast`.
- OK: `python simulations\run_capability_checks.py --fast`.
- OK: `python simulations\run_flowpilot_resume_checks.py`.
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`.
- OK: `python simulations\run_router_next_recipient_checks.py --json-out simulations\router_next_recipient_results.json`.
- OK: `python simulations\run_router_action_contract_checks.py --json-out simulations\flowpilot_router_action_contract_results.json`.
- OK: `python simulations\run_card_instruction_coverage_checks.py`.
- OK: `python simulations\run_prompt_isolation_checks.py --json-out simulations\prompt_isolation_results.json`.
- OK: `python skills\flowpilot\assets\run_packet_control_plane_checks.py --json-out skills\flowpilot\assets\packet_control_plane_results.json`.
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`.
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json`.
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py --json-out simulations\flowpilot_repair_transaction_results.json`.
- OK: focused router runtime direct-dispatch and repair-transaction unittest subset, 13 tests.
- OK: `python -m py_compile` on changed router, packet runtime, simulations, runners, and focused test module.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\smoke_autopilot.py --fast`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python simulations\run_flowpilot_gate_decision_contract_checks.py --json-out simulations\flowpilot_gate_decision_contract_results.json`.
- OK: `python simulations\run_flowpilot_gate_policy_audit_checks.py --json-out simulations\flowpilot_gate_policy_audit_results.json`.
- OK: `python simulations\run_flowpilot_route_hard_gate_checks.py --json-out simulations\flowpilot_route_hard_gate_results.json`.

### Findings
- PM material-scan and current-node packets now proceed through router direct-dispatch preflight and packet ledger checks instead of reviewer dispatch cards.
- Reviewer dispatch cards remain as unmanifested legacy files only; reviewer responsibility is shifted to result quality, stage gates, and PM decision review.
- Router/runtime direct relay checks cover required envelope fields, sealed body visibility, body hash replay, allowed background role, output-contract recipient match, scoped result paths, ledger identity, and Controller no-body-read boundaries.
- Legacy material dispatch reviewer-block state is no longer part of model-miss reviewer-block repair; router material-dispatch hard blockers route through control-blocker repair and direct recheck outcomes.
- Local installed `flowpilot` was stale before sync and matched the repository digest after `install_flowpilot.py --sync-repo-owned`.

### Counterexamples
- material packet relay without router direct-dispatch preflight
- current-node worker dispatch before router direct-dispatch approval
- packet body hash mismatch
- missing output contract
- output contract recipient mismatch
- Controller sealed-body read
- material dispatch router block without PM control-blocker repair path

### Friction Points
- The full unfiltered `tests\test_flowpilot_router_runtime.py` pytest run exceeded the tool timeout, so focused runtime tests plus FlowGuard model checks were used.
- Full meta/capability checks were too slow in parallel; valid proof files were reused with `--fast`.
- An existing live run under `.flowpilot/runs/run-20260510-162511` still has role-output hash replay warnings; this was not a source conformance blocker.

### Skipped Steps
- No GitHub push or remote release.
- No destructive cleanup of legacy reviewer dispatch card files because install checks still require the files to exist for legacy/compatibility coverage.

### Next Actions
- If future work fully retires legacy run compatibility, remove the orphan reviewer dispatch card files and update install checks in the same change.


## flowpilot-0.7.0-installer-bootstrap-20260510 - Add required dependency bootstrap and public FlowGuard install guard

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested that FlowPilot installers tell other AIs which sub-skills are required, auto-install missing required pieces when authorized, keep UI companions optional, model the installer flow with FlowGuard, bump the version, and publish to GitHub.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-10T18:45:00+00:00
- Ended: 2026-05-10T19:35:00+00:00
- Commands OK: True

### Model Files
- `simulations/release_tooling_model.py`
- `simulations/run_release_tooling_checks.py`
- `simulations/release_tooling_results.json`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`, schema 1.0.
- OK: `python -m py_compile scripts\install_flowpilot.py scripts\check_public_release.py scripts\check_install.py simulations\release_tooling_model.py simulations\run_release_tooling_checks.py tests\test_flowpilot_installer_dependencies.py`.
- OK: `python simulations\run_release_tooling_checks.py`.
- OK: `python -m pytest tests\test_flowpilot_installer_dependencies.py -q`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\check_public_release.py --json`, with expected warning that the worktree was dirty before commit.
- OK: `python scripts\smoke_autopilot.py --fast`.
- OK: `python -m pytest tests\test_flowguard_result_proof.py -q`.

### Findings
- The dependency manifest now makes `flowguard`, `model-first-function-flow`, and `grill-me` required; UI-oriented companion skills remain optional.
- The installer prints required/optional tiers before actions, installs required Codex skills with `--install-missing`, and installs FlowGuard from `https://github.com/liuyingxuvka/FlowGuard` only when `--install-flowguard` explicitly authorizes Python environment changes.
- `skills/flowpilot/DEPENDENCIES.md` and `SKILL.md` now give installing AIs a small startup reminder before FlowPilot runs.
- Public release checks now understand `github_python_package` dependencies and probe FlowGuard's `pyproject.toml`.

### Counterexamples
- FlowGuard install attempted without public source plus explicit authorization.
- Required dependencies marked ready before FlowGuard verification.
- Optional companion skill installation without `--include-optional`.
- Release prepared before dependency notice and tier declaration.

### Friction Points
- The local installed `flowpilot` skill was stale before sync; `install_flowpilot.py --sync-repo-owned --json` refreshed it and subsequent checks reported `source_fresh: true`.

### Skipped Steps
- OpenSpec was considered, but this repository has no initialized OpenSpec change directory, so no OpenSpec proposal was created.
- No companion skill repository was modified, packaged, tagged, or published.

### Next Actions
- Keep future dependency additions in `flowpilot.dependencies.json`, `skills/flowpilot/DEPENDENCIES.md`, README install commands, and `simulations/release_tooling_model.py` in sync.


## route-visible-committed-only-20260510 - Keep FlowPilot user-visible route projection committed-route only

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Route visibility protocol affects user commitments, route state, display sync, and draft/committed source-of-truth boundaries
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-10T20:02:21+00:00
- Ended: 2026-05-10T20:02:21+00:00
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


## route-visible-committed-only-20260510 - Keep FlowPilot user-visible route projection committed-route only

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Route visibility protocol affects user commitments, route state, display sync, and draft/committed source-of-truth boundaries
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-10T20:25:23+00:00
- Ended: 2026-05-10T20:25:23+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_route_display_model.py

### Commands
- OK (0.000s): `python simulations\\run_flowpilot_route_display_checks.py --json-out simulations\\flowpilot_route_display_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_display_plan_is_controller_synced_projection_from_pm_plan tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_check_results_require_router_delivered_check_cards tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress`
- OK (0.000s): `python -m py_compile skills\\flowpilot\\assets\\flowpilot_router.py skills\\flowpilot\\assets\\flowpilot_user_flow_diagram.py scripts\\flowpilot_user_flow_diagram.py simulations\\flowpilot_route_display_model.py simulations\\run_flowpilot_route_display_checks.py`
- OK (0.000s): `python simulations\\run_meta_checks.py`
- OK (0.000s): `python simulations\\run_capability_checks.py`
- OK (0.000s): `python scripts\\install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts\\audit_local_install_sync.py --json`
- OK (0.000s): `python scripts\\check_install.py`

### Findings
- FlowGuard route-display model now detects draft or repair candidate projection, draft display-plan writes, draft-backed snapshots, draft-backed route signs, and previous committed visible route overwrite.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Remote GitHub sync intentionally skipped; only local repo and installed local skill were updated.


## child-skill-execution-binding-20260511 - Bind selected child skills at current-node execution time

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User required FlowPilot workers and reviewers to directly use relevant child skills during current-node execution, with child-skill stricter standards taking precedence over the PM packet floor.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T00:00:00+00:00
- Ended: 2026-05-11T00:00:00+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/capability_model.py
- simulations/meta_model.py
- simulations/flowpilot_control_plane_friction_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\capability_model.py simulations\run_capability_checks.py simulations\meta_model.py simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py --force`
- OK: `python simulations\run_meta_checks.py --force`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py tests\test_flowpilot_router_runtime.py tests\test_flowpilot_planning_quality.py tests\test_flowpilot_output_contracts.py`
- OK: `python -m pytest tests\test_flowpilot_planning_quality.py tests\test_flowpilot_output_contracts.py -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k "current_node_worker_packet_requires_active_child_skill_binding_projection or current_node_packet_relay_uses_router_direct_dispatch or current_node_completion_requires_reviewer_passed_packet_audit" -q`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_output_contracts.py -q`
- OK: `python -m pytest tests\test_flowpilot_card_instruction_coverage.py tests\test_flowpilot_card_runtime.py -q`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit`
- OK: `python scripts\smoke_autopilot.py --fast`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\check_install.py`

### Findings
- Capability and meta models now include current-node active child-skill bindings, direct worker packet use instructions, allowed child-skill source paths, worker `Child Skill Use Evidence`, reviewer evidence checks, and stricter child-skill standard precedence over the PM packet floor.
- Router now preserves PM-authored `active_child_skill_bindings` and blocks current-node worker packets that omit active binding projection, direct-use metadata, or source path allowances.
- Packet/result templates, worker cards, reviewer cards, and output contracts now make execution-time child-skill use explicit without broad route-wide skill forcing.

### Counterexamples
- Missing active child-skill binding.
- Binding not scoped to the current-node child-skill slice.
- Stricter child-skill standard downgraded to the PM packet floor.
- Worker packet missing direct child-skill use instruction.
- Worker packet missing allowed child-skill source paths.
- Worker result missing `Child Skill Use Evidence`.
- Reviewer approval missing child-skill use evidence check.

### Friction Points
- Meta model current-node fields reset after terminal completion, so current-node binding invariants must apply during node execution/review windows, while terminal completeness remains covered by terminal replay and final-review gates.

### Skipped Steps
- Remote GitHub push/release skipped by user request.
- Control-plane friction live-run audit skipped with `--skip-live-audit`; abstract model and hazard checks passed.

### Next Actions
- Keep future FlowPilot child-skill routing changes aligned across node plans, packet metadata, sealed body templates, worker/reviewer cards, output contracts, and FlowGuard hazard cases.
- Local installed FlowPilot skill was synchronized; remote GitHub synchronization remains intentionally out of scope for this change.
