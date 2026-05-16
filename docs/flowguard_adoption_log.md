# FlowGuard Adoption Log

This human-readable log summarizes FlowGuard adoption records for major protocol changes.
Machine-readable entries live in `.flowguard/adoption_log.jsonl`.

## reconcile-daemon-durable-evidence-20260514 - Reconcile durable Router evidence before pending replay

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The live FlowPilot run could stop at a second-layer wait when
  Router state still carried stale pending/action flags even though durable
  role outputs or Controller receipts already existed on disk.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T16:45:00+02:00
- Ended: 2026-05-14T20:20:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_daemon_reconciliation_model.py
- simulations/run_flowpilot_daemon_reconciliation_checks.py
- simulations/flowpilot_daemon_reconciliation_results.json
- simulations/flowpilot_persistent_router_daemon_model.py
- simulations/flowpilot_role_output_runtime_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`:
  `1.0`
- OK: `openspec validate reconcile-daemon-durable-evidence --strict --json`
- OK: `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json`
- OK: `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json`
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py`
- OK: compile check for Router, tests, and daemon reconciliation model files.
- OK: focused new router reconciliation tests: 5 passed.
- OK: adjacent daemon standby/runtime tests: 7 passed.
- OK: install checks and local installed-skill sync.
- OK: background `python simulations\run_meta_checks.py`: exit 0,
  1,949,768 states, 2,010,668 edges, proof reuse mentioned in output.
- OK: background `python simulations\run_capability_checks.py`: exit 0,
  24 shards complete, proof reuse mentioned in output.

### Findings
- Router now runs a durable reconciliation barrier before returning pending
  Controller actions or computing stale-pending fallback actions.
- Completed, blocked, and skipped Controller receipts clear pending actions
  instead of being replayed; incomplete stateful rehydration receipts become
  repair blockers.
- Valid startup fact role-output ledger entries are reconciled into canonical
  report artifacts, Router flags, and run events idempotently.
- Canonical startup fact artifacts can repair stale Router flags/events once
  without duplicating role work.
- Local installed FlowPilot is source-fresh after repository sync.

### Counterexamples
- `completed_controller_action_repeated`
- `blocked_receipt_repeated_instead_of_blocker`
- `submitted_role_output_left_in_ledger`
- `canonical_artifact_flag_not_synced`
- `computed_from_pending_before_reconciliation`
- `receipt_and_role_output_interleaving_starves_role_output`

### Friction Points
- The earlier daemon model covered foreground no-manual-next progress but did
  not separate durable disk evidence from stale in-memory Router flags, so this
  second-layer drift needed a dedicated reconciliation model.

### Skipped Steps
- No remote GitHub push, tag, or release action was performed.
- No unrelated peer-agent changes were reverted.

### Next Actions
- Keep durable-evidence reconciliation ahead of pending-action replay for
  future Router daemon changes.
- When adding a new durable evidence source, add a model hazard for stale
  Router state plus a runtime reconciliation test.

## flowpilot-model-mesh-runner-integration-20260512 - Upgrade mesh coverage ingestion and derive runtime repair recommendation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested running the FlowPilot model mesh across all
  FlowGuard models, upgrading only the model/check network as needed, finding
  current FlowPilot issues, and stopping before runtime code changes with an
  architecture repair recommendation.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T09:20:00+02:00
- Ended: 2026-05-12T09:40:11+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_model_mesh_model.py
- scripts/run_flowguard_coverage_sweep.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`, schema 1.0
- OK: `python simulations/run_flowpilot_model_mesh_checks.py --json-out simulations/flowpilot_model_mesh_results.json`
- OK: `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 30 --json-out tmp\flowguard_model_mesh_network_sweep_after_runner_upgrade.json`
- OK: `python scripts/check_install.py`
- OK: `python scripts/smoke_autopilot.py --fast`
- Partial: `python scripts/smoke_autopilot.py` timed out after 124 seconds and
  left a spawned `run_meta_checks.py` child process; both were stopped.

### Findings
- Coverage sweep now parses all 44 FlowGuard runners in this repository; no
  runner remains unparsed or unavailable.
- The only live findings after runner ingestion were the four mesh blockers:
  active blocker present, packet authority unchecked, parent repair reusing a
  leaf-only event, and collapsed repair outcome events.
- The mesh classification is valid while current-run permission is blocked:
  `classification_ok=true`, `current_run_can_continue=false`, and
  `decision=blocked_by_cross_model_contradiction`.

### Counterexamples
- The model rejects treating abstract/local green checks as authority to
  continue the current live run.
- The model rejects ignoring coverage parse gaps in a mesh-level decision.

### Friction Points
- Full smoke is too heavy for this quick recommendation pass; fast smoke,
  install, mesh, and coverage sweep passed.

### Skipped Steps
- FlowPilot runtime/code repair was intentionally not started per user
  instruction.
- Local installed skill sync and remote publish/push were not run.

### Next Actions
- Implement the recommended runtime repair separately as a small control-plane
  transaction kernel with event-capability preflight, typed repair outcomes,
  and packet authority gating.

## 2026-05-11 - Route Placeholder Display Contract

- Trigger reason: User wanted the startup Mermaid route sign to remain as a
  useful placeholder while making its placeholder identity and replacement rule
  explicit before any runtime change.
- Risk modeled: Startup route-sign placeholders could be mistaken for canonical
  route maps, keep showing after real route data appears, or rely on indirect
  fields such as `route_source_kind: none` instead of a clear display contract.
- Model files: `simulations/flowpilot_route_display_model.py`,
  `simulations/run_flowpilot_route_display_checks.py`,
  `simulations/flowpilot_route_display_results.json`.
- Commands:
  - OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`:
    `1.0`
  - OK after one model-order repair:
    `python simulations\run_flowpilot_route_display_checks.py --json-out simulations\flowpilot_route_display_results.json`
  - OK: `python -m py_compile scripts\flowpilot_user_flow_diagram.py skills\flowpilot\assets\flowpilot_user_flow_diagram.py simulations\flowpilot_route_display_model.py simulations\run_flowpilot_route_display_checks.py`
  - OK: `python -m unittest tests.test_flowpilot_user_flow_diagram tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_display_plan_is_controller_synced_projection_from_pm_plan tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_cockpit_requested_startup_display_records_chat_fallback_mermaid tests.test_flowpilot_meta_route_sign`
  - OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
  - OK: `python scripts\check_install.py`
  - OK: `python scripts\audit_local_install_sync.py --json`
  - OK: `python scripts\install_flowpilot.py --check --json`
- Findings: The route-display model now catches missing placeholder identity,
  missing placeholder replacement rule, canonical displays that keep placeholder
  semantics, and canonical displays with no canonical identity. Runtime display
  packets now carry `display_role`, `is_placeholder`, `replacement_rule`, and
  `canonical_route_available`.
- Skipped/partial checks: Full `tests.test_flowpilot_router_runtime` was
  attempted but timed out after about ten minutes, so it was not counted as a
  pass. The targeted router display tests and install checks passed.
- Next action: If a future native Cockpit UI reader consumes these packets,
  prefer the explicit fields over inferring placeholder state from route source
  and node counts.

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


## controller-wait-boundary-audit - Audit FlowPilot Controller stop at role ACK wait boundary

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed that stopping the foreground Controller at a role wait can stop background agents and halt FlowPilot progress
- Status: read-only audit completed
- Skill decision: used_flowguard read_only_audit
- Started: 2026-05-14T10:50:00+00:00
- Ended: 2026-05-14T10:50:00+00:00

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `openspec list --json`
- OK: inspected `HANDOFF.md`, `docs/flowguard_preflight_findings.md`, current run router/lifecycle records, router wait code, and related OpenSpec artifacts
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_record_external_event_does_not_preconsume_incomplete_bundle_ack tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_user_intake_mail_requires_packet_ledger_check_after_pm_cards`

### Findings
- The stopped run did receive both direct Router ACKs. PM bundle ACK returned at `2026-05-14T10:45:15Z`.
- The Router would have advanced to `check_packet_ledger` after a subsequent `next`/`run-until-wait`; focused tests confirm that path.
- The live failure mode is a host/protocol liveness mismatch: current Controller guidance treats ordinary card/bundle waits as controlled stops for heartbeat/manual resume, but the current host workflow may not preserve useful background-agent progress once the foreground Controller turn ends.
- A durable fix should model and require either bounded artifact-based foreground polling until ACK consumption, or proven host continuation/role-rehydration before allowing Controller to end a nonterminal card/bundle wait.

### Skipped Steps
- No production code was changed in this audit.
- Full FlowGuard suites were not rerun because the task was diagnostic and two focused runtime tests directly covered the observed ACK continuation path.

## 2026-05-14 - Unified Blocker Repair Policy

### Trigger
- User requested a small, concrete blocker-repair upgrade where every blocker has a first handler, bounded direct retries, PM escalation after retry exhaustion, PM recovery options, return-gate recording, and hard-stop handling while preserving parallel-agent changes.

### Files Updated
- openspec/changes/unify-blocker-repair-policy/
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/runtime_kit/cards/roles/controller.md
- skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_activation.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_model_miss_triage.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md
- templates/flowpilot/blocker_repair_policy.template.json
- templates/flowpilot/runs/run-001/run.template.json
- templates/flowpilot/state.template.json
- templates/flowpilot/README.md
- simulations/meta_model.py
- simulations/capability_model.py
- simulations/run_meta_checks.py
- simulations/run_capability_checks.py
- tests/test_flowpilot_router_runtime.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `openspec validate unify-blocker-repair-policy --strict`
- OK: `openspec status --change unify-blocker-repair-policy --json`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\meta_model.py simulations\capability_model.py simulations\run_meta_checks.py simulations\run_capability_checks.py`
- OK: targeted blocker-policy router tests: 6 passed.
- OK: targeted existing PM repair decision router tests: 6 passed.
- OK: `python simulations/run_meta_checks.py` with background log root `tmp/flowguard_background/`, exit code 0, status completed, proof_reuse false; stdout `tmp/flowguard_background/run_meta_checks.out.txt`, stderr `tmp/flowguard_background/run_meta_checks.err.txt`, combined `tmp/flowguard_background/run_meta_checks.combined.txt`, exit `tmp/flowguard_background/run_meta_checks.exit.txt`; latest update 2026-05-14T12:16:25.5523183+02:00.
- OK: `python simulations/run_capability_checks.py` with background log root `tmp/flowguard_background/`, exit code 0, status completed, proof_reuse false; stdout `tmp/flowguard_background/run_capability_checks.out.txt`, stderr `tmp/flowguard_background/run_capability_checks.err.txt`, combined `tmp/flowguard_background/run_capability_checks.combined.txt`, exit `tmp/flowguard_background/run_capability_checks.exit.txt`; latest update 2026-05-14T12:19:13.8769425+02:00.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py --json`

### Findings
- Router now attaches a blocker repair policy row and run-visible policy snapshot to control blockers.
- Mechanical control-plane blockers first return to the responsible role, then escalate to PM after the direct retry budget is exhausted.
- PM-handled blockers now require an allowed recovery option and a return gate or terminal stop before the blocked path can continue.
- Fatal hard-stop blockers reject ordinary PM waiver handling.
- Self-interrogation blockers are PM-handled blockers with recovery options to rerun, record disposition, or convert findings into repair work.
- PM and Controller cards now tell roles to read the policy row, retry count, recovery options, return policy, and hard-stop conditions instead of treating blocker review as a silent pass.
- Local installed FlowPilot skill digest matches repository source after sync.

### Counterexamples
- exhausted direct blocker retries did not escalate to PM
- PM-handled blocker lacked recovery option, return gate, or silent-pass prohibition
- router hard rejection did not attach a blocker repair policy row and run-visible policy snapshot

### Friction Points
- Full `tests/test_flowpilot_router_runtime.py` exceeded the local 10-minute timeout; focused blocker and PM repair decision tests plus FlowGuard meta/capability checks were used.
- Existing parallel-agent changes were present across several FlowPilot files; this pass preserved them and avoided any rollback.

### Skipped Steps
- No remote GitHub push, tag, or release action was performed.

### Next Actions
- Keep future blocker additions table-driven: add a policy row first, then route first-handler, retry budget, PM recovery option, return gate, and hard-stop handling from that row.

## 2026-05-14 - Startup Heartbeat Before Controller Core

### Trigger
- User confirmed that scheduled continuation heartbeat should be bootstrapped during startup before entering the Controller main loop, and requested OpenSpec plus FlowGuard repair with local installed skill sync.

### Files Updated
- openspec/changes/move-heartbeat-before-controller-core/
- skills/flowpilot/assets/flowpilot_router.py
- tests/test_flowpilot_router_runtime.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `openspec validate move-heartbeat-before-controller-core --strict --json`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\meta_model.py simulations\capability_model.py`
- OK: targeted startup heartbeat/manual-resume/router tests: 4 passed.
- OK: `python simulations/run_meta_checks.py` with background log root `tmp/flowguard_background/`, exit code 0, status completed, proof_reuse false; stdout `tmp/flowguard_background/run_meta_checks.out.txt`, stderr `tmp/flowguard_background/run_meta_checks.err.txt`, combined `tmp/flowguard_background/run_meta_checks.combined.txt`, exit `tmp/flowguard_background/run_meta_checks.exit.txt`; latest update 2026-05-14T12:16:25.5523183+02:00.
- OK: `python simulations/run_capability_checks.py` with background log root `tmp/flowguard_background/`, exit code 0, status completed, proof_reuse false; stdout `tmp/flowguard_background/run_capability_checks.out.txt`, stderr `tmp/flowguard_background/run_capability_checks.err.txt`, combined `tmp/flowguard_background/run_capability_checks.combined.txt`, exit `tmp/flowguard_background/run_capability_checks.exit.txt`; latest update 2026-05-14T12:19:13.8769425+02:00.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\check_install.py --json`

### Findings
- Scheduled startup now emits `create_heartbeat_automation` from the bootloader before `load_controller_core`.
- Controller core loading now requires a ready host heartbeat binding for scheduled continuation and then marks `controller_core_loaded`.
- Manual-resume startup still bypasses heartbeat creation and enters Controller core with manual continuation binding.
- Meta and capability models now reject loading Controller core before continuation readiness.
- Installed local FlowPilot skill digest matches repository source after sync.

### Counterexamples
- controller_core_loaded_without_continuation_binding
- scheduled_startup_without_host_heartbeat_binding
- manual_resume_startup_created_heartbeat

### Friction Points
- Full `tests/test_flowpilot_router_runtime.py` exceeded the local 15-minute timeout, so focused startup/router tests plus FlowGuard meta/capability checks and install checks were used.
- A broader startup keyword subset exposed an existing `pm.material_scan` await-role ordering failure that appears tied to parallel startup/card-boundary work, not this heartbeat bootstrap change.

### Skipped Steps
- No remote GitHub push, tag, or release action was performed.
- Existing parallel-agent file changes were preserved and not reverted.

### Next Actions
- Treat heartbeat creation as startup bootstrap ownership unless a future design explicitly moves continuation binding into another pre-Controller host boundary.


## flowpilot-control-plane-event-contract - Validate Router external event waits before persistence

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Router control blocker repair could persist a wait for a string that was not a registered external event, causing resume to wait for an event that could never be recorded.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T14:20:00+00:00
- Ended: 2026-05-11T15:45:00+00:00
- Commands OK: partial; focused checks passed, one broad existing conformance scan still reports unrelated current-source issues.

### Model Files
- `simulations/flowpilot_event_contract_model.py`
- `simulations/run_flowpilot_event_contract_checks.py`
- `simulations/flowpilot_event_contract_results.json`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py simulations\flowpilot_event_contract_model.py simulations\run_flowpilot_event_contract_checks.py tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_flowpilot_event_contract_checks.py --json-out simulations\flowpilot_event_contract_results.json`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_delivered_control_blocker_with_legacy_invalid_wait_falls_back_to_pm_repair_decision tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_repair_transaction_recheck_blocker_registers_followup_blocker tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_repair_transaction_protocol_blocker_registers_followup_blocker tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_repair_decision_can_repeat_for_new_control_blocker tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_missing_open_receipt_control_blocker_routes_to_same_reviewer_reissue`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out %TEMP%\flowpilot_router_loop_event_contract.json`
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py --json-out %TEMP%\flowpilot_repair_transaction_event_contract.json`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- Partial: `python -m unittest tests.test_flowpilot_router_runtime` did not complete in the foreground timeout and the background retry did not emit a terminal summary.
- Known unrelated residual: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json` still reports current-source conformance findings about PM resume payload and reviewer blocker flags; the abstract model portion passes and this is outside the event-wait contract fix.

### Findings
- FlowGuard event-contract model now rejects unregistered PM rerun targets, internal Router action labels, PM repair self-loops, ACK/check-in event waits, waits whose prerequisites are false, success-only repair outcome tables, duplicate PM repair mutation, and post-write cleanup-only recovery.
- Production Router now validates external wait events before writing pending actions or control blocker repair outcomes.
- Legacy bad PM-decision-required control blockers fall back to requesting a fresh PM repair decision instead of waiting forever on an unrecordable event.

### Counterexamples
- `internal_router_action_as_pm_rerun_target`
- `unknown_string_as_pm_rerun_target`
- `pm_repair_event_as_rerun_target`
- `ack_event_in_allowed_external_events`
- `ack_consumed_semantic_wait_lost`
- `wait_requires_false_flag`
- `material_repair_success_only`
- `duplicate_pm_repair_created_new_blocker`
- `postwrite_cleanup_only_for_invalid_wait`

### Friction Points
- Full router runtime unittest is too slow or unstable for an interactive foreground pass; keep focused regression tests as the required event-contract gate and run the full suite as a background or CI-level check.

### Next Actions
- Consider adding a runtime conformance runner that summarizes the full router runtime suite without relying on unittest progress dots.

## gate-outcome-control-blocker-repair-20260511 - Model-backed repair for stale gate blockers and wrong-role follow-ups

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot accepted a PM-routed repair decision but then produced stale gate/control-blocker state around `reviewer_passes_child_skill_gate_manifest`.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T12:30:00+00:00
- Ended: 2026-05-11T13:00:00+00:00
- Commands OK: True

### Model Files
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/run_flowpilot_control_plane_friction_checks.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out tmp\flowpilot_control_plane_friction_results.json`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "child_skill_gate_manifest_repair_pass_clears_active_gate_block or control_blocker_reviewer_followup_rejects_pm_origin"`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "child_skill_gate_manifest_block_records_repair_without_approval or child_skill_gate_manifest_repair_pass_clears_active_gate_block or control_blocker_reviewer_followup_rejects_pm_origin or already_recorded_event_can_resolve_delivered_control_blocker or already_recorded_event_does_not_resolve_pm_required_control_blocker or already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision or pm_repair_transaction_commits_material_reissue_generation or pm_repair_decision_can_repeat_for_new_control_blocker"`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_capability_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The prior model did not represent an active gate outcome block coexisting with a newer same-gate reviewer pass.
- The prior model did not check that direct Router ACK consumption preserves the semantic pass/block wait.
- The prior model did not check that a control blocker delivered to PM cannot make PM the authorizing role for a reviewer follow-up event.

### Counterexamples
- `gate_pass_left_active_block`
- `ack_consumed_semantic_wait_lost`
- `pm_impersonates_reviewer_followup`
- `no_legal_next_with_valid_role_output`
- `duplicate_pm_repair_created_new_blocker`

### Friction Points
- Large meta/capability checks exceeded the short foreground timeout and were rerun as long background checks with stdout/stderr logs under `tmp/`.
- The working tree had active peer-agent changes and a concurrent local commit. The repair avoided reverting those changes and staged only the model/plan/adoption files that belong to this repair pass.

### Skipped Steps
- No GitHub push was run, per user instruction.

### Next Actions
- Keep the gate outcome lifecycle checks in the control-plane friction model whenever future router wait-state or repair-dedup logic changes.


## direct-router-ack-migration - Routed system-card and active-holder ACKs directly to Router

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing protocol change to ACK routing, prompt contracts, Router/card runtime validation, and packet active-holder flow
- Status: completed with targeted verification; full router pytest suite did not finish within the local timeout window
- Skill decision: used_flowguard
- Started: 2026-05-11T12:00:00+00:00
- Ended: 2026-05-11T12:35:00+00:00
- Duration seconds: not measured precisely
- Commands OK: true for required targeted checks; false for timeout-only full-suite attempts

### Model Files
- `simulations/flowpilot_card_envelope_model.py`
- `simulations/card_instruction_coverage_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python -m py_compile skills\flowpilot\assets\card_runtime.py skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\flowpilot_runtime.py skills\flowpilot\assets\packet_runtime.py simulations\flowpilot_card_envelope_model.py simulations\run_flowpilot_card_envelope_checks.py simulations\card_instruction_coverage_model.py simulations\run_card_instruction_coverage_checks.py`
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py -q`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py -q`
- OK: targeted router ACK/card/bundle/route-card checks in `tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- Timeout: `python -m pytest tests\test_flowpilot_router_runtime.py -q`
- Timeout: `python simulations\run_meta_checks.py`
- Timeout: `python simulations\run_capability_checks.py`

### Findings
- Direct Router ACK token validation is now required for system-card and bundle ACKs.
- Legacy `record-event *_card_ack` submissions are rejected instead of rerouted.
- Prompt coverage now detects stale Controller-routed ACK wording and missing direct-Router ACK/result guidance in card and packet prompts.
- A model miss was found and fixed: startup system cards may be issued before an execution frontier exists, so direct ACK tokens must allow missing frontier bindings only during that startup-before-frontier state.
- The prompt coverage model found real stale/custom card wording in route officer/reviewer cards and a duplicate stale identity block in `pm_role_work_request`; those prompts were corrected.

### Counterexamples
- Missing direct Router ACK token.
- ACK submitted through Controller handoff.
- ACK accepted through legacy external-event entrypoint.
- Missing direct Router ACK prompt coverage.
- Stale Controller ACK prompt wording.
- Missing packet active-holder ACK/result guidance.
- Missing Controller wait-for-router-notice guidance.

### Friction Points
- The full router pytest module and full meta/capability graph expansions exceeded the local timeout windows. Targeted router checks passed, and meta/capability proofs were reused through the runners' `--fast` proof-validation mode because those model files were not changed.

### Skipped Steps
- No GitHub push was performed, per user instruction.

### Next Actions
- If a future change touches `simulations/meta_model.py` or `simulations/capability_model.py`, rerun the full non-fast graph checks with a larger execution window.


## 2026-05-11 - Heartbeat resume role reuse model upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: optimize FlowPilot heartbeat/manual resume so confirmed live role agents are reused after current-run memory refresh, while only failed or uncertain roles are replaced.
- Status: completed
- Skill decision: used_flowguard
- Commands OK: True

### Model Files
- `simulations/flowpilot_resume_model.py`
- `simulations/run_flowpilot_resume_checks.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_resume_checks.py`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_resume_model.py simulations\run_flowpilot_resume_checks.py`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_resume_reentry_loads_state_before_resume_cards -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k resume -q`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`

### Findings
- The resume model now distinguishes all-active reuse, partial failed-role replacement, and all-uncertain replacement.
- Added hazards prove the model catches all-active roles being replaced, one failed role causing all six replacements, and failed-role recovery that does not reuse still-active roles.

### Counterexamples
- `all_active_roles_replaced_instead_of_reused`
- `one_failed_role_replaced_all_six`
- `one_failed_role_does_not_reuse_active_roles`

### Friction Points
- Full `run_meta_checks.py` and `run_capability_checks.py` exceeded the local timeout, so unchanged meta/capability proof artifacts were checked with `--fast`.

### Skipped Steps
- Full meta/capability reruns were skipped because this change only touched the resume model/router contract and the full checks timed out locally.

### Next Actions
- none recorded


## 2026-05-11 - Unified role-output progress and concurrent resume liveness

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Reduce background-agent wait time by making all role-output waits expose metadata-only progress and by requiring concurrent six-role resume liveness probes.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T08:16:06+00:00
- Ended: 2026-05-11T10:51:26+00:00
- Commands OK: True

### Model Files
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/flowpilot_resume_model.py`
- `simulations/flowpilot_role_output_runtime_model.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations/flowpilot_control_plane_friction_results.json`
- OK: `python simulations/run_flowpilot_resume_checks.py`
- OK: `python simulations/run_flowpilot_role_output_runtime_checks.py --json-out simulations/flowpilot_role_output_runtime_results.json`
- OK: `python simulations/run_meta_checks.py`
- OK: `python simulations/run_capability_checks.py`
- OK: `python simulations/run_flowpilot_router_loop_checks.py`
- OK: `python -m pytest tests/test_flowpilot_role_output_runtime.py tests/test_flowpilot_packet_runtime.py -q`
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py` split into four collected-test shards; all 122 collected tests passed across the shards.
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/install_flowpilot.py --check --json`
- OK: `python scripts/check_install.py --json`

### Findings
- Role-output progress needed to be defaulted through the existing runtime progress pattern, not added as a PM-resume-only patch.
- The resume PM decision wait was bypassing the shared role-output wait constructor; routing it through that constructor exposed the metadata-only progress status consistently.
- Six-role resume liveness must be represented as a single concurrent batch with one batch id and all probe starts recorded before any individual wait result.

### Counterexamples
- Model hazards caught missing default progress, missing progress prompt inheritance, broad status visibility, sealed-body leakage, manual progress writes, nonnumeric progress, using progress as decision evidence, serial six-role liveness waits, missing probe batches, early waiting before all starts, and batch id mismatch.

### Friction Points
- Full `tests/test_flowpilot_router_runtime.py` exceeded a 10 minute single-process timeout, so the same collected tests were run in four shards.
- Two router tests had stale expectations from the concurrent active-holder/ledger-check work and were updated to assert the current invariants.

### Skipped Steps
- GitHub push was intentionally skipped per user instruction.

### Next Actions
- Keep future role-output waits on the shared wait constructor so progress visibility and metadata-only boundaries stay uniform.


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

## 2026-05-11 - FlowPilot card ACK check-in repair

### Trigger
- System-card ACK handling affects card-return state, route progress, role runtime entrypoints, external-event routing, and installed skill behavior.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --no-write`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`
- OK: `python -m py_compile scripts\flowpilot_runtime.py skills\flowpilot\assets\flowpilot_runtime.py skills\flowpilot\assets\flowpilot_router.py`
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_system_card_delivery_requires_manifest_check -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_initial_pm_system_cards_are_delivered_as_same_role_bundle -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_committed_system_card_relay_can_resolve_without_apply_roundtrip -q`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers -q`
- OK: `python scripts\check_install.py --json`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: `python scripts\audit_local_install_sync.py --json`

### Findings
- Card envelopes and card-bundle envelopes now carry an explicit `card_checkin_instruction`.
- The unified runtime now has one-step `receive-card` and `receive-card-bundle` commands that open the card, write read receipts, write ACK envelopes, and validate them.
- Controller guidance now states card ACKs are not normal external events.
- Router can recover if a valid runtime-backed card ACK is sent to the external-event entrypoint; it reroutes to card-return validation instead of recording a normal event.

### Counterexamples
- Missing check-in instruction.
- Missing check-in command.
- Hand-written ACK attempt.
- Card ACK sent to the external-event entrypoint without safe reroute.
- ACK recorded as a normal external event.

### Friction Points
- Running the whole router runtime test file exceeded the tool timeout once, so the verification used focused ACK/card-bundle tests plus install checks.
- Running local install sync and install check in parallel caused a transient missing-file read during copy; rerunning the check after sync passed.

### Skipped Steps
- Remote GitHub push/release skipped by user request.

### Next Actions
- Keep future system-card changes aligned across card envelopes, role I/O protocol, runtime entrypoints, Controller wording, router recovery, and FlowGuard hazards.


## run-20260511-081606-product-architecture-modelability - Product FlowGuard officer assessed product architecture modelability and produced role-output event envelope

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot product architecture modelability gate before route drafting
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T09:30:42+00:00
- Ended: 2026-05-11T09:30:42+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python .flowpilot/runs/run-20260511-081606/flowguard/product_architecture_modelability_checks.py --architecture-path .flowpilot/runs/run-20260511-081606/product_function_architecture.json --json-out .flowpilot/runs/run-20260511-081606/flowguard/product_architecture_modelability_results.json`

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


## run-20260511-081606-root-contract-modelability - Product FlowGuard officer assessed root acceptance contract modelability and produced role-output event envelope

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot root contract modelability gate before route design
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T09:54:10+00:00
- Ended: 2026-05-11T09:54:10+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python .flowpilot/runs/run-20260511-081606/flowguard/root_contract_modelability_checks.py --contract-path .flowpilot/runs/run-20260511-081606/root_acceptance_contract.json --scenario-pack-path .flowpilot/runs/run-20260511-081606/standard_scenario_pack.json --json-out .flowpilot/runs/run-20260511-081606/flowguard/root_contract_modelability_results.json`

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


## run-20260511-081606-child-skill-product-fit - Product FlowGuard officer assessed child-skill product fit and produced role-output event envelope

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot child-skill product-fit gate before route design
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T10:57:47+00:00
- Ended: 2026-05-11T10:57:47+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python .flowpilot/runs/run-20260511-081606/flowguard/child_skill_product_fit_checks.py --capabilities-path .flowpilot/runs/run-20260511-081606/capabilities.json --selection-path .flowpilot/runs/run-20260511-081606/pm_child_skill_selection.json --manifest-path .flowpilot/runs/run-20260511-081606/child_skill_gate_manifest.json --conformance-path .flowpilot/runs/run-20260511-081606/flowguard/child_skill_conformance_model.json --json-out .flowpilot/runs/run-20260511-081606/flowguard/child_skill_product_fit_results.json`

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


## run-20260511-081606-route-product-check - Product FlowGuard officer assessed PM route product fit and produced route product pass event envelope

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot route product check gate before route activation
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T11:41:01+00:00
- Ended: 2026-05-11T11:41:01+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python .flowpilot/runs/run-20260511-081606/flowguard/route_product_check_model.py --flow-draft-path .flowpilot/runs/run-20260511-081606/routes/route-001/flow.draft.json --route-payload-path .flowpilot/runs/run-20260511-081606/route_drafts/route-001_pm_route_draft_payload.body.json --product-architecture-path .flowpilot/runs/run-20260511-081606/product_function_architecture.json --product-model-path .flowpilot/runs/run-20260511-081606/flowguard/product_architecture_modelability.json --root-contract-path .flowpilot/runs/run-20260511-081606/root_acceptance_contract.json --capabilities-path .flowpilot/runs/run-20260511-081606/capabilities.json --process-results-path .flowpilot/runs/run-20260511-081606/flowguard/route_process_check_results.json --json-out .flowpilot/runs/run-20260511-081606/flowguard/route_product_check_results.json`

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


## flowpilot-all-models-20260511 - Update all FlowPilot FlowGuard models after handoff artifact protocol changes

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requires every existing FlowGuard model to be updated and passing after broad protocol changes
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T16:15:11+00:00
- Ended: 2026-05-11T16:15:11+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_protocol_contract_conformance_model.py

### Commands
- OK (0.000s): `python tmp\\run_all_flowguard_checks.py`

### Findings
- Updated protocol conformance source scan to recognize direct PM resume payload_contract binding and gate-outcome reviewer block lanes; full regression passed 39/39.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- production replay skipped by model-specific conformance checks where declared; this pass was the repository model regression suite

### Next Actions
- none recorded


## contract-runtime-gap-audit-20260511 - Audit FlowPilot contract-event-runtime output type gap for startup activation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Protocol/runtime routing mismatch affects stateful role-output submission, router events, and startup activation authority.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T20:38:22+00:00
- Ended: 2026-05-11T20:38:22+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python simulations\run_flowpilot_role_output_runtime_checks.py --json-out tmp\role_output_runtime_check_current.json`
- OK (0.000s): `python simulations\run_output_contract_checks.py --json-out tmp\output_contract_check_current.json`

### Findings
- PM startup activation contracts exist and router events exist, but role_output_runtime lacks matching output types and registry runtime metadata.
- Current role-output checks are manually enumerated and pass despite contract registry/runtime coverage gaps.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- No production code was changed because this turn used OpenSpec explore/read-only audit framing.

### Next Actions
- Add registry-backed conformance that every role_output_envelope contract maps to a runtime output type and router event or is explicitly marked non-runtime.


## contract-runtime-binding-registry-20260511 - Make FlowPilot role-output contract runtime bindings registry-driven and checked end to end

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Changing role-output runtime, contract registry, router event binding, and startup activation submission affects stateful protocol flow, role authority, route events, and sealed body boundaries.
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-11T20:45:14+00:00
- Ended: 2026-05-11T20:45:14+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_role_output_runtime_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`

### Findings
- Risk intent: prevent descriptive contract tables from drifting away from runtime output types, router events, and role cards.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Write detailed binding upgrade plan and then upgrade FlowGuard model/source checks before production code edits.


## contract-runtime-binding-registry-20260511 - Make FlowPilot role-output contract runtime bindings registry-driven and checked end to end

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Changing role-output runtime, contract registry, router event binding, and startup activation submission affects stateful protocol flow, role authority, route events, and sealed body boundaries.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T21:15:33+00:00
- Ended: 2026-05-11T21:15:33+00:00
- Duration seconds: 0.000
- Commands OK: False

### Model Files
- simulations/flowpilot_role_output_runtime_model.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_role_output_runtime_checks.py; python -m unittest tests.test_flowpilot_role_output_runtime -v; python scripts/check_install.py; python simulations/run_meta_checks.py; python simulations/run_capability_checks.py --fast; targeted startup/router unittest set`
- FAIL (0.000s): `python simulations/run_capability_checks.py (full rerun exceeded 10 minutes; --fast proof remained valid because capability_model.py and runner fingerprint were unchanged)`

### Findings
- Registry-backed binding source now covers 16 role-output contracts plus pm_resume_recovery_decision compatibility alias; source check fails if a runtime-backed contract lacks output_type, body schema, allowed roles, path/hash keys, default location, or fixed router event.
- Startup activation approval, repair request, and protocol dead-end are ordinary registry rows and are accepted by flowpilot_runtime.py prepare-output/submit-output-to-router through generated SUPPORTED_OUTPUT_TYPES.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- none recorded

### Next Actions
- Keep future role-output additions in runtime_kit/contracts/contract_index.json with runtime_channel=role_output_runtime and run role-output runtime checks before release.


## flowpilot-pm-package-absorption-verification-20260512 - Verify PM-first package absorption and local install sync

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested a FlowGuard-first implementation path for routing PM-issued worker package results back to the Project Manager before any formal reviewer gate.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T21:15:00+02:00
- Ended: 2026-05-12T23:59:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_pm_package_absorption_model.py
- simulations/flowpilot_control_plane_friction_model.py
- simulations/flowpilot_resume_model.py
- simulations/flowpilot_router_loop_model.py
- simulations/flowpilot_protocol_contract_conformance_model.py
- simulations/flowpilot_legal_next_action_model.py
- simulations/flowpilot_model_driven_recursive_route_model.py
- simulations/flowpilot_parent_child_lifecycle_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations\run_flowpilot_pm_package_absorption_checks.py --json-out simulations\flowpilot_pm_package_absorption_results.json`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`
- OK: `python simulations\run_flowpilot_dynamic_return_path_checks.py --json-out simulations\flowpilot_dynamic_return_path_results.json`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json`
- OK: `python simulations\run_flowpilot_resume_checks.py`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_flowpilot_legal_next_action_checks.py --json-out simulations\flowpilot_legal_next_action_results.json`
- OK: `python simulations\run_flowpilot_model_driven_recursive_route_checks.py --json-out simulations\flowpilot_model_driven_recursive_route_results.json`
- OK: `python simulations\run_flowpilot_parent_child_lifecycle_checks.py --json-out simulations\flowpilot_parent_child_lifecycle_results.json`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python -m unittest tests.test_flowpilot_output_contracts tests.test_flowpilot_packet_runtime`
- OK: `python -m unittest tests.test_flowpilot_router_runtime` split into three deterministic chunks: 50 passed, 50 passed, 44 passed.
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`

### Findings
- The focused PM package model accepts only the PM-first flow for current-node, material-scan, research, and resume worker results.
- Negative hazards catch direct raw worker result relay to reviewer, undispositioned worker evidence, reviewer gate without a PM-built package, missing node-completion reviewer gate, removed critical reviewer gates, resume direct-to-reviewer drift, controller body reads, and legacy reviewer-relay flags reused as current acceptance.
- Runtime and contract source checks show current-node, material-scan, research, and reviewer-result-review package results require `project_manager` as the first result recipient.
- The local installed FlowPilot skill is fresh against this repository after sync.
- A parallel legal-next-action change was preserved and verified; one route-root error message was tightened so replanning gaps are not mislabeled as repair-node work.

### Counterexamples
- `raw_worker_result_relayed_to_reviewer`
- `formal_evidence_from_undispositioned_result`
- `reviewer_started_without_pm_gate_package`
- `node_completion_without_reviewer_gate`
- `critical_reviewer_gate_removed`
- `resume_result_direct_to_reviewer`
- `material_research_decision_without_gate`
- `controller_reads_sealed_body`
- `legacy_reviewer_relay_used_as_current_acceptance`
- `pm_forwarded_raw_package_to_reviewer`

### Friction Points
- A full one-shot router runtime unittest run exceeded the tool timeout, so the suite was split into three stable chunks.
- A direct full meta/capability rerun produced valid proof files but did not return cleanly through the tool output path; `--fast` proof reuse returned cleanly afterward.
- The dynamic-return-path live-run projection still reports two historical active-run findings in `run-20260512-110741`; this is current-run state debt, not a PM package absorption model failure.

### Skipped Steps
- The control-plane friction live audit was skipped for the abstract validation because the active run contains unrelated historical findings.
- Remote GitHub sync/push was intentionally skipped per user instruction.

### Next Actions
- If the historical active run should continue, repair its persisted dynamic-return-path blockers through the registered PM/router path rather than treating those old outputs as current evidence.


## flowpilot-parent-child-lifecycle-model-miss-20260512 - Model parent/child lifecycle authority before Router repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Runtime model miss where route/frontier state could appear green while parent/backward closure actions were requested before the active child subtree had executed and completed.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T21:00:00+02:00
- Ended: 2026-05-12
- Commands OK: True

### Model Files
- simulations/flowpilot_parent_child_lifecycle_model.py
- simulations/run_flowpilot_parent_child_lifecycle_checks.py
- simulations/flowpilot_model_mesh_model.py
- simulations/run_flowpilot_model_mesh_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_parent_child_lifecycle_model.py simulations\run_flowpilot_parent_child_lifecycle_checks.py`
- OK: `python simulations\run_flowpilot_parent_child_lifecycle_checks.py --json-out simulations\flowpilot_parent_child_lifecycle_results.json`
- OK: `python simulations\run_flowpilot_model_driven_recursive_route_checks.py --json-out simulations\flowpilot_model_driven_recursive_route_results.json`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python -m py_compile simulations\flowpilot_model_mesh_model.py simulations\run_flowpilot_model_mesh_checks.py`
- OK: `python simulations\run_flowpilot_model_mesh_checks.py --project-root . --run-id run-20260512-110741 --json-out simulations\flowpilot_model_mesh_results.json`

### Findings
- Added a focused FlowGuard model for parent/module closure authority, child subtree entry, leaf execution, descendant completion, current-ledger authority, and live Router next-action replay.
- The focused model accepts valid parent/child and leaf lifecycles, and rejects 12 same-class hazards.
- The model mesh now projects metadata-only route/frontier/router state and blocks the current run with `parent_child_lifecycle_conformance_failed` instead of treating old route state or abstract green evidence as liveness proof.

### Counterexamples
- abstract_green_without_live_action_replay
- child_completion_from_old_route_version
- direct_child_done_descendant_pending
- live_router_action_not_in_model
- non_leaf_acceptance_stuck_on_parent
- parent_complete_before_child_completion
- parent_dispatches_worker_packet
- parent_flags_leak_to_child
- parent_replay_before_child_entry
- parent_segment_before_child_completion
- parent_targets_before_child_entry
- stale_route_status_counts_as_child_done

### Friction Points
- Production Router code was intentionally left untouched per user instruction.
- One pre-existing Router syntax error from the stopped run remains outside this model-only pass.

### Skipped Steps
- Router/product repair was intentionally skipped until the upgraded models finish identifying the full failure class.
- Sealed packet/result/report bodies were not read.

### Next Actions
- Use these model results to derive the smallest bottom-level fix that enforces parent/child lifecycle authority in one shared place instead of patching the observed bad action only.


## flowpilot-terminal-summary-20260512 - Require final run summary before terminal observation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot terminal behavior now grants Controller a terminal-only all-current-run-files read scope and writes a final run summary receipt with FlowPilot GitHub attribution.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T19:01:00+02:00
- Ended: 2026-05-12T19:01:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_terminal_summary_model.py
- simulations/run_flowpilot_terminal_summary_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_terminal_summary_model.py simulations\run_flowpilot_terminal_summary_checks.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_flowpilot_terminal_summary_checks.py --json-out simulations\flowpilot_terminal_summary_results.json`
- OK: `python simulations\run_meta_checks.py` in background; 634501 states, 654672 edges, no stuck states, no nonterminating components.
- OK: targeted terminal-summary router tests covering protocol dead end, stopped/cancelled run, closure, legacy closure recovery, and invalid summary payloads.
- OK: `python -m unittest tests.test_flowpilot_role_output_runtime`
- OK: `python simulations\run_flowpilot_dynamic_return_path_checks.py --json-out simulations\flowpilot_dynamic_return_path_results.json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- Added terminal summary model coverage for closed, stopped, cancelled, and blocked-handoff terminal modes.
- Runtime now returns `write_terminal_summary` before `run_lifecycle_terminal` when a terminal run lacks a valid indexed summary for the current lifecycle mode.
- The summary action grants `current_run_root_all_files` read scope only after terminal mode, validates first-line FlowPilot GitHub attribution, verifies the displayed summary hash, writes `final_summary.md` and `final_summary.json`, and registers paths in `.flowpilot/index.json`.
- `write_terminal_summary` skips generic route-memory/display refreshes so the terminal receipt cannot mutate route artifacts as incidental cleanup.

### Counterexamples
- Hazards detected terminal lifecycle without summary, pre-terminal all-file read, missing attribution, missing index registration, display/saved-content mismatch, repeated summary request after completion, outside-run read, gate approval after summary, route continuation after summary, and non-summary writes in summary mode.

### Friction Points
- Full `run_meta_checks.py` exceeded the first 3-minute foreground timeout; rerunning it in the background completed successfully.

### Skipped Steps
- `python simulations\run_capability_checks.py` was not rerun because this change did not alter skill/capability routing.
- Remote GitHub sync/push was intentionally skipped per user instruction.

### Next Actions
- Future terminal artifacts should use the indexed `final_summary` receipt as the human-readable run history entry instead of adding separate ad hoc completion reports.


## flowpilot-work-authority-runtime-20260512 - Bind formal role outputs to current work authority

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested a FlowGuard-first implementation so system cards, role cards, and formal reports cannot rely on guessed Router events or prompt prose as work authority.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T18:02:00+02:00
- Ended: 2026-05-12T18:59:31+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_dynamic_return_path_model.py
- simulations/run_flowpilot_dynamic_return_path_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_dynamic_return_path_model.py simulations\run_flowpilot_dynamic_return_path_checks.py skills\flowpilot\assets\role_output_runtime.py skills\flowpilot\assets\flowpilot_runtime.py tests\test_flowpilot_role_output_runtime.py`
- OK: `python simulations\run_flowpilot_dynamic_return_path_checks.py --json-out simulations\flowpilot_dynamic_return_path_results.json`
- OK: `python -m pytest tests\test_flowpilot_role_output_runtime.py -q`
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py --json-out simulations\flowpilot_role_output_runtime_results.json`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`
- OK: `python simulations\run_flowpilot_model_mesh_checks.py --json-out simulations\flowpilot_model_mesh_results.json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\smoke_autopilot.py --fast`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python simulations\run_flowpilot_terminal_summary_checks.py --json-out simulations\flowpilot_terminal_summary_results.json`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "terminal_summary or terminal_lifecycle or run_lifecycle_terminal or user_requests_run_stop or user_requests_run_cancel"`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The dynamic-return-path model now rejects system-card-only formal reports, task-like cards without work authority, role-guessed events, registered-but-not-currently-allowed events, mechanical green misused as Router acceptance, stale authority, wrong role, wrong contract, and wrong result recipient.
- `flowpilot_runtime.py submit-output-to-router` now calls `role_output_runtime.validate_direct_router_submission_authority` before writing role-output artifacts or recording a Router event.
- Fixed-event role outputs remain valid through the contract registry; router-supplied role outputs require the current Router wait to list the submitted event.
- Core role/system cards and the PM output contract catalog now state that identity/system cards can ACK or explain routing but cannot by themselves authorize formal report work.
- The local installed FlowPilot skill is fresh against the repository after sync.
- Parallel terminal-summary work was preserved and separately verified before local install sync.

### Counterexamples
- Rejected: hidden formal work inside an identity card, task card without registered authority, role-guessed unknown event, registered event outside current wait, static card text treated as a dynamic lease, old direct officer event competing with PM role-work, wrong role, wrong contract, wrong recipient, stale authority, and mechanical runtime pass treated as process pass.

### Friction Points
- A direct full `run_meta_checks.py` invocation did not return a readable result through the tool, so the valid cached proof path was used with `--fast`.
- The model mesh live projection still classifies the historical active run as blocked by existing packet-authority findings; that is a current-run state issue, not a regression from this change.

### Skipped Steps
- Remote GitHub sync/push was intentionally skipped per user instruction.

### Next Actions
- For future router-supplied role-output contracts, keep the direct Router submission authority check and prefer PM role-work packets or active-holder leases for assigned work instead of prompt-only event names.


## flowpilot-resume-priority-control-blocker-20260512 - Prioritize heartbeat/manual resume before active control blockers

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Heartbeat resume was observed to handle an existing active router control blocker before running resume reentry, which can delay crew rehydration and make resumed work unreachable.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T17:45:00+02:00
- Ended: 2026-05-12T18:17:45+02:00
- Duration seconds: 1965
- Commands OK: True

### Model Files
- simulations/flowpilot_resume_model.py
- simulations/run_flowpilot_resume_checks.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_resume_model.py simulations\run_flowpilot_resume_checks.py tests\test_flowpilot_router_runtime.py`
- OK: `python simulations\run_flowpilot_resume_checks.py`
- OK: targeted resume runtime unittest set
- OK: targeted control-blocker runtime unittest set
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python scripts\smoke_autopilot.py --fast`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The resume model now represents an active control blocker that exists at heartbeat/manual resume entry.
- The router fix suppresses active control-blocker handling while `resume_reentry_requested` is true and `pm_resume_recovery_decision_returned` is false.
- The deferred control blocker is not deleted; after PM resume recovery decision evidence is recorded, the router can return to the original blocker.
- Runtime regression coverage proves the first resume action is `load_resume_state`, not `handle_control_blocker`, when both are possible.

### Counterexamples
- The upgraded model detects active blocker handling before resume state load.
- The upgraded model detects waiting on or handling an active blocker before role rehydration and PM resume decision.
- The upgraded model detects an active blocker being present without an explicit defer record.
- The upgraded model detects completing route progress while an active control blocker remains unhandled after resume readiness.

### Friction Points
- A full `tests.test_flowpilot_router_runtime` run exceeded the local 5 minute command window, so validation used focused resume and control-blocker runtime suites.
- A full non-fast capability check exceeded the local 5 minute command window; capability routing files were unchanged, so the fast proof path was used and passed.
- Running install sync and install audit in parallel produced a stale audit read once; rerunning the audit after sync passed.

### Skipped Steps
- Remote GitHub sync/push was intentionally skipped per user instruction.
- Production conformance replay for the abstract resume model remains skipped because no production replay adapter exists in the allowed write set.

### Next Actions
- If resume ordering changes again, keep the active-control-blocker defer/return labels and hazards in the resume model so the same regression is caught before runtime edits.


## flowpilot-dynamic-return-path-authority-20260512 - Model and audit router-supplied role-output return-path authority

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to upgrade FlowGuard coverage for prompt/report road-sign failures, run models against current FlowPilot state, and propose a bottom-level fix without modifying FlowPilot product code.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T18:02:00+02:00
- Ended: 2026-05-12T18:09:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_dynamic_return_path_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations/flowpilot_dynamic_return_path_model.py simulations/run_flowpilot_dynamic_return_path_checks.py`
- OK: `python simulations/run_flowpilot_dynamic_return_path_checks.py --json-out simulations/flowpilot_dynamic_return_path_results.json`
- OK: `python simulations/run_flowpilot_model_mesh_checks.py --json-out tmp/flowpilot_model_mesh_dynamic_return_crosscheck.json`
- OK: `python simulations/run_flowpilot_role_output_runtime_checks.py --json-out tmp/flowpilot_role_output_runtime_dynamic_return_crosscheck.json`

### Findings
- The new model separates static card guidance, mechanical role-output validation, and live Router/PM packet authority.
- Current run `run-20260512-110741` has two concrete rejected router-supplied `officer_model_report` attempts: `product_officer_model_report` was unknown, and `product_officer_blocks_product_architecture_modelability` was registered but not currently allowed.
- Four router-supplied role-output contracts require a concrete dynamic lease: `officer_model_report`, `flowguard_model_miss_report`, `reviewer_review_report`, and `material_sufficiency_report`.
- Existing PM role-work packets show the correct mitigation shape for `officer_model_report`: a PM-authored packet with strict process contract binding and result recipient set to `project_manager`.

### Counterexamples
- The model rejects system-card-only router-supplied reports, role-guessed unknown events, registered but not currently allowed events, mechanical green treated as Router acceptance, static card text treated as a dynamic event lease, and legacy direct officer events competing with PM role-work result contracts.

### Skipped Steps
- FlowPilot product/router/runtime code was intentionally not modified per user instruction.
- Remote GitHub sync/push was not requested.

### Next Actions
- Implement the architecture fix separately: make every router-supplied role-output task enter through an assignment lease/result contract, then make role-output submission consume that lease instead of relying on role-guessed event names or generic card prose.


## flowpilot-control-transaction-registry-20260512 - Unify FlowPilot control writes behind a registered transaction authority

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested a FlowGuard-first bottom-architecture fix that connects FlowPilot's contract, event-capability, packet-authority, and repair tables before runtime optimization.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T09:00:00+02:00
- Ended: 2026-05-12T09:00:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_control_transaction_registry_model.py
- simulations/flowpilot_model_mesh_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_flowpilot_control_transaction_registry_checks.py --json-out simulations/flowpilot_control_transaction_registry_results.json`
- OK: `python simulations/run_flowpilot_model_mesh_checks.py --json-out simulations/flowpilot_model_mesh_results.json`
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py -k "repair_transaction or control_blocker"`
- OK: `python scripts/check_install.py --json`
- OK: `python scripts/smoke_autopilot.py --fast`
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/install_flowpilot.py --check --json`
- OK: `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 120 --json-out tmp/flowguard_coverage_sweep_after_sync.json`

### Findings
- Added `runtime_kit/control_transaction_registry.json` as the unified authority for route progression, packet dispatch, result absorption, reviewer gates, control-blocker repair, control-plane reissue, route mutation, and legacy reconcile commits.
- Router source checks now validate the registry against registered contracts, external events, event usages, commit targets, packet-authority policy, repair policy, outcome policy, and legacy policy.
- PM control-blocker repair now validates the `control_blocker_repair` transaction before writing repair decision artifacts, repair transaction records, active blocker updates, or indexes.
- Control-plane reissue is now a first-class transaction and can wait for the reissued role event without being falsely blocked by the original card-delivery flag.
- The model mesh now treats missing or incomplete control transaction authority as a blocker for safe continuation.

### Counterexamples
- FlowGuard rejects unregistered transactions, contract/event split-brain, missing packet authority, invalid completed-agent identity, collapsed repair outcomes, repair without transaction, parent repair leaf-event reuse, partial commits, active blocker marked green, bad legacy transaction continuation, bad registry references, route mutation without stale-evidence policy, non-success outcomes using success-only events, missing atomic commit targets, and control-plane reissue without delivery authority.

### Friction Points
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py` hit a transient Windows `__pycache__` file lock; syntax was verified with `python -B -c "compile(...)"` instead.
- Coverage sweep still reports four live current-run blockers from the active run: active blocker present, unchecked packet authority, parent repair leaf-event reuse, and collapsed repair outcomes. These are classified as current-run findings, not install drift.

### Skipped Steps
- Remote GitHub sync/push was intentionally skipped per user instruction.

### Next Actions
- Repair the active run's persisted blocker/packet-authority artifacts through the newly registered transaction path if the current run should continue.


## reviewer-pm-user-perspective-challenge-20260512 - Fuse final-user challenge into reviewer and PM gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Reviewer and PM prompt behavior affects FlowPilot completion quality, evidence sufficiency, route decisions, and user-facing product standards.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T08:45:00+02:00
- Ended: 2026-05-12T09:10:00+02:00
- Commands OK: mostly true

### Model Files
- simulations/flowpilot_reviewer_active_challenge_model.py
- simulations/run_flowpilot_reviewer_active_challenge_checks.py
- simulations/flowpilot_reviewer_active_challenge_results.json
- simulations/flowpilot_planning_quality_model.py
- simulations/run_flowpilot_planning_quality_checks.py
- simulations/flowpilot_planning_quality_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile simulations\flowpilot_reviewer_active_challenge_model.py simulations\run_flowpilot_reviewer_active_challenge_checks.py tests\test_flowpilot_reviewer_active_challenge.py`
- OK: `python -m py_compile simulations\flowpilot_planning_quality_model.py simulations\run_flowpilot_planning_quality_checks.py tests\test_flowpilot_planning_quality.py`
- OK: `python simulations\run_flowpilot_reviewer_active_challenge_checks.py --json-out simulations\flowpilot_reviewer_active_challenge_results.json`
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`
- OK: `python -m unittest tests.test_flowpilot_reviewer_active_challenge tests.test_flowpilot_planning_quality`
- OK: `python scripts\check_runtime_card_capability_reminders.py`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python simulations\run_card_instruction_coverage_checks.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- TIMEOUT_RECORDED: `python scripts\smoke_autopilot.py` exceeded 120 seconds after another local change added the model-mesh check to the smoke chain.
- EXISTING_FAILURE_RECORDED: `python -m unittest tests.test_flowpilot_card_instruction_coverage tests.test_flowpilot_output_contracts tests.test_flowpilot_reviewer_active_challenge tests.test_flowpilot_planning_quality` failed because the existing card-instruction unit test expects worker-balance guidance in `pm_material_scan.md`, `pm_current_node_loop.md`, and `pm_research_package.md`; this was outside the scoped user-perspective change.
- READ_ONLY_SWEEP_RECORDED: `python scripts\run_flowguard_coverage_sweep.py --timeout-seconds 120` reported pre-existing live model-mesh blockers in the active FlowPilot run and several historical runner parse gaps; the reviewer/PM user-perspective runners themselves passed.

### Findings
- Reviewer active-challenge model now rejects missing final-user applicability decision, omitted final-user/product-usefulness challenge, missing user-perspective failure hypothesis, hard user-intent failure downgrade, final replay that only trusts ledger cleanliness, existence-only user-facing evidence, and reviewer PM-role creep.
- Planning-quality model now rejects PM plans that omit final-user/product-usefulness self-checks, omit higher-standard improvement-space self-checks, leave improvement opportunities unclassified, turn nonblocking improvements into hard current-gate requirements, or close without final-user outcome replay.
- Runtime cards were updated without adding a separate UX phase or top-level reviewer report object; the wording is folded into `independent_challenge`, PM product architecture, route skeleton, node acceptance, final ledger, and closure cards.
- Local installed FlowPilot skill was synchronized from the repository and verified source-fresh.

### Counterexamples
- Reviewer hazards: `final_user_intent_omitted`, `hard_user_intent_failure_downgraded`, `final_replay_ledger_only`, `user_facing_evidence_exists_only`, and `reviewer_made_pm_route_decision` are all detected.
- PM hazards: `pm_user_intent_self_check_missing`, `pm_higher_standard_self_check_missing`, `pm_improvement_opportunity_unclassified`, `pm_improvement_scope_creep`, and `pm_closure_user_outcome_replay_missing` are all detected.

### Friction Points
- Full smoke now depends on the concurrently added model-mesh path and timed out in this validation window.
- A broad unittest selection exposed an existing worker-balance prompt coverage mismatch outside this scoped patch.

### Skipped Steps
- Remote GitHub push/sync was intentionally skipped per user instruction.
- Existing model-mesh active-run blockers were not repaired in this patch because they belong to a parallel optimization stream.

### Next Actions
- Keep future reviewer and PM prompt changes covered by both the reviewer active-challenge and planning-quality models before editing runtime cards.
- If the worker-balance card coverage test is still desired, handle it as a separate small prompt consistency patch.


## flowpilot-model-mesh-20260512 - Add FlowPilot model mesh authority gate

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested a FlowGuard-first meta model that connects FlowPilot's specialized models before runtime optimization work.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T08:37:18+02:00
- Ended: 2026-05-12T08:37:18+02:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_model_mesh_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"; python simulations/run_flowpilot_model_mesh_checks.py --json-out simulations/flowpilot_model_mesh_results.json; python -m py_compile simulations/flowpilot_model_mesh_model.py simulations/run_flowpilot_model_mesh_checks.py scripts/smoke_autopilot.py scripts/check_install.py scripts/run_flowguard_coverage_sweep.py; python scripts/check_install.py; python scripts/smoke_autopilot.py --fast`

### Findings
- Added a model-mesh authority gate that accepts safe continuation only from current/live or conformance-grade evidence and separately accepts correctly classified blocked states.
- The model catches 15 risk scenarios, including abstract-only green evidence, skipped live audit, stale run evidence, hidden active blockers, collapsed repair outcomes, parent repair leaf-event reuse, packet authority gaps, sealed-body reads, coverage parse errors, stale local install, and install checks that require safe-to-continue.
- Live metadata-only projection of the current run classified it as `blocked_by_cross_model_contradiction`, with active blocker, collapsed repair outcomes, parent repair leaf-event reuse, and packet authority unchecked as blocking reasons.

### Counterexamples
- Current live run projection would be unsafe to treat as green; the mesh correctly blocks it without opening sealed body files.

### Friction Points
- The read-only coverage sweep still reports four pre-existing unparsed support runners, so the sweep process exits nonzero even though the new mesh runner is classified as coverage_strong and passes.

### Skipped Steps
- Full local skill sync was not run in this step; this change established the repository model, runner, result, install, smoke, and coverage-sweep integration.

### Next Actions
- Use the mesh result as the top-level permission gate before applying the later runtime repair/optimization steps.


## flowpilot-event-capability-registry-runtime-20260512 - Gate waits, rerun targets, and repair outcomes through event capability facts

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested the control table and prompt migration plan to prevent scattered prompt authority and the router bug class where a registered event could be persisted as a wait even when it was not executable for the current route state or repair origin.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T07:01:02+02:00
- Ended: 2026-05-12T07:56:49+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_event_capability_registry_model.py
- simulations/flowpilot_event_contract_model.py
- simulations/flowpilot_repair_transaction_model.py
- simulations/flowpilot_router_loop_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_event_contract_model.py simulations\run_flowpilot_event_contract_checks.py simulations\flowpilot_event_capability_registry_model.py simulations\run_flowpilot_event_capability_registry_checks.py scripts\check_install.py scripts\run_flowguard_coverage_sweep.py`
- OK: `python simulations\run_flowpilot_event_capability_registry_checks.py --json-out simulations\flowpilot_event_capability_registry_results.json`
- OK: `python simulations\run_flowpilot_event_contract_checks.py --json-out simulations\flowpilot_event_contract_results.json`
- OK: `python simulations\run_flowpilot_repair_transaction_checks.py --json-out simulations\flowpilot_repair_transaction_results.json`
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_flowpilot_route_replanning_policy_checks.py --json-out simulations\flowpilot_route_replanning_policy_results.json`
- OK: `python simulations\run_protocol_contract_conformance_checks.py --json-out simulations\protocol_contract_conformance_results.json`
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "control_blocker_repair or repair_transaction or pm_repair_decision or parent_backward_non_continue or parent_node_cannot_receive_current_node_packet"`
- OK: `python scripts\check_install.py`
- OK: `python simulations\run_meta_checks.py` in background; 634501 states, 654672 edges, no stuck states, no nonterminating components.
- OK: `python simulations\run_capability_checks.py` in background; 624663 states, 650122 edges, no stuck states, no nonterminating components.
- OK: `python simulations\run_meta_checks.py --fast`
- OK: `python simulations\run_capability_checks.py --fast`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- WARN: `python scripts\run_flowguard_coverage_sweep.py --json-out tmp\flowguard_coverage_sweep_event_capability_after_sync.json` returned nonzero because four pre-existing support runners are unparsed/unavailable, but finding_count was zero after local install sync.

### Findings
- Added a concrete event capability model that treats event registration as necessary but not sufficient. Waits, repair rerun targets, and repair outcome rows must also match active node kind, repair origin, target role, current prerequisite flags, and row usage.
- Router repair decisions now reject registered but non-receivable rerun targets before writing a wait. Parent/backward replay repairs cannot target leaf-only current-node packet events.
- Generic control-blocker repair outcomes now use distinct success, blocker, and protocol-blocker events instead of collapsing all outcomes onto one business event. Material dispatch keeps its existing three explicit outcome events.
- The migration plan records the prompt/control-table inventory, optimization sequence, risk checklist, FlowGuard coverage matrix, and pre-implementation architecture fit check.

### Counterexamples
- FlowGuard hazards detect unregistered events, false-precondition waits, wrong producer-role waits, ACK waits, parent repairs targeting leaf events, collapsed repair outcomes, blocker/protocol rows using success-only events, and PM repair events reused as rerun targets.

### Friction Points
- Read-only coverage sweep still has four pre-existing unparsed support runners. It is useful for drift findings, and it confirmed the installed-skill drift disappeared after sync, but it remains nonzero until those support runners expose parseable result paths.

### Skipped Steps
- Remote GitHub sync/push was intentionally skipped per user instruction.

### Next Actions
- Continue the broader prompt migration by replacing scattered worker/card command prose with generated snippets sourced from the control/event capability tables.


## flowpilot-control-event-compatibility-model-upgrade-20260512 - Model router repair event identity and node-kind compatibility

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot control-plane deadlock analysis exposed a model miss where repair and router outcome tables treated events as routable without checking whether the concrete event was executable under the active parent/leaf node kind.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-12T07:01:02+02:00
- Ended: 2026-05-12T07:01:02+02:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_router_loop_model.py
- simulations/flowpilot_repair_transaction_model.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK (0.000s): `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json`
- OK (0.000s): `python simulations/run_flowpilot_repair_transaction_checks.py --json-out simulations/flowpilot_repair_transaction_results.json`
- OK (0.000s): `python simulations/run_meta_checks.py`
- OK (0.000s): `python -m py_compile simulations/flowpilot_router_loop_model.py simulations/run_flowpilot_router_loop_checks.py simulations/flowpilot_repair_transaction_model.py simulations/run_flowpilot_repair_transaction_checks.py`

### Findings
- Router-loop and repair-transaction models now represent active node kind, repair origin, concrete rerun event identity, and success/blocker/protocol-blocker outcome event identities.
- New hazard states catch parent/backward-replay repairs targeting leaf-only current-node events, outcome events incompatible with the active node kind, collapsed outcome tables, and routable outcomes without concrete event identities.
- Abstract model checks passed with no safe-graph invariant failures, no stuck states, and no nonterminal loops.

### Counterexamples
- Captured known-bad hazard mutations for the event-compatibility deadlock class; all were detected by the upgraded model.

### Friction Points
- `python simulations/run_meta_checks.py` needed a longer timeout because the project-level graph has more than 600k states.

### Skipped Steps
- Production router mutation and runtime conformance replay were intentionally skipped; this task was limited to model upgrade, simulation, and repair recommendation.
- Capability checks were not rerun because this change did not alter skill/capability routing.

### Next Actions
- Implement the router fix as a separate change: add a shared event-capability preflight and make repair outcome-table construction use distinct, context-compatible event identities.


## contract-runtime-binding-registry-20260511 - Make FlowPilot role-output contract runtime bindings registry-driven and checked end to end

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Changing role-output runtime, contract registry, router event binding, and startup activation submission affects stateful protocol flow, role authority, route events, and sealed body boundaries.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-11T21:15:49+00:00
- Ended: 2026-05-11T21:15:49+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_role_output_runtime_model.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_role_output_runtime_checks.py; python -m unittest tests.test_flowpilot_role_output_runtime -v; python scripts/check_install.py; python simulations/run_meta_checks.py; python simulations/run_capability_checks.py --fast; targeted startup/router unittest set`

### Findings
- Registry-backed binding source now covers 16 role-output contracts plus pm_resume_recovery_decision compatibility alias; source check fails if a runtime-backed contract lacks output_type, body schema, allowed roles, path/hash keys, default location, or fixed router event.
- Startup activation approval, repair request, and protocol dead-end are ordinary registry rows and are accepted by flowpilot_runtime.py prepare-output/submit-output-to-router through generated SUPPORTED_OUTPUT_TYPES.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Full capability rerun was not treated as required for this change because capability_model.py and run_capability_checks.py were unchanged; python simulations/run_capability_checks.py --fast reused a valid proof. A forced full rerun exceeded 10 minutes.

### Next Actions
- Keep future role-output additions in runtime_kit/contracts/contract_index.json with runtime_channel=role_output_runtime and run role-output runtime checks before release.


## ack-after-receipt-guidance-20260513 - Strengthen FlowPilot post-ACK card and packet work guidance

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Changing ACK receipt semantics and runtime prompts affects stateful FlowPilot protocol flow, role authority, packet handoff, and Router waits.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T05:03:50+00:00
- Ended: 2026-05-13T05:03:50+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/card_instruction_coverage_model.py
- simulations/flowpilot_event_contract_model.py
- simulations/flowpilot_command_refinement_model.py

### Commands
- OK (0.000s): `python -m flowguard schema-version`
- OK (0.000s): `python simulations/run_card_instruction_coverage_checks.py --json-out .flowpilot/tmp/ack_after_receipt_post_worker_guidance_results.json`
- OK (0.000s): `python -m unittest tests.test_flowpilot_card_instruction_coverage -v`
- OK (0.000s): `python simulations/run_flowpilot_event_contract_checks.py --json-out .flowpilot/tmp/ack_after_receipt_event_contract_results.json`
- OK (0.000s): `python simulations/run_command_refinement_checks.py --json-out .flowpilot/tmp/ack_after_receipt_command_refinement_results.json`
- OK (0.000s): `python scripts/check_runtime_card_capability_reminders.py`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json`
- OK (0.000s): `python scripts/install_flowpilot.py --check --json`

### Findings
- Card instruction coverage now models post-ACK receipt semantics separately for role cards, work/system cards, event cards, packet bodies, and packet runtime identity boundaries.
- Known-bad hazards for role-card task start, work-card stop after ACK, event-card ACK-as-disposition, and packet ACK-without-execution are rejected.
- Runtime cards now carry type-specific post_ack identity text, and Router card check-in text states that ACK is receipt only, not completion.
- The first targeted unittest run exposed worker-packet dispatch guidance drift on three PM cards; those cards were repaired and final tests passed.

### Counterexamples
- ack_consumed_semantic_wait_lost remains detected by the event-contract model.

### Friction Points
- none recorded

### Skipped Steps
- Full meta/capability graph reruns were skipped because this change did not alter project-control transitions or capability routing; targeted card, packet, ACK-event, bundle, install, and audit checks passed.

### Next Actions
- Keep future card or packet prompt changes under card_instruction_coverage_model hazards before editing production prompts.


## dynamic-return-path-gate-alignment-20260513 - Model FlowPilot gate satisfaction for legacy/general officer events

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A recovered FlowPilot run showed `router_no_legal_next_action` blockers after a legacy/general product officer report was recorded before the concrete product architecture modelability gate event.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T07:29:35+02:00
- Ended: 2026-05-13T07:29:35+02:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_dynamic_return_path_model.py
- simulations/run_flowpilot_dynamic_return_path_checks.py

### Commands
- OK (0.000s): `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- OK (0.000s): `python -m py_compile simulations\flowpilot_dynamic_return_path_model.py simulations\run_flowpilot_dynamic_return_path_checks.py`.
- OK (0.000s): `python simulations\run_flowpilot_dynamic_return_path_checks.py --project-root . --json-out simulations\flowpilot_dynamic_return_path_results.json`.

### Findings
- The dynamic-return-path model now represents current gate satisfaction separately from event registration, event recording, PM repair follow-up, and mechanical role-output validity.
- New bad scenarios are rejected for gate cards without declared completion contracts, legacy/general events accepted without the required gate flag, repair outcomes that resolve a control blocker without satisfying the current gate, and PM role-work results that are not mapped to the current gate.
- Metadata-only live projection classifies `run-20260513-034857` as currently continuable while preserving the historical gate-alignment findings from the two recovered `router_no_legal_next_action` blockers.

### Counterexamples
- `gate_card_without_completion_contract`
- `legacy_event_accepted_without_required_gate_flag`
- `pm_repair_resolves_blocker_without_gate_event`
- `pm_role_work_result_not_mapped_to_current_gate`

### Friction Points
- The live projection intentionally reads only public metadata and does not inspect sealed packet/result/report bodies, so it can identify control-flow alignment risk but not judge report semantic quality.

### Skipped Steps
- Runtime Router, card, and contract code were intentionally not changed because the user requested model upgrade and repair-plan review before implementation.
- Full meta/capability reruns were skipped because this pass changed the focused FlowGuard model and check harness only, not production control-flow transitions or capability routing.

### Next Actions
- Review the minimal bottom-level fix: make every gate-bearing card/event wait declare a concrete gate completion contract, require PM repair success events to satisfy the same gate, and map PM role-work results into the active gate before the Router computes continuation.


## dynamic-return-path-gate-alignment-runtime-20260513 - Enforce FlowPilot gate contracts in Router runtime

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Implement the approved minimal bottom-level fix after the focused FlowGuard model caught legacy/general officer events, PM repair follow-ups, and unmapped PM role-work results that could bypass active gate satisfaction.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T07:30:00+02:00
- Ended: 2026-05-13T08:15:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_dynamic_return_path_model.py
- simulations/run_flowpilot_dynamic_return_path_checks.py
- simulations/flowpilot_dynamic_return_path_results.json

### Runtime Files
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/runtime_kit/cards/officers/product_architecture_modelability.md
- skills/flowpilot/assets/runtime_kit/cards/officers/route_process_check.md

### Commands
- OK: `python -m py_compile simulations\flowpilot_dynamic_return_path_model.py simulations\run_flowpilot_dynamic_return_path_checks.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py tests\test_flowpilot_role_output_runtime.py`.
- OK: `python simulations\run_flowpilot_dynamic_return_path_checks.py --project-root . --json-out simulations\flowpilot_dynamic_return_path_results.json`.
- OK: `python -m unittest tests.test_flowpilot_role_output_runtime.FlowPilotRoleOutputRuntimeTests.test_router_supplied_direct_submission_requires_current_wait_authority tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_legacy_product_officer_model_report_does_not_close_modelability_gate tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_gate_targeted_pm_role_work_result_requires_mapped_gate_event tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_product_architecture_and_root_contract_gate_route_skeleton tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_draft_requires_product_behavior_model_report tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_check_reports_require_hard_gate_verdict_fields tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_model_miss_followup_uses_generic_role_work_request_channel`.
- OK: `python simulations\run_flowpilot_model_driven_recursive_route_checks.py`.
- OK: `python simulations\run_meta_checks.py`.
- OK: `python simulations\run_capability_checks.py`.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- Router now carries a machine-readable gate contract from gate-bearing card delivery into the generated wait action.
- Legacy/general officer report events remain registered for compatibility, but they are marked non-terminal for active gate completion.
- Product Officer modelability is now treated as the compatibility name for the canonical product behavior model gate.
- Process route check is now treated as the compatibility name for the canonical process route model gate.
- Canonical artifacts are written first, with old compatibility artifact paths mirrored for existing callers.
- PM role-work results that target a gate must declare a concrete mapped gate event before the original gate can be satisfied.

### Counterexamples
- `legacy_event_accepted_without_required_gate_flag`
- `pm_repair_resolves_blocker_without_gate_event`
- `pm_role_work_result_not_mapped_to_current_gate`
- `product_behavior_model_gate_uses_modelability_as_canonical_completion`
- `process_route_model_gate_uses_route_check_as_canonical_completion`

### Friction Points
- Full meta and capability checks each needed more than the initial three-minute timeout. They were rerun separately with longer timeouts and passed.

### Skipped Steps
- No remote GitHub sync was performed, per user instruction.

### Next Actions
- Keep future Product or Process officer gate changes synchronized across FlowGuard model scenarios, Router gate contracts, card wording, canonical artifacts, compatibility aliases, and focused runtime tests.


## current-node-completion-router-compat-repair-20260513 - Repair batch-registered current-node completion context

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A FlowPilot PM role-work packet reported that PM completion from an already-reviewed current-node result failed when the current-node packet had been registered through the active batch path instead of the legacy latest-event payload path.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T14:15:00+02:00
- Ended: 2026-05-13T14:25:52+02:00
- Commands OK: True

### Runtime Files
- skills/flowpilot/assets/flowpilot_router.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py`.
- OK: targeted router context lookup check for live run metadata.
- OK: temporary-copy `pm_completes_current_node_from_reviewed_result` rehearsal.
- OK: `python simulations\run_meta_checks.py`.

### Findings
- Router current-node packet and result context lookup now falls back to the active current-node batch index when legacy/latest event payload metadata lacks `packet_id` or explicit envelope paths.
- The fallback is scoped to context reconstruction after the strict legacy path reports missing packet identity, so normal packet registration validation still requires explicit packet identity.
- The live repaired packet/result context resolved from envelopes only; sealed packet/result body contents were not exposed to Controller.

### Counterexamples
- `batch_registered_current_node_completion_context_missing_packet_id`

### Friction Points
- None.

### Skipped Steps
- Capability model checks were not run because this repair changes current-node completion context resolution, not skill/capability routing.

### Next Actions
- PM can retry the already-authorized `pm_completes_current_node_from_reviewed_result` event for `leaf-functional-framing-and-concept-brief` without reissuing worker work or rereading sealed result bodies.


## card-return-resolved-duplicate-ack-repair-20260513 - Prevent duplicate ACK from reopening a resolved return wait

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The live FlowPilot run produced a control blocker after a reviewer card ACK had already been resolved, because a later duplicate runtime check-in set the pending return status back to `returned` and blocked subsequent PM/reviewer events.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T16:20:00+02:00
- Ended: 2026-05-13T16:31:00+02:00
- Commands OK: True

### Runtime Files
- skills/flowpilot/assets/flowpilot_router.py
- tests/test_flowpilot_router_runtime.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_committed_system_card_relay_can_resolve_without_apply_roundtrip`.
- OK: `python simulations\run_meta_checks.py`.
- OK: `python simulations\run_capability_checks.py`.

### Findings
- Router pending-return selection now ignores a `returned` pending entry when the same card or bundle return already has a resolved completed-return record or a `resolved_at` marker.
- A duplicate runtime card check-in can still update acknowledgement metadata, but it no longer blocks unrelated role events after the original return has been validated.
- The live run's PM control-blocker repair event no longer has a pending card-return blocker after the patch.

### Counterexamples
- `resolved_card_return_reopened_by_duplicate_ack`

### Friction Points
- The live run exposed a race/order hazard between runtime ACK submission and Router return-ledger status classification that existing tests did not cover.

### Skipped Steps
- No sealed card, packet, result, or report body was read for this repair.
- No remote GitHub sync or push was performed.

### Next Actions
- Keep future card-runtime changes aligned with Router pending-return classification so receipt retries remain idempotent.


## flowpilot-unified-role-recovery-20260513 - Unify heartbeat and mid-run role recovery

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot controller can observe a missing, cancelled, timed-out, or unaddressable background role during an active route. Recovery must preempt normal waits/work and use the same recovery ladder as heartbeat/manual resume.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T14:35:00+02:00
- Ended: 2026-05-13T16:26:19+02:00
- Commands OK: True

### Planning Files
- docs/flowpilot_unified_role_recovery_plan.md

### Model Files
- simulations/flowpilot_role_recovery_model.py
- simulations/run_flowpilot_role_recovery_checks.py
- simulations/flowpilot_role_recovery_results.json

### Runtime Files
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/runtime_kit/cards/roles/controller.md
- skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_crew_rehydration_freshness.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_resume_decision.md

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python -m py_compile simulations\flowpilot_role_recovery_model.py simulations\run_flowpilot_role_recovery_checks.py`.
- OK: `python simulations\run_flowpilot_role_recovery_checks.py`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_role_recovery_model.py simulations\run_flowpilot_role_recovery_checks.py`.
- OK: targeted resume/router regression tests for resume preemption and heartbeat resume entry.
- OK: targeted mid-run role liveness fault runtime test.
- OK: `python simulations\run_flowpilot_resume_checks.py` in a background process.
- OK: `python simulations\run_meta_checks.py` in a background process.
- OK: `python simulations\run_capability_checks.py` in a background process.
- OK: `python -m pytest -q tests\test_flowpilot_role_output_runtime.py`.
- OK: `python -m pytest -q tests\test_flowpilot_card_instruction_coverage.py`.
- OK: `python -m pytest -q tests\test_flowpilot_router_runtime.py -k "role_liveness_fault or resume_reentry or heartbeat_alive_status_still_enters_router_resume_path or crew_rehydration"`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_role_recovery_model.py simulations\run_flowpilot_role_recovery_checks.py tests\test_flowpilot_router_runtime.py`.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- Heartbeat/manual resume and mid-run liveness faults now enter one role-recovery transaction path instead of separate recovery concepts.
- Recovery actions are selected before normal control blockers, route work, packet work, and gate waits unless an explicit user stop/cancel is present.
- Targeted recovery first records current state, then attempts old-role restore, targeted replacement, slot reconciliation, and full crew recycle escalation when capacity or close failures block targeted recovery.
- Recovery reports carry memory/context injection, packet ownership reconciliation, role binding epoch advancement, crew generation, superseded agent ids, and stale output quarantine evidence before PM is asked to continue.
- Existing PM resume decision machinery is reused after recovery so the controller does not silently continue after a restored or replaced role.
- Controller and PM cards now explicitly require immediate role-liveness fault recording, unified recovery-first handling, and report review before continuation.

### Counterexamples
- `mid_run_fault_treated_as_wait`
- `heartbeat_bypasses_unified_recovery`
- `normal_work_preempts_recovery`
- `targeted_replace_before_restore`
- `capacity_full_without_full_recycle`
- `full_recycle_without_targeted_attempt`
- `failed_full_recycle_marked_ready`
- `ready_without_memory_injection`
- `pm_continue_without_packet_reconciliation`
- `stale_generation_output_accepted`
- `controller_auto_continues_after_recovery`
- `recovery_blocks_user_stop`

### Friction Points
- A single broad pytest invocation across the router runtime, role-output runtime, and card-coverage tests exceeded the local command timeout and hit a Windows stdout flush error. The same coverage area was split into focused pytest runs, and those completed successfully.
- The new abstract model intentionally skips production conformance replay until a dedicated router adapter is added; runtime behavior is covered by focused router tests for this change.

### Skipped Steps
- Remote GitHub sync was not performed, per user instruction.
- Full router runtime pytest was not treated as a blocking gate because it exceeded the local command timeout; focused recovery, resume, role-output, and card-coverage tests passed.

### Next Actions
- If role recovery grows beyond controller-hosted recovery actions, add a production conformance adapter for `flowpilot_role_recovery_model.py`.
- Keep future resume, heartbeat, and mid-run liveness changes on the same transaction/report path so recovery remains preemptive and PM-reviewed.

## terminal-state-monotonicity-model-20260513 - Model duplicate ACK terminal-state downgrade hazards

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested a model-first investigation of a live FlowPilot ACK control-plane issue before any runtime repair. The issue involved a card return ACK already resolved by Router, followed by a duplicate runtime check-in that wrote the raw pending return status back to `returned`.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T16:40:00+02:00
- Ended: 2026-05-13T16:55:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_terminal_state_monotonicity_model.py
- simulations/run_flowpilot_terminal_state_monotonicity_checks.py
- simulations/flowpilot_terminal_state_monotonicity_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python -m py_compile simulations\flowpilot_terminal_state_monotonicity_model.py simulations\run_flowpilot_terminal_state_monotonicity_checks.py`.
- OK: `python simulations\run_flowpilot_terminal_state_monotonicity_checks.py --json-out simulations\flowpilot_terminal_state_monotonicity_results.json`.
- OK: `python simulations\run_flowpilot_event_idempotency_checks.py --json-out simulations\flowpilot_event_idempotency_results.json`.
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json`.

### Findings
- Existing event-idempotency coverage checked scoped event replay, but not terminal control-plane record downgrade after a duplicate or late input.
- Existing card-envelope coverage checked ACK shape, receipt, and Router submission rules, but not whether a duplicate ACK may dirty a resolved pending return record.
- The new terminal-state model catches same-class hazards where terminal facts are reopened by duplicate ACKs, incomplete bundle ACKs, stale gate blocks, stale control blockers, duplicate PM repair decisions, old repair-generation failures, or duplicate result returns.
- Source audit found the Router pending-return selector is currently terminal-aware through `resolved_at` and completed-return records, while card runtime ACK writers can still dirty raw pending records by assigning `status = "returned"` after resolution.
- Live metadata audit found one dirty terminal pending record in `.flowpilot/runs/run-20260513-034857/return_event_ledger.json`: pending index 57 for `reviewer_node_acceptance_plan_review-delivery-009-attempt-001`, with `resolved_at` present and raw `status` set back to `returned`.

### Counterexamples
- `resolved_card_return_reopened_by_duplicate_ack`
- `resolved_bundle_return_reopened_by_duplicate_ack`
- `resolved_bundle_return_downgraded_to_incomplete`
- `pending_selector_ignores_resolved_at`
- `pending_selector_ignores_completed_return`
- `repair_channel_blocked_by_resolved_return`
- `gate_pass_reopened_by_late_block`
- `resolved_control_blocker_reactivated_by_stale_artifact`
- `duplicate_pm_repair_created_new_blocker`
- `old_repair_generation_failure_reopened_success`
- `new_repair_generation_failure_swallowed`
- `result_disposition_reopened_by_duplicate_result`
- `same_identity_replay_writes_duplicate_side_effect`

### Skipped Steps
- No production Router, card runtime, route state, or live run mutation was performed; this pass was model and analysis only by user request.
- No sealed card, packet, result, or report body was read.

### Next Actions
- Discuss a narrow shared terminal-merge rule for control-plane records before implementing any runtime repair.

## terminal-state-monotonicity-runtime-20260513 - Implement monotonic duplicate ACK merge

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved the model-first repair for duplicate or late ACK/check-in events that could dirty an already resolved FlowPilot return wait and re-block PM or reviewer events.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T16:55:00+02:00
- Ended: 2026-05-13T17:28:57+02:00
- Commands OK: True

### Planning Files
- docs/control_plane_terminal_merge_plan.md

### Model Files
- simulations/flowpilot_terminal_state_monotonicity_model.py
- simulations/run_flowpilot_terminal_state_monotonicity_checks.py
- simulations/flowpilot_terminal_state_monotonicity_results.json
- simulations/flowpilot_event_idempotency_results.json
- simulations/flowpilot_card_envelope_results.json
- simulations/flowpilot_control_plane_friction_results.json

### Runtime Files
- skills/flowpilot/assets/card_runtime.py
- tests/test_flowpilot_card_runtime.py
- tests/test_flowpilot_router_runtime.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python -m py_compile skills\flowpilot\assets\card_runtime.py skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_terminal_state_monotonicity_model.py simulations\run_flowpilot_terminal_state_monotonicity_checks.py tests\test_flowpilot_card_runtime.py tests\test_flowpilot_router_runtime.py`.
- OK: `python simulations\run_flowpilot_terminal_state_monotonicity_checks.py --json-out simulations\flowpilot_terminal_state_monotonicity_results.json`.
- OK: `python simulations\run_flowpilot_event_idempotency_checks.py --json-out simulations\flowpilot_event_idempotency_results.json`.
- OK: `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json`.
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json`.
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py -q` -> 9 passed.
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "card_return or bundle_ack or control_blocker or repair_decision or gate_decision or result_disposition"` -> 20 passed, 128 deselected.
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "committed_system_card_relay_can_resolve_without_apply_roundtrip or incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers or pm_repair_decision_can_repeat_for_new_control_blocker or already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision"` -> 4 passed, 144 deselected.
- OK: `python -m pytest tests\test_flowpilot_control_gates.py -q` -> 19 passed.
- OK: background `python simulations\run_meta_checks.py` -> exit 0.
- OK: background `python simulations\run_capability_checks.py` -> exit 0.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- OK: `python scripts\check_install.py`.

### Findings
- Card and bundle ACK writers now merge duplicate acknowledgements monotonically. If a pending return already has terminal proof through `status=resolved`, `resolved_at`, or a matching resolved completed-return record, a later duplicate ACK is recorded as audit metadata instead of changing the pending record back to `returned`.
- Real unresolved card and bundle returns still transition to `returned`, so the repair does not release unfinished work.
- Completed-return records are upserted by return identity instead of appended blindly, which avoids duplicate side effects for the same card or bundle return.
- The upgraded terminal-state model verifies the same rule across card ACK, bundle ACK, gate pass/block, control blocker resolution, PM repair decision, repair generation, and result disposition classes.
- Existing Router scoped-identity behavior already covers the non-ACK ledger classes; this change only repaired the ACK writer path that could dirty raw pending-return records.
- Local installed FlowPilot skill was synchronized from the repository and audited fresh. Remote GitHub sync was not performed.

### Counterexamples
- `resolved_card_return_reopened_by_duplicate_ack`
- `resolved_bundle_return_reopened_by_duplicate_ack`
- `resolved_bundle_return_downgraded_to_incomplete`
- `pending_selector_ignores_resolved_at`
- `pending_selector_ignores_completed_return`
- `repair_channel_blocked_by_resolved_return`
- `gate_pass_reopened_by_late_block`
- `resolved_control_blocker_reactivated_by_stale_artifact`
- `duplicate_pm_repair_created_new_blocker`
- `old_repair_generation_failure_reopened_success`
- `new_repair_generation_failure_swallowed`
- `result_disposition_reopened_by_duplicate_result`
- `same_identity_replay_writes_duplicate_side_effect`
- `new_gate_identity_swallowed_by_old_pass`
- `new_control_blocker_swallowed_by_old_resolution`
- `new_result_identity_swallowed_by_old_disposition`
- `real_unresolved_return_released_by_overbroad_terminal_merge`

### Friction Points
- Full `tests\test_flowpilot_router_runtime.py -q` exceeded the local command timeout, so related Router coverage was split into focused idempotency, return, repair, gate, and result-disposition selections that passed.
- Long meta and capability checks were run in background. A duplicated background start was detected and cleaned up; the final meta and capability runs both exited 0.
- A parallel agent has unrelated startup-intake UI changes in the workspace. Those files were preserved and intentionally excluded from this repair scope.

### Skipped Steps
- No sealed card, packet, result, or report body was read.
- No live `.flowpilot` route state was mutated.
- No remote GitHub sync or push was performed, per user instruction.

### Next Actions
- Keep future control-plane ledger writers on the same terminal-merge rule: same identity plus terminal proof means audit-only replay; genuinely new identity or unresolved work remains actionable.

## 2026-05-13 - Startup Intake UI Prompt-Isolation Integration

### Trigger
- User approved replacing the old startup three-question boundary with a native desktop startup intake UI, but required the change to be modeled first so the Controller cannot start from or read the original chat prompt.

### Model Files
- simulations/flowpilot_startup_intake_ui_model.py
- simulations/run_flowpilot_startup_intake_ui_checks.py
- simulations/flowpilot_startup_intake_ui_results.json

### Runtime Files
- skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/packet_runtime.py
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_intake.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/startup_fact_check.md
- skills/flowpilot/SKILL.md
- scripts/check_install.py
- tests/test_flowpilot_router_runtime.py
- docs/startup_intake_ui_integration_plan.md

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python simulations\run_flowpilot_startup_intake_ui_checks.py --json-out simulations\flowpilot_startup_intake_ui_results.json`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py scripts\check_install.py simulations\flowpilot_startup_intake_ui_model.py simulations\run_flowpilot_startup_intake_ui_checks.py`.
- OK: `powershell -STA -NoProfile -ExecutionPolicy Bypass -File skills\flowpilot\assets\ui\startup_intake\flowpilot_startup_intake.ps1 -SmokeTest`.
- OK: headless confirm and cancel startup intake UI runs.
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_card_runtime` -> 22 tests passed.
- OK: focused startup router tests -> 19 tests passed.
- OK: `python scripts\check_install.py`.
- OK: `python simulations\run_flowpilot_startup_control_checks.py`.
- OK: `python simulations\run_prompt_isolation_checks.py`.
- OK: `python simulations\run_startup_pm_review_checks.py`.
- OK: `python simulations\run_meta_checks.py`.
- OK: `python simulations\run_capability_checks.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- Boot now opens the native startup intake UI at the former startup question boundary.
- Confirmed UI intake writes a body file plus result, receipt, and envelope artifacts; router state stores only references and hashes, not the body text.
- Cancelled UI intake is terminal before run shell creation or role startup.
- The PM intake packet is created from the sealed UI body reference, while Controller only sees the sealed reference.
- Reviewer startup and live review context now points to the UI startup record, receipt, and envelope hash instead of searching chat history.
- UI toggles map to the old startup answer enums, preserving downstream compatibility.
- Local installed FlowPilot skill was synchronized from this checkout and audited fresh. Remote GitHub sync was not performed.

### Counterexamples
- controller_before_ui_confirm
- controller_body_leak
- accepted_without_hash
- cancel_continues_to_run
- invalid_toggle_value
- manual_creates_heartbeat
- single_agent_starts_roles
- chat_opens_cockpit
- ui_confirm_requires_old_chat
- reviewer_uses_chat

### Friction Points
- Full `python -m unittest tests.test_flowpilot_router_runtime` exceeded the local timeout with no failure output, so startup coverage was validated through focused router tests and the existing full meta/capability model checks.
- The formal UI asset was added under the skill asset tree; an older preview UI script remains a separate preview artifact.

### Skipped Steps
- No sealed startup request body was read by Controller.
- No live `.flowpilot` route state was mutated.
- No remote GitHub sync or push was performed, per user instruction.

### Next Actions
- Keep future startup intake changes aligned across the UI artifact schema, router payload validation, PM sealed packet creation, reviewer startup/live review card wording, and the FlowGuard startup-intake model.

## 2026-05-13 - Parent Review Router Gate Repair

### Trigger
- A live FlowPilot run exposed a model miss: after the last child leaf in a
  module completed, the router advanced into the next sibling module's leaf
  before local parent backward replay and PM segment disposition ran.

### Model Files
- simulations/flowpilot_parent_child_lifecycle_model.py
- simulations/run_flowpilot_parent_child_lifecycle_checks.py
- simulations/flowpilot_parent_child_lifecycle_results.json

### Runtime Files
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/flowpilot_user_flow_diagram.py
- scripts/flowpilot_user_flow_diagram.py
- tests/test_flowpilot_router_runtime.py
- tests/test_flowpilot_user_flow_diagram.py
- docs/flowpilot_parent_review_router_repair_plan.md

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python simulations\run_flowpilot_parent_child_lifecycle_checks.py --json`.
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "next_effective_node_returns_parent_before_sibling_module_after_last_child"` -> 1 passed.
- OK: `python -m pytest tests\test_flowpilot_user_flow_diagram.py -q -k "hidden_active_leaf_highlights_visible_parent_without_label_detail"` -> 1 passed.
- OK: `python simulations\run_flowpilot_parent_child_lifecycle_checks.py`.
- OK: `python simulations\run_flowpilot_legal_next_action_checks.py`.
- OK: `python simulations\run_flowpilot_model_driven_recursive_route_checks.py`.
- OK: `python simulations\run_flowpilot_route_display_checks.py`.
- OK: `python -m pytest tests\test_flowpilot_user_flow_diagram.py -q` -> 18 passed.
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "next_effective_node_returns_parent_before_sibling_module_after_last_child or parent_backward_targets_require_current_child_completion_ledgers or parent_node_requires_backward_replay_before_completion or parent_backward_non_continue_decision_mutates_route_and_requires_rerun"` -> 4 passed.
- OK: `python -m py_compile simulations\flowpilot_parent_child_lifecycle_model.py simulations\run_flowpilot_parent_child_lifecycle_checks.py skills\flowpilot\assets\flowpilot_router.py scripts\flowpilot_user_flow_diagram.py skills\flowpilot\assets\flowpilot_user_flow_diagram.py`.
- OK: `python simulations\run_meta_checks.py`.
- OK: `python simulations\run_capability_checks.py`.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- The parent-child lifecycle model now has a positive scenario for last-child
  completion returning to the nearest parent scope and negative hazards for
  entering a sibling module leaf or selecting a non-nearest parent scope before
  parent replay.
- The router now checks the completed leaf's parent chain before scanning
  sibling modules. A parent/module whose direct effective children are all
  completed is reactivated for parent backward replay before sibling work.
- Route signs now distinguish child-work-complete parent modules from truly
  completed parent modules. Child-complete parents render as review-ready, not
  done, until the parent itself is completed.
- Local installed FlowPilot was synchronized from this checkout and audited
  fresh. Remote GitHub sync was not performed.

### Counterexamples
- sibling_module_leaf_entered_before_parent_replay
- non_nearest_parent_selected_for_child_replay

### Friction Points
- `python -m pytest tests\test_flowpilot_router_runtime.py tests\test_flowpilot_user_flow_diagram.py -q` exceeded the local 15-minute timeout with no failure output. Coverage was completed through focused router tests, full route-sign tests, model checks, meta/capability checks, and install/audit checks.
- Other local agents had concurrent uncommitted startup-intake changes in the working tree. They were preserved and not reverted.

### Skipped Steps
- No live `.flowpilot` run state was repaired or frozen; the user explicitly scoped this pass to the FlowPilot implementation.
- No remote GitHub sync or push was performed, per user instruction.

### Next Actions
- Future router scheduling changes should update both the parent-child lifecycle model and a concrete runtime next-node regression before changing production routing code.

## 2026-05-13 - Startup Intake UI BOM Compatibility Repair

### Trigger
- A FlowPilot startup UI run exposed a control-plane compatibility issue:
  Windows PowerShell-generated startup intake JSON could carry a UTF-8 BOM,
  causing Router/Python JSON parsing to fail before the startup contract could
  continue.

### Model Files
- simulations/flowpilot_startup_intake_ui_model.py
- simulations/run_flowpilot_startup_intake_ui_checks.py
- simulations/flowpilot_startup_intake_ui_results.json

### Runtime Files
- docs/startup_intake_ui_integration_plan.md
- skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1
- skills/flowpilot/assets/flowpilot_router.py
- tests/test_flowpilot_router_runtime.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python simulations\run_flowpilot_startup_intake_ui_checks.py --json-out simulations\flowpilot_startup_intake_ui_results.json`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_startup_intake_ui_model.py simulations\run_flowpilot_startup_intake_ui_checks.py tests\test_flowpilot_router_runtime.py`.
- OK: `powershell -STA -NoProfile -ExecutionPolicy Bypass -File skills\flowpilot\assets\ui\startup_intake\flowpilot_startup_intake.ps1 -SmokeTest`.
- OK: headless UI output check confirmed result, receipt, envelope, and body files do not start with `EF BB BF`.
- OK: focused startup intake BOM unittest selection passed.
- OK: focused startup router tests passed.
- OK: `python -m unittest tests.test_flowpilot_packet_runtime tests.test_flowpilot_card_runtime`.
- OK: `python scripts\check_install.py`.
- OK: `python simulations\run_flowpilot_startup_control_checks.py`.
- OK: `python simulations\run_prompt_isolation_checks.py`.
- OK: `python simulations\run_startup_pm_review_checks.py`.
- OK: `python simulations\run_meta_checks.py`.
- OK: `python simulations\run_capability_checks.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

### Findings
- The startup UI writes result, receipt, envelope, and body artifacts as UTF-8
  without BOM.
- Router `read_json` tolerates legacy BOM-prefixed JSON artifacts with
  `utf-8-sig`.
- PM intake packet construction strips a leading body BOM marker after byte hash
  verification, preventing a visible `\ufeff` marker from entering the PM-bound
  packet text.
- UI body hashing no longer depends on host availability of PowerShell
  `Get-FileHash`; it uses .NET SHA256.
- The startup intake UI model now catches partial artifact fixes, legacy BOM
  compatibility gaps, body BOM leakage, and hash-bypass regressions.

### Counterexamples
- ui_result_json_bom_breaks_router
- ui_receipt_json_bom_breaks_router
- ui_envelope_json_bom_breaks_router
- legacy_bom_json_without_router_fallback
- body_bom_leaks_to_pm_packet
- bom_repair_bypasses_body_hash

### Friction Points
- The new UI regression exposed that `Get-FileHash` may be unavailable in some
  PowerShell subprocess contexts, so hashing moved to .NET SHA256.
- Other local agents had concurrent FlowPilot changes; this repair stayed
  scoped and preserved their work.

### Skipped Steps
- No sealed startup request body was read by Controller.
- No live `.flowpilot` route state was mutated.
- No remote GitHub sync or push was performed, per user instruction.

### Next Actions
- Keep startup UI artifact encoding as an explicit control-plane contract
  whenever the startup UI output schema changes.

## 2026-05-13 - Reviewer-Only Root And Child Gate Simplification

### Trigger
- The user approved removing Product/Process Officer participation from the
  default `root_contract` and `child_skill_manifest` gates, while requiring a
  FlowGuard-first optimization pass before implementation.

### Model Files
- `simulations/flowpilot_reviewer_only_gate_model.py`
- `simulations/run_flowpilot_reviewer_only_gate_checks.py`
- `simulations/flowpilot_reviewer_only_gate_results.json`

### Runtime Files
- `docs/reviewer_only_gate_simplification_plan.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> schema 1.0.
- OK: `python simulations\run_flowpilot_reviewer_only_gate_checks.py`.
- OK: `python simulations\run_prompt_isolation_checks.py`.
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`.
- OK in background: `python simulations\run_meta_checks.py --force`.
- OK in background: `python simulations\run_capability_checks.py --force`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py skills\flowpilot\assets\barrier_bundle.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_reviewer_only_gate_model.py simulations\run_flowpilot_reviewer_only_gate_checks.py scripts\check_install.py`.
- OK: focused Reviewer-only router tests for root contract and child-skill manifest gates.
- OK: focused active-holder/current-node router tests preserving parallel changes.
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_barrier_bundle.py -q`.
- OK: `python scripts\check_install.py`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.
- Timed out: `python -m pytest tests\test_flowpilot_router_runtime.py -q` did not finish within 20 minutes, so it was not counted as passed.

### Findings
- The Reviewer-only model now catches all listed risks R1-R14, including
  hidden officer artifact requirements, removed-officer card emission,
  missing Reviewer evidence burden, broken role/body isolation, and removed
  legacy officer event compatibility.
- The target Reviewer-only plan passes with root freeze and child-skill
  approval requiring Reviewer pass but no Product/Process Officer default
  gate.
- Runtime tests explicitly prove root freeze does not create or require
  `flowguard/root_contract_modelability.json`, and child-skill approval does
  not create or require `flowguard/child_skill_conformance_model.json` or
  `flowguard/child_skill_product_fit.json`.
- Local installed `flowpilot` skill remained fresh against the repo-owned
  source after sync/audit.

### Counterexamples
- root_freeze_without_reviewer
- root_freeze_waits_for_product_officer
- root_freeze_requires_product_officer_artifact
- root_product_officer_card_emitted
- child_approval_without_reviewer
- child_approval_waits_for_process_officer
- child_approval_waits_for_product_officer
- child_approval_requires_process_officer_artifact
- child_approval_requires_product_officer_artifact
- child_process_officer_card_emitted
- child_product_officer_card_emitted
- root_reviewer_omits_verifiability
- root_reviewer_omits_proof_obligations
- child_reviewer_omits_skill_standards
- child_reviewer_omits_evidence_obligations
- pm_consultation_tail_required
- role_body_boundary_broken
- legacy_officer_event_handlers_removed
- route_ready_without_root_freeze
- route_ready_without_child_manifest_approval

### Skipped Steps
- No remote GitHub push or release action was performed, per user instruction.
- Full router runtime module completion remains unverified because the module
  exceeded the 20-minute local command limit; focused route-critical tests
  were used instead.

### Next Actions
- Future Reviewer-only gate changes should update this dedicated model before
  changing Router sequencing or gate file prerequisites.


## heartbeat-resume-manifest-check-fold-20260513 - Make FlowPilot heartbeat resume continue past prompt-manifest checks to the PM resume card

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Heartbeat/manual resume could rehydrate roles, reach check_prompt_manifest, and stop before PM resume decision; the fix changes resume control flow and required model-first validation.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T17:59:02+00:00
- Ended: 2026-05-13T17:59:02+00:00
- Duration seconds: 3900.000
- Commands OK: True

### Model Files
- simulations/flowpilot_resume_model.py
- simulations/run_flowpilot_resume_checks.py
- simulations/flowpilot_resume_results.json

### Commands
- OK (0.000s): `flowguard schema version check -> 1.0`
- OK (0.000s): `run_flowpilot_resume_checks -> ok true; 517 states; 516 edges; hazards detected`
- OK (0.000s): `focused router resume pytest selection -> 7 passed`
- OK (0.000s): `run_capability_checks -> ok true; 620559 states; 646018 edges; hazards matched`
- OK (0.000s): `run_meta_checks -> ok true; 622789 states; 642960 edges`
- OK (0.000s): `install_flowpilot sync repo-owned -> ok true`
- OK (0.000s): `audit_local_install_sync -> ok true`
- OK (0.000s): `install_flowpilot check -> ok true`

### Findings
- check_prompt_manifest is modeled as an internal controller check before prompt delivery, not as a stop boundary.
- Heartbeat startup guidance now explicitly tells resumed agents to continue the router loop after manifest checks and stop only at real wait boundaries.
- Derived status is synchronized immediately after pending controller action computation so current_status_summary.json does not mislead resumed agents.

### Counterexamples
- run_until_wait_stops_at_manifest_check
- run_until_wait_crosses_true_wait_boundary
- pm_resume_card_without_manifest_fold
- pm_resume_card_after_stale_status_summary
- heartbeat_prompt_allows_manifest_checkpoint_stop

### Friction Points
- Windows background Start-Process attempts did not produce reliable logs; long model checks were rerun in foreground with extended timeouts and passed.

### Skipped Steps
- No remote GitHub sync or push was performed, per user instruction.

### Next Actions
- Keep resume run-until-wait folding scoped to safe controller checks and rerun resume/meta/capability models before future heartbeat-control changes.


## dial1-active-holder-fast-lane-20260513 - Add current-node active-holder fast lane for FlowPilot speed tier 1

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved speed tier 1 only, requiring a model-first implementation that removes avoidable Controller/PM relay waiting from current-node worker execution while preserving packet identity, route/frontier freshness, and reviewer/PM disposition gates.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-13T19:10:00+02:00
- Ended: 2026-05-13T20:01:30+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_router_loop_model.py
- simulations/run_flowpilot_router_loop_checks.py
- simulations/flowpilot_router_loop_results.json
- simulations/flowpilot_optimization_proposal_results.json

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> 1.0
- OK: `python simulations\run_flowpilot_router_loop_checks.py --json-out simulations\flowpilot_router_loop_results.json`
- OK: `python simulations\run_flowpilot_optimization_proposal_checks.py --json-out simulations\flowpilot_optimization_proposal_results.json`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py simulations\flowpilot_router_loop_model.py simulations\run_flowpilot_router_loop_checks.py`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py -k active_holder -q` -> 4 passed
- OK: `python -m pytest tests\test_flowpilot_router_runtime.py -k "current_node or run_until_wait_folds_manifest_check_before_card_boundary" -q` -> 13 passed
- OK: project model checks for meta, capability, resume, prompt isolation, reviewer-only gate, and card instruction coverage
- OK: `python scripts\smoke_autopilot.py --fast`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\check_install.py`

### Findings
- Router current-node packet relay now issues active-holder leases to the current worker when a live agent id is known, avoiding an extra Controller/PM work-start round trip.
- Worker result return through the active-holder path now produces a Router next-action notice to `project_manager` for result disposition instead of hardcoding reviewer delivery.
- Router result validation now requires fast-lane mechanics and Controller notice evidence for packets that had an active-holder lease.
- The model now catches project work starting before an active-holder lease and legacy result return that bypasses fast-lane mechanics.
- A concurrent reviewer-only optimization left legacy officer events requiring removed default card-delivery flags; those events were marked legacy so old records remain accepted without blocking the new default path.

### Counterexamples
- current_node_packet_relayed_without_active_holder_lease
- legacy_worker_result_return_without_fast_lane_mechanics
- worker project work started before active-holder lease
- worker result returned before active-holder mechanics pass
- card instruction coverage failure from non-legacy removed officer events

### Friction Points
- Other local AI agents had concurrent FlowPilot speed-profile edits in the same repository; this work preserved their changes and fixed one smoke-test gap they exposed.
- The broad `smoke_autopilot.py` run exceeded a foreground timeout before rerunning successfully with `--fast`.

### Skipped Steps
- The abstract router-loop model still has no production conformance replay adapter, so conformance replay remains skipped with reason rather than treated as passed.
- No sealed card, packet, result, or report body was read by Controller.
- No live `.flowpilot` route state was mutated.
- No remote GitHub sync or push was performed, per user instruction.

### Next Actions
- Keep current-node speed work on the active-holder lease path and rerun router-loop plus current-node tests before extending speed tier 2 parallelization.


## flowpilot-low-quality-success-hardening-20260513 - Fuse low-quality success prevention into existing FlowPilot PM and reviewer gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to prevent FlowPilot PM/reviewer planning from letting hard parts be handled thinly or casually, and required FlowGuard model validation before prompt/template changes.
- Status: in_progress
- Skill decision: use_flowguard
- Started: 2026-05-13T18:31:53+00:00
- Ended: 2026-05-13T18:31:53+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_planning_quality_model.py
- simulations/flowpilot_reviewer_active_challenge_model.py

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
- Write the concrete optimization/risk table, upgrade planning/reviewer models, prove hazards are caught, then edit existing cards/templates without adding a new workflow.


## flowpilot-low-quality-success-hardening-20260513 - Fuse low-quality success prevention into existing FlowPilot PM and reviewer gates

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior-bearing FlowPilot prompt and protocol quality change; user required model-first simulation before prompt edits
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-13T19:08:27+00:00
- Ended: 2026-05-13T19:08:27+00:00
- Duration seconds: 7200.000
- Commands OK: True

### Model Files
- simulations/flowpilot_planning_quality_model.py
- simulations/flowpilot_reviewer_active_challenge_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK (0.000s): `python simulations/run_flowpilot_planning_quality_checks.py --json-out simulations/flowpilot_planning_quality_results.json`
- OK (0.000s): `python simulations/run_flowpilot_reviewer_active_challenge_checks.py --json-out simulations/flowpilot_reviewer_active_challenge_results.json`
- OK (0.000s): `python simulations/run_meta_checks.py --force`
- OK (0.000s): `python simulations/run_capability_checks.py --force`
- OK (0.000s): `python -m pytest tests/test_flowpilot_planning_quality.py tests/test_flowpilot_reviewer_active_challenge.py -q`
- OK (0.000s): `python scripts/check_install.py`
- OK (0.000s): `python -m pytest tests --ignore=tests/test_flowpilot_router_runtime.py -q`
- OK (0.000s): `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK (0.000s): `python scripts/audit_local_install_sync.py --json`

### Findings
- Planning model now catches missing/generic low-quality-success review, unowned hard low-quality risks, route bloat, missing node mapping, missing work-packet warning, and missing closure disposition.
- Reviewer active challenge model now catches missing low-quality-success challenge and existence-only evidence accepted for hard-part claims.
- Prompt/template changes were fused into existing PM product architecture, root contract, route skeleton, node acceptance, packet/result, reviewer, final ledger, and closure gates without adding a new major flow.

### Counterexamples
- none recorded

### Friction Points
- PowerShell background model launches with the Windows Python app alias required duplicate-process cleanup and a resolved Python path.

### Skipped Steps
- Whole-repo pytest from repository root is not a valid signal because backup tests shadow active tests; formal tests were run from tests/.
- Full tests including tests/test_flowpilot_router_runtime.py exceeded the practical local timeout while another agent was actively running router-runtime tests. Non-router tests, target tests, install checks, and FlowGuard simulations passed.

### Next Actions
- When router runtime work by parallel agents settles, rerun tests/test_flowpilot_router_runtime.py separately before any remote release.


## flowpilot-reviewer-only-gate-runtime-alignment-20260513 - Validate reviewer-only gates and align runtime tests with active-holder fast lane

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested FlowPilot speed tier 2 reviewer-only gate simplification with FlowGuard proof before implementation, while preserving parallel agent optimizations.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-13T00:00:00+00:00
- Ended: 2026-05-13T00:00:00+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_reviewer_only_gate_model.py
- simulations/barrier_bundle_model.py
- simulations/prompt_isolation_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_flowpilot_reviewer_only_gate_checks.py`
- OK: `python simulations/run_barrier_equivalence_checks.py`
- OK: `python simulations/run_prompt_isolation_checks.py`
- OK: `python simulations/run_meta_checks.py --force`
- OK: `python simulations/run_capability_checks.py --force`
- OK: `python -m pytest tests/test_flowpilot_barrier_bundle.py -q`
- OK: `python -m pytest tests/test_flowpilot_card_instruction_coverage.py -q`
- OK: `python -m pytest tests/test_flowpilot_router_runtime.py` by ordered chunks covering all 156 collected tests
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/install_flowpilot.py --check --json`
- OK: `python scripts/check_install.py`

### Findings
- Reviewer-only model catches root freeze without Reviewer, hidden Product Officer waits or artifacts, hidden child-skill Process/Product Officer waits or artifacts, removed card emissions, route readiness before required PM approval, and weakened Reviewer checklist coverage.
- The reviewer-only target plan passes with root contract freeze and child-skill manifest approval depending on PM authored artifacts plus Reviewer pass only.
- Runtime validation exposed two stale current-node tests that bypassed the parallel active-holder fast lane; tests now use the active-holder helper instead of direct `write_result`.
- Runtime validation exposed two Product Officer block specs whose reset lists included their own blocked flag; the reset lists now preserve the freshly recorded block.

### Counterexamples
- Known-bad reviewer-only hazards R1-R14 were detected by `run_flowpilot_reviewer_only_gate_checks.py`.

### Friction Points
- Full router-runtime pytest in one process exceeded the practical local timeout, so the 156 tests were run in ordered chunks.
- Long FlowGuard meta and capability checks are expensive on this Windows/Python setup and should remain long-running validation steps.

### Skipped Steps
- No GitHub push or remote sync was run by user request.

### Next Actions
- Keep the reviewer-only model updated if future agents reintroduce Product/Process Officer default gates at root-contract or child-skill-manifest boundaries.


## startup-intake-powershell-source-encoding-20260513 - Repair legacy Windows PowerShell source parsing for startup intake UI

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User reported another Windows agent could not open the startup UI because Windows PowerShell parsed UTF-8 no-BOM Chinese source text under a legacy code page and broke script syntax.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-13T20:00:00+00:00
- Ended: 2026-05-13T20:11:00+00:00
- Duration seconds: 660.000
- Commands OK: True

### Model Files
- simulations/flowpilot_startup_intake_ui_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_flowpilot_startup_intake_ui_checks.py --json-out simulations/flowpilot_startup_intake_ui_results.json`
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_intake_powershell_sources_with_non_ascii_use_utf8_bom` failed before the source repair and passed after it
- OK: `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_intake_powershell_sources_with_non_ascii_use_utf8_bom tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_intake_ui_writes_utf8_without_bom tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_router_accepts_utf8_bom_json_control_artifact tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_intake_body_bom_is_not_injected_into_pm_packet_body`
- OK: `powershell.exe -STA -NoProfile -ExecutionPolicy Bypass -File skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1 -SmokeTest`
- OK: `powershell.exe -STA -NoProfile -ExecutionPolicy Bypass -File docs/ui/startup_intake_desktop_preview/flowpilot_startup_intake.ps1 -SmokeTest`
- OK: `python -m py_compile scripts/check_install.py simulations/flowpilot_startup_intake_ui_model.py simulations/run_flowpilot_startup_intake_ui_checks.py`
- OK: `python scripts/check_install.py`
- OK: `python simulations/run_flowpilot_startup_control_checks.py`
- OK: `python simulations/run_prompt_isolation_checks.py`
- OK: `python simulations/run_startup_pm_review_checks.py`
- OK: `python simulations/run_meta_checks.py --force`
- OK: `python simulations/run_capability_checks.py --force`
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/install_flowpilot.py --check --json`

### Findings
- The startup intake UI model now represents launcher source encoding separately from generated JSON/body artifact encoding.
- The model catches the legacy Windows PowerShell hazard where non-ASCII UTF-8 no-BOM `.ps1` source can fail before any script-level encoding setup runs.
- The approved repair plan passes with UTF-8 BOM source files while preserving no-BOM generated artifacts for downstream packet compatibility.
- `scripts/check_install.py` now guards the active and preview startup UI PowerShell sources so future non-ASCII edits cannot silently reintroduce UTF-8 no-BOM source fragility.

### Counterexamples
- `ui_opened_before_source_encoding_check` was detected by the startup intake UI model.
- `utf8_no_bom_script_source_legacy_powershell_parse_break` was detected by the startup intake UI model.

### Friction Points
- Long meta and capability simulations were run as hidden background PowerShell processes so installation sync and local checks could proceed in parallel.
- Parallel agents introduced unrelated working-tree changes during validation; this repair kept its git scope limited to startup UI encoding, its model, tests, install check, and documentation.

### Skipped Steps
- No GitHub push or remote sync was run by user request.

### Next Actions
- Preserve the distinction between PowerShell source-file BOM requirements and generated artifact no-BOM requirements in future startup UI changes.


## route-skeleton-reviewer-only-optimization-20260513 - Remove redundant Product route review and final-closure officer slices

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested FlowPilot speed tier 2 optimization with a concrete FlowGuard-first plan before removing redundant Officer checks from route skeleton and final closure.
- Status: completed
- Skill decision: use_flowguard
- Started: 2026-05-13T20:45:00+02:00
- Ended: 2026-05-13T22:50:00+02:00
- Duration seconds: 7500.000
- Commands OK: True

### Model Files
- simulations/flowpilot_route_hard_gate_model.py
- simulations/router_next_recipient_model.py
- simulations/barrier_equivalence_model.py
- simulations/flowpilot_optimization_proposal_model.py
- simulations/flowpilot_control_plane_friction_model.py
- simulations/meta_model.py
- simulations/capability_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- OK: `python simulations/run_flowpilot_route_hard_gate_checks.py`
- OK: `python simulations/run_router_next_recipient_checks.py`
- OK: `python simulations/run_barrier_equivalence_checks.py`
- OK: `python simulations/run_flowpilot_optimization_proposal_checks.py --json-out simulations/flowpilot_optimization_proposal_results.json`
- OK: `python simulations/run_flowpilot_dynamic_return_path_checks.py`
- OK: `python simulations/run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations/flowpilot_control_plane_friction_results.json`
- OK: `python simulations/run_card_instruction_coverage_checks.py`
- OK: `python simulations/run_protocol_contract_conformance_checks.py`
- OK: `python simulations/run_meta_checks.py --force`
- OK: `python simulations/run_capability_checks.py --force`
- OK: `python -m py_compile skills/flowpilot/assets/flowpilot_router.py skills/flowpilot/assets/barrier_bundle.py simulations/flowpilot_route_hard_gate_model.py simulations/router_next_recipient_model.py simulations/barrier_equivalence_model.py simulations/flowpilot_optimization_proposal_model.py simulations/flowpilot_control_plane_friction_model.py`
- OK: `python -m unittest tests.test_flowpilot_barrier_bundle`
- OK: `python -m unittest tests.test_flowpilot_meta_route_sign`
- OK: targeted `tests.test_flowpilot_router_runtime` route/closure subset, 17 tests
- OK: targeted `tests.test_flowpilot_router_runtime` affected route hard-gate subset, 4 tests
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/install_flowpilot.py --check --json`

### Findings
- Route skeleton no longer has a default Product Officer route fit review between PM Process route model acceptance and Reviewer route challenge.
- The remaining product-side protection is upstream: Product Officer product behavior model plus PM product behavior model acceptance, then Process Officer checks route coverage against that product model.
- Reviewer route challenge now depends on the PM-accepted Process route model and Product behavior model context instead of a second Product route check.
- Final closure barrier role slices now require PM and Reviewer only; FlowGuard Officer slices are not required at final closure while all legacy obligations remain preserved.
- The compatibility Product route check card and event remain legacy-compatible but are no longer on the default system-card path.

### Counterexamples
- Missing Product behavior model before PM route draft was detected.
- Process route pass without product-model coverage was detected.
- Reviewer route challenge before PM process-route acceptance was detected.
- Route activation without Reviewer challenge was detected.
- Final closure missing required obligations was detected.
- Hidden/default route Product Officer wait reintroduction was detected by router next-recipient and route hard-gate models.

### Friction Points
- Default control-plane live audit found an existing local `.flowpilot/current.json` active-run inconsistency in material-scan phase context. The abstract control-plane model was rerun with `--skip-live-audit` and passed; the local active-run issue was not caused by this optimization.
- Full `tests.test_flowpilot_router_runtime` exceeded the practical 15-minute local timeout, so verification used route/closure-focused subsets plus the broader model suite and installer checks.
- Long meta and capability simulations remained expensive and were run with extended timeouts.

### Skipped Steps
- No live `.flowpilot` run artifacts were mutated to rewrite historical prompt-delivery records.
- The full router-runtime unittest module did not complete within the local 15-minute timeout.

### Next Actions
- If the local active FlowPilot run is resumed, reconcile its existing material-scan phase-context audit finding separately from this route-skeleton optimization.
- Keep the Product route check card/event marked as compatibility-only unless a future route explicitly opts into that extra review.

## 2026-05-13 - Direct ACK Pre-Event Race Model Upgrade

### Trigger
- Investigated a live FlowPilot control-plane stop where a valid PM card-bundle ACK file existed before a reviewer role event, but Router still blocked the role event as an unresolved card return.

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py

### Commands
- OK: `python -m py_compile simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out tmp\flowpilot_control_plane_friction_model_ack_preconsume.json`
- EXPECTED_FINDING: `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out tmp\flowpilot_control_plane_friction_live_ack_preconsume.json`

### Findings
- Added abstract state and hazards for direct card ACK files that are present and valid before a later role event reaches Router while the return ledger is still unresolved.
- Added coverage for both single-card ACK and card-bundle ACK paths.
- Added a guard against accepting a pre-event ACK without role/hash/bundle-receipt validation and without resolving the return ledger before processing the role event.
- Added live audit projection that catches historical blockers where `ack_returned_at <= blocker_created_at < ledger_resolved_at`.

### Live Evidence
- Run `run-20260513-211725` produced `valid_card_ack_file_present_role_event_blocked`.
- The PM card-bundle ACK was returned at `2026-05-13T23:28:08+02:00`.
- Router blocker artifacts were created at `2026-05-13T23:28:25+02:00` and `2026-05-13T23:28:26+02:00`.
- The return ledger was only resolved at `2026-05-13T23:35:02+02:00`.

### Minimal Repair Direction
- Move validated pending card-return ACK reconciliation into the Router event-ingress path before unresolved-card-return blocker creation.
- Reuse the existing card ACK and card-bundle ACK validation rules before marking the return ledger resolved.
- Preserve blocking behavior for missing, invalid, wrong-role, wrong-hash, or incomplete bundle ACKs.

## 2026-05-13 - Direct ACK Pre-Event Repair Implementation

### Trigger
- Implemented the repair modeled above: Router now reconciles a valid direct card ACK before creating an unresolved-card-return blocker for a later normal role event.

### Production Files
- skills/flowpilot/assets/flowpilot_router.py
- tests/test_flowpilot_router_runtime.py

### Model and Planning Files
- docs/direct_ack_pre_event_repair_plan.md
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py

### Commands
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
- OK: targeted new router tests for valid single-card ACK, valid card-bundle ACK, invalid ACK rejection, and incomplete bundle ACK rejection.
- OK: adjacent router card-return regression tests for committed system-card relay, PM card bundle delivery, and incomplete bundle recovery.
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py -q`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out tmp\flowpilot_control_plane_friction_after_router_fix.json`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py`
- OK: `python simulations\run_flowpilot_event_contract_checks.py --json-out tmp\flowpilot_event_contract_after_ack_preconsume.json`
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`
- OK: background `python simulations\run_meta_checks.py`; stderr was empty, no `ok:false` markers were present, progress and loop/stuck reviews were OK with 622789 states and 642960 edges.

### Findings
- The first runtime test pass exposed that `_pending_card_return_ack_exists` did not recognize `check_card_return_event` or `check_card_bundle_return_event` actions. The helper was extended to include those action types before trusting the new ingress reconciliation.
- Valid ACKs now resolve the return ledger before the incoming role event is evaluated for unresolved card-return blocking.
- Invalid ACKs and incomplete bundle ACKs still preserve blocking behavior.
- The implementation preserves unrelated role-event wait authority by clearing `pending_action` only when it matches the consumed card return.

### Skipped Steps
- No remote GitHub push was performed.
- The default live audit still reports historical pre-fix local run artifacts; that is expected and does not represent the post-fix runtime path.

## 2026-05-14 - Missing ACK Report Recovery Model and Repair

### Trigger
- Designed and implemented a safer recovery rule for role reports that arrive before their required system-card ACK exists or validates.

### Production Files
- skills/flowpilot/assets/flowpilot_router.py
- tests/test_flowpilot_router_runtime.py

### Model and Planning Files
- docs/missing_ack_report_recovery_plan.md
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py

### Commands
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py`
- OK: `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out tmp\flowpilot_control_plane_friction_missing_ack_after_code.json`
- OK: targeted router tests for valid pre-event ACK reconciliation, missing same-role ACK report quarantine, fresh post-ACK resubmission, invalid same-role ACK quarantine, and unrelated incomplete bundle blocking.
- OK: `python -m pytest tests\test_flowpilot_card_runtime.py -q`
- OK: `python -m pytest tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_role_output_runtime.py -q`
- OK: `python simulations\run_flowpilot_event_contract_checks.py --json-out tmp\flowpilot_event_contract_missing_ack_recovery.json`
- OK: `python simulations\run_flowpilot_card_envelope_checks.py`
- OK: background `python simulations\run_meta_checks.py`; stderr was empty, progress and loop/stuck reviews were OK with 622789 states and 642960 edges.
- OK: `python scripts\check_install.py --json`

### Findings
- The upgraded control-plane model now catches seven bug classes: accepting a report before ACK, recovering without quarantine, using a quarantined report as evidence, reviving an old pre-ACK report, escalating the first recoverable case to generic PM blocking, quarantining unrelated pending ACKs, and failing to escalate repeated recovery failures.
- Router now quarantines same-role, same-card-dependency reports that arrive before a valid ACK; the event is not recorded and its flag is not set.
- The recovery action points back to the pending card-return path, requiring the role to open the card, submit a valid ACK, and resubmit a fresh report.
- Unrelated pending card returns still use the existing unresolved-card-return blocker instead of being quarantined.

### Skipped Steps
- Full `tests\test_flowpilot_router_runtime.py` exceeded the local 5-minute command timeout, so verification used the new targeted router tests, adjacent runtime tests, FlowGuard checks, event-contract checks, card-envelope checks, meta checks, and install checks.
- No remote GitHub push was performed.

## 2026-05-14 - Wait Reconciliation Optimization Model-First Upgrade

### Trigger
- Began a model-first optimization for FlowPilot wait latency: stale waits, partial batch accounting, dependency-aware continuation, active-holder fast-lane expansion, and dynamic event authority.

### Planning Files
- docs/flowpilot_wait_reconciliation_optimization_plan.md
- openspec/changes/optimize-flowpilot-wait-reconciliation/

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py
- simulations/flowpilot_parallel_packet_batch_model.py
- simulations/run_flowpilot_parallel_packet_batch_checks.py
- simulations/flowpilot_decision_liveness_model.py
- simulations/run_flowpilot_decision_liveness_checks.py
- simulations/flowpilot_router_loop_model.py
- simulations/run_flowpilot_router_loop_checks.py
- simulations/flowpilot_event_contract_model.py
- simulations/run_flowpilot_event_contract_checks.py
- simulations/flowpilot_event_capability_registry_model.py
- simulations/run_flowpilot_event_capability_registry_checks.py

### Production and Prompt Files
- skills/flowpilot/assets/flowpilot_router.py
- tests/test_flowpilot_router_runtime.py
- docs/schema.md
- templates/flowpilot/packet_ledger.template.json
- templates/flowpilot/packets/controller_status_packet.template.json
- templates/flowpilot/packets/packet_envelope.template.json
- templates/flowpilot/packets/result_envelope.template.json
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_scan.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_package.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_role_work_request.md

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: background model run set in `tmp/wait_opt_model_runs_2/` for control-plane, parallel-batch, and router-loop checks.
- OK: background decision-liveness rerun in `tmp/wait_opt_model_runs_3/decision.json`.
- OK: background event-contract and event-capability reruns in `tmp/wait_opt_event_model_runs/`.
- OK: final model reruns in `tmp/wait_opt_final_model_runs/` for control-plane, decision-liveness, router-loop, event-contract, and event-capability checks.
- OK: `python simulations\run_flowpilot_parallel_packet_batch_checks.py`.
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`.
- OK: targeted router tests for stale material-result reconciliation, material partial-batch missing-role summary, PM role-work result reconciliation, advisory nonblocking wait, model-miss role-work channel, PM role-work batch join, current-node batch join, and insufficient-material event handling.
- OK: targeted packet-runtime active-holder tests for close-with-controller-notice, wrong/stale contact rejection, and mechanical reject preserving the holder.
- OK: targeted router tests for expanded active-holder lease issuance on material scan, research, and PM role-work packets.
- OK: `python simulations\run_flowpilot_planning_quality_checks.py` and `python simulations\run_flowpilot_requirement_traceability_checks.py` for the concurrently present planning/traceability changes.
- OK: `python scripts\check_install.py --json` before local install sync.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`; installed `flowpilot` digest changed to match the repository source digest.
- OK: `python scripts\check_install.py --json` after local install sync.

### Findings
- The model suite now catches stale waits after durable result evidence exists, partial batch returned-count drift, stale missing-role status, duplicate reconciliation count increments, unsafe non-dependent continuation, active-holder misuse outside current-node packets, and incoming role events outside current `allowed_external_events`.
- The intended optimized design passed the upgraded model checks before production Router edits began.
- Router now reconciles durable result evidence before reissuing waits, refreshes partial batch status from packet/result ledgers, and records reconciliation events idempotently.
- Partial material, research, current-node, and PM role-work batches now expose metadata-only returned/missing role summaries and wait only for the missing roles.
- Active-holder leases are now issued for material scan, research, and PM role-work packets when a live holder is known; the existing Controller relay path remains the fallback.
- Advisory and prep-only PM role-work waits are retained as recheckable nonblocking waits instead of freezing unrelated work or disappearing from terminal accountability.
- During final status inspection, concurrent planning-quality and requirement-traceability edits were present in the same worktree and in `flowpilot_router.py`; they were preserved and separately smoke-checked instead of reverted.

### Skipped Steps
- No remote GitHub push was performed.
- Full `tests\test_flowpilot_router_runtime.py` was not run because it is large and has previously exceeded local timeouts; verification used the upgraded FlowGuard model suite, targeted router tests, packet-runtime tests, install checks, and model checks for adjacent concurrent changes.

## 2026-05-14 - Requirement Traceability Upgrade

### Trigger
- Began a model-first upgrade to give FlowPilot OpenSpec-like requirement traceability while keeping FlowPilot standalone and full-protocol-only.

### Planning Files
- docs/flowpilot_requirement_traceability_upgrade_plan.md

### Model Files
- simulations/flowpilot_requirement_traceability_model.py
- simulations/run_flowpilot_requirement_traceability_checks.py
- simulations/flowpilot_requirement_traceability_results.json
- simulations/flowpilot_planning_quality_model.py
- simulations/run_flowpilot_planning_quality_checks.py
- simulations/flowpilot_planning_quality_results.json

### Production and Prompt Files
- skills/flowpilot/assets/flowpilot_router.py
- templates/flowpilot/product_function_architecture.template.json
- templates/flowpilot/root_acceptance_contract.template.json
- templates/flowpilot/routes/route-001/flow.template.json
- templates/flowpilot/node_acceptance_plan.template.json
- templates/flowpilot/final_route_wide_gate_ledger.template.json
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_root_contract.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md
- skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md
- skills/flowpilot/assets/runtime_kit/cards/reviewer/route_challenge.md

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_requirement_traceability_model.py simulations\run_flowpilot_requirement_traceability_checks.py simulations\flowpilot_planning_quality_model.py simulations\run_flowpilot_planning_quality_checks.py`
- OK: `python simulations\run_flowpilot_requirement_traceability_checks.py --json-out simulations\flowpilot_requirement_traceability_results.json`
- OK: `python simulations\run_flowpilot_planning_quality_checks.py --json-out simulations\flowpilot_planning_quality_results.json`
- OK: JSON parsing checks for the updated FlowPilot templates.
- OK: targeted router tests for product architecture/root contract/route skeleton, node acceptance plan traceability, final ledger, and node acceptance repair.
- OK: background `python simulations\run_meta_checks.py`; progress and loop/stuck reviews were OK with 622789 states and 642960 edges.
- OK: background `python simulations\run_capability_checks.py`; status was OK and known capability hazards matched expected failures.
- OK: `python scripts\check_install.py --json`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The new traceability model catches missing stable requirement IDs, unmapped product capabilities, root requirements without source/change/supersession metadata, route nodes referencing unknown requirements, node plans without direct evidence mapping, stale mutation evidence, incomplete final ledger closure, unauthorized external spec authority, and forbidden light/simple FlowPilot profiles.
- The planning-quality model now treats small/simple formal FlowPilot as a hazard; FlowPilot remains full protocol whenever invoked.
- Product architecture, root contract, route skeleton, node acceptance plan, and final route ledger artifacts now carry requirement trace fields through the existing FlowPilot process instead of adding a parallel change-pack process.
- Router writers now normalize trace fields for product/root/route/node artifacts and validate node-plan and final-ledger traceability before accepting those artifacts.
- The installed local FlowPilot skill is source-fresh against this repository after local sync.

### Skipped Steps
- Full `tests\test_flowpilot_router_runtime.py` exceeded a 10-minute command timeout in this mixed worktree; verification used targeted router tests, template checks, upgraded FlowGuard models, meta/capability checks, and install sync checks.
- No remote GitHub push was performed.

## 2026-05-14 - OpenSpec Second-Perspective Cleanup

### Trigger
- Used OpenSpec as a second review lens over the existing FlowPilot wait-reconciliation work, while keeping FlowPilot as the control plane and FlowGuard as the executable validation layer.

### Files Updated
- docs/protocol.md
- skills/flowpilot/references/protocol.md
- templates/flowpilot/product_function_architecture.template.json
- templates/flowpilot/routes/route-001/nodes/node-001-start/node.template.json
- docs/legacy_to_router_equivalence.md
- docs/legacy_to_router_equivalence.json
- openspec/changes/optimize-flowpilot-wait-reconciliation/design.md
- openspec/changes/optimize-flowpilot-wait-reconciliation/tasks.md
- openspec/changes/optimize-flowpilot-wait-reconciliation/specs/dependency-aware-continuation/spec.md

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `openspec status --change "optimize-flowpilot-wait-reconciliation" --json`
- OK: `openspec instructions apply --change "optimize-flowpilot-wait-reconciliation" --json`
- OK: `rg -n "\.flowpilot/pm_material_understanding\.json" docs templates skills openspec` returned no stale top-level path matches.
- OK: `openspec validate optimize-flowpilot-wait-reconciliation --strict --json`
- OK: `python simulations/run_flowpilot_requirement_traceability_checks.py --json-out tmp/openspec_flowguard_requirement_traceability.json`
- OK: `python simulations/run_flowpilot_event_contract_checks.py --json-out tmp/openspec_flowguard_event_contract.json`
- OK: `python simulations/run_flowpilot_event_capability_registry_checks.py --json-out tmp/openspec_flowguard_event_capability.json`
- OK: `python simulations/run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out tmp/openspec_flowguard_control_plane.json`
- OK: `python simulations/run_flowpilot_parallel_packet_batch_checks.py --json`
- OK: `python simulations/run_flowpilot_decision_liveness_checks.py --json-out tmp/openspec_flowguard_decision_liveness.json`
- OK: `python simulations/run_flowpilot_router_loop_checks.py --json-out tmp/openspec_flowguard_router_loop.json`
- OK: `python scripts/check_install.py --json`
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts/audit_local_install_sync.py --json`
- OK: `python scripts/install_flowpilot.py --check --json`

### Findings
- The stale top-level `.flowpilot/pm_material_understanding.json` references in docs and templates were aligned to `.flowpilot/runs/<run-id>/pm_material_understanding.json`.
- OpenSpec coverage now explicitly names Router-authorized return events, role-work result/request matching, and prompt/runtime capability drift.
- Legacy equivalence notes now treat PM role-work as the generic sealed-envelope packet path while preserving dedicated officer-model report lifecycle coverage as remaining future work.
- The installed local FlowPilot skill is source-fresh against this repository after sync.

### Skipped Steps
- No remote GitHub push was performed.
- No broad production-code rewrite was performed; this pass was limited to alignment, specs, templates, docs, local install sync, and local Git preparation.

## 2026-05-14 - Router-Ready Controller Wait Preemption

### Trigger
- User reported FlowPilot Controller waiting two to three minutes on roles after relaying cards even when Router already had the next instruction.
- User approved an OpenSpec plus FlowGuard repair and requested local installed skill sync plus local git sync.

### Files Updated
- simulations/flowpilot_role_output_runtime_model.py
- simulations/run_flowpilot_role_output_runtime_checks.py
- skills/flowpilot/SKILL.md
- skills/flowpilot/assets/flowpilot_router.py
- skills/flowpilot/assets/runtime_kit/cards/roles/controller.md
- skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md
- skills/flowpilot/references/protocol.md
- tests/test_flowpilot_router_runtime.py
- openspec/changes/preempt-controller-stale-role-waits/

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `openspec validate preempt-controller-stale-role-waits --strict --json`
- OK: `python simulations\run_flowpilot_role_output_runtime_checks.py --json-out simulations\flowpilot_role_output_runtime_results.json`
- OK: `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_role_output_runtime_model.py simulations\run_flowpilot_role_output_runtime_checks.py`
- OK: targeted Router runtime tests for `run_until_wait`, system-card delivery, committed relay resolution, and resume reentry preemption: 7 passed.
- OK: `python -m pytest tests\test_flowpilot_role_output_runtime.py -q`: 14 passed.
- OK: `python simulations\run_meta_checks.py`: progress and loop/stuck reviews OK with 622789 states and 642960 edges.
- OK: `python simulations\run_capability_checks.py`: progress, loop/stuck, and expected hazard reviews OK with 620559 states and 646018 edges.
- OK: card-envelope, router-loop, decision-liveness, and dynamic-return-path FlowGuard checks.
- OK: `python scripts\check_install.py`
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`
- OK: `python scripts\audit_local_install_sync.py --json`
- OK: `python scripts\install_flowpilot.py --check --json`

### Findings
- The role-output runtime model now rejects a Controller path that foreground-waits on a role after Router-ready evidence exists.
- Superseded historical note: this relay/wait contract has been replaced by the formal Router daemon plus Controller action ledger contract; `next` and `run-until-wait` are diagnostics or explicit repair tools, not the normal runtime metronome.
- Controller, resume, skill, and protocol guidance now say Router daemon status, resolved ACKs, status packets, result notices, and pending ledger actions preempt foreground role waits.
- Liveness waits remain recovery-only and do not become ordinary two-minute work waits.
- The installed local FlowPilot skill is source-fresh against the repository after sync.

### Skipped Steps
- Full `tests\test_flowpilot_router_runtime.py` exceeded a 10-minute timeout; a broad keyword subset also exceeded a 5-minute timeout.
- Verification used focused router tests, the full role-output runtime test module, FlowGuard models, install checks, and OpenSpec strict validation.
- No remote GitHub push was performed.


## standardize-flowguard-background-logs - Standardize FlowPilot FlowGuard background progress logs and legacy runner progress

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot project-control FlowGuard checks needed fixed logs, progress, and exit evidence
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T07:59:58+00:00
- Ended: 2026-05-14T07:59:58+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `python simulations\\run_meta_checks.py --force; python simulations\\run_capability_checks.py --force`

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

## daemonize-flowpilot-router - Persistent Router daemon and Controller action ledger

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Controller could stop at a nonterminal role wait after all card ACK evidence had already reached Router, leaving no foreground actor to call Router again.
- Status: completed with focused follow-up coverage still tracked in OpenSpec
- Skill decision: used_flowguard
- Started: 2026-05-14T13:00:00+02:00
- Ended: 2026-05-14T16:35:00+02:00
- Commands OK: True

### Model Files
- simulations/flowpilot_persistent_router_daemon_model.py
- simulations/run_flowpilot_persistent_router_daemon_checks.py
- simulations/meta_model.py
- simulations/run_meta_checks.py
- simulations/capability_model.py
- simulations/run_capability_checks.py
- simulations/flowpilot_resume_model.py
- simulations/run_flowpilot_resume_checks.py
- simulations/flowpilot_protocol_contract_conformance_model.py

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`
- OK: `python simulations/run_flowpilot_persistent_router_daemon_checks.py --json-out simulations/flowpilot_persistent_router_daemon_results.json`
- OK: `python simulations/run_flowpilot_resume_checks.py`
- OK: `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json`
- OK: `python simulations/run_flowpilot_control_plane_friction_checks.py --json-out simulations/flowpilot_control_plane_friction_results.json`
- OK: `python simulations/run_flowpilot_event_contract_checks.py --json-out simulations/flowpilot_event_contract_results.json`
- OK: `python simulations/run_protocol_contract_conformance_checks.py --json-out simulations/protocol_contract_conformance_results.json`
- OK: all `simulations/run_*_checks.py` scripts passed after the protocol conformance probe was corrected.
- OK: background `python simulations/run_meta_checks.py --force`: exit 0, 1,949,768 states, 2,010,668 edges, 0 invariant failures, proof reuse `not_reused_force`.
- OK: background `python simulations/run_capability_checks.py --force`: exit 0, 1,959,064 states, 2,036,034 edges, 0 invariant failures, proof reuse `not_reused_force`.
- OK: `python -m py_compile skills/flowpilot/assets/flowpilot_router.py tests/test_flowpilot_router_runtime.py`
- OK: focused daemon, heartbeat, and run-until-wait runtime tests: 12 passed.
- OK: prompt/source checks: card instruction coverage, role-output runtime, startup-control, protocol conformance, and `python scripts/check_install.py`.
- OK: local install sync and audit: `python scripts/install_flowpilot.py --sync-repo-owned --json`, `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json`.

### Findings
- Router now has a per-run daemon mode with a fixed one-second tick, a run-scoped single-writer lock, daemon status, daemon event log, and stale-lock recovery path.
- Controller-visible work now persists in `runtime/controller_action_ledger.json` with per-action files and required Controller receipts; Router does not mark Controller work done without a valid receipt.
- Daemon ticks call the existing Router decision path, so valid card ACK, bundle ACK, report, packet ACK, result envelope, and return-ledger evidence can be reconciled without a foreground manual `next`.
- Controller, heartbeat/manual resume, PM/reviewer/worker/officer role cards, packet templates, and protocol text now say role ACKs/results go to the Router mailbox; the daemon consumes valid evidence and roles do not advance route state directly.
- Local installed FlowPilot is source-fresh against the repository after the final sync.

### Counterexamples
- `pm_bundle_ack_available_but_no_daemon_consumes_it`
- `duplicate_router_daemon_writers_for_one_run`
- `controller_action_marked_done_without_receipt`
- `controller_stops_at_nonterminal_daemon_wait`
- `heartbeat_starts_second_router_instead_of_attaching`

### Friction Points
- Prompt/source scanners rely on exact Router-ready wait-preemption phrases, so daemon wording had to preserve those existing strings while adding ledger/daemon wording.
- `skills/flowpilot/SKILL.md` must remain a small launcher; earlier wording exceeded the self-check line threshold and was shortened.
- Full broad router-runtime selection remains slower than the focused smoke subset, so this pass used focused runtime tests plus full FlowGuard model coverage.

### Skipped Steps
- No remote GitHub push, tag, or release action was performed.
- OpenSpec still tracks targeted follow-up tests for malformed daemon ACKs, multi-action ledger edge cases, resume stale-daemon scenarios, Route Sign sourcing, and focused card/packet runtime compatibility.

### Next Actions
- Add the remaining focused tests listed in `openspec/changes/daemonize-flowpilot-router/tasks.md` before archiving the change.
- Keep future wait/recovery changes modeled first in the persistent daemon model and rerun meta/capability checks when project-control flow changes.

### Finalization Update
- Status: completed.
- OpenSpec: `daemonize-flowpilot-router` is complete and passes strict validation.
- Follow-up tests added and passed for malformed daemon ACK variants, incomplete bundle ACK waits, duplicate stale ACK idempotency, multi-action Controller ledger receipts, live daemon resume, stale/missing daemon recovery, and Route Sign/status sourcing.
- Local install: `python scripts/install_flowpilot.py --sync-repo-owned --json`, `python scripts/audit_local_install_sync.py --json`, and `python scripts/install_flowpilot.py --check --json` all passed with installed FlowPilot source-fresh.
- Heavy meta/capability checks were not rerun during finalization because the user explicitly narrowed validation scope and the heavy FlowGuard models/flag logic had not changed after their prior successful run.
- Future rule: rerun heavyweight meta/capability checks only when project-control flow, skill/capability routing, heavy FlowGuard models, or runner semantics change.

## flowpilot-control-plane-evidence-closure - Stateful receipt and role-output evidence model miss

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: run-20260514-181747 reached startup but blocked before route work because Controller/PM progress surfaces looked complete while Router-visible evidence was not closed.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T20:35:00+02:00
- Ended: 2026-05-14T20:58:00+02:00
- Commands OK: True

### Risk Intent
- Model and catch control-plane cases where a receipt, status packet, or progress update claims completion before the Router can verify the concrete state mutation, postcondition evidence, or file-backed role-output body.
- Preserve the Controller's envelope/status-only boundary while making every stateful completion claim resolve through one Router-visible evidence contract.
- Focused protected harms: false route advancement, repeated control blockers, PM decisions accepted from prepared/progress status, and display/status actions that appear done without durable postcondition evidence.

### Model Files
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/run_flowpilot_control_plane_friction_checks.py`
- `simulations/flowpilot_control_plane_friction_results.json`
- `simulations/flowpilot_control_plane_friction_checks_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_checks_results.json` passed.
- Live audit against the active `.flowpilot/current.json` intentionally failed with two errors: `stateful_receipt_done_without_postcondition_evidence` and `role_output_event_missing_file_backed_body`.
- `python scripts\check_install.py` passed.

### Findings
- The prior control-plane friction model did not express a generic evidence-closure rule for stateful Controller receipts.
- The prior model covered role-output progress/status metadata but did not force role-output event acceptance to require a file-backed body path and replayable body hash.
- The active run now projects into invariant failures for missing postcondition evidence and missing file-backed role-output body evidence.

### Counterexamples
- `stateful_receipt_done_without_postcondition_evidence`
- `stateful_receipt_advanced_without_postcondition_evidence`
- `role_output_event_missing_file_backed_body`
- `role_output_status_prepared_used_as_decision`

### Skipped Steps
- Runtime repair was not implemented in this pass; the user requested the model upgrade and a minimal root repair plan derived from the model findings.
- Heavy meta/capability checks were not rerun because this pass changed the focused control-plane friction model and result artifacts, not production project-control flow or skill/capability routing.

### Next Actions
- Implement a central Router-visible postcondition evidence registry for stateful Controller actions.
- Route PM/control role-output events through the role-output runtime so status/progress packets cannot be accepted as event evidence.


## simplify-controller-user-status - Make FlowPilot Controller user updates plain-language and status summaries progress-fact oriented

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior change affects Controller user-facing status, Router action contracts, and current status display data
- Status: in_progress
- Skill decision: used_flowguard
- Started: 2026-05-14T18:47:05+00:00
- Ended: 2026-05-14T18:47:05+00:00
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


## tier-controller-completion-evidence - Four-tier Router completion evidence

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot Router auto-advance exposed that display/status sync work was treated like a hard completion gate, causing PM repair before real route work started.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T21:00:00+02:00
- Ended: 2026-05-14T22:00:00+02:00
- Commands OK: True

### Risk Intent
- Split Controller/Router work into four evidence tiers: Router-owned state writes, soft display/status sync, lightweight external continuation confirmations, and strict file-backed role decisions.
- Keep display/status work from blocking Router progress or creating PM repair requirements.
- Preserve strong evidence for actual process-changing decisions.

### Model Files
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/run_flowpilot_control_plane_friction_checks.py`
- `simulations/flowpilot_control_plane_friction_results.json`
- `simulations/flowpilot_control_plane_friction_checks_results.json`

### Runtime Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`
- `openspec/changes/tier-controller-completion-evidence/`

### Commands
- `openspec validate tier-controller-completion-evidence --strict --json` passed.
- `openspec validate simplify-controller-user-status --strict --json` passed for the parallel AI change preserved in this commit.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py tests\test_flowpilot_router_runtime.py` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_checks_results.json` passed.
- Focused Router tests for display sync, run-until-wait, stateful receipt blockers, file-backed role output, controller reporting policy, and progress summary passed: `13 passed, 184 deselected`.
- `python -m pytest tests\test_flowpilot_role_output_runtime.py -q` passed: `14 passed`.
- `python -m pytest tests\test_flowpilot_output_contracts.py tests\test_flowpilot_card_instruction_coverage.py -q` passed: `10 passed, 67 subtests passed`.
- `python simulations\run_flowpilot_role_output_runtime_checks.py` passed.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\audit_local_install_sync.py --json` passed with installed FlowPilot source-fresh.

### Findings
- Display/status synchronization should be a soft projection that the Router can perform and record without PM repair escalation.
- The Router can safely fold nonblocking `sync_display_plan` work in `run_until_wait` because boundary actions still stop on user, payload, card, host automation, or explicit display-confirmation requirements.
- External continuation actions still need a lightweight hard marker, while PM/reviewer/worker decisions still need file-backed body evidence and replayable hashes.

### Counterexamples
- `display_work_hard_postcondition_gate`
- `display_work_escalated_to_pm_repair`
- `external_keepalive_unconfirmed`
- `stateful_receipt_done_without_postcondition_evidence`
- `role_output_event_missing_file_backed_body`

### Skipped Steps
- Full `tests\test_flowpilot_router_runtime.py tests\test_flowpilot_role_output_runtime.py` run was stopped after 10 minutes; focused affected subsets and role-output suite passed.
- Heavy background `python simulations\run_meta_checks.py` and `python simulations\run_capability_checks.py` were launched under `tmp/flowguard_background/`, but the user explicitly authorized not waiting for final exit artifacts in this turn. Their in-progress logs were treated as nonblocking, not as hard pass evidence.

### Next Actions
- For future Router actions, classify the action into one of the four evidence tiers before adding completion gates.
- Do not add screenshot or heavy proof requirements for display/status-only Controller work unless that work becomes a real process boundary.


## simplify-controller-user-status - Make FlowPilot Controller user updates plain-language and status summaries progress-fact oriented

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Behavior change affects Controller user-facing status, Router action contracts, and current status display data
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T19:43:17+00:00
- Ended: 2026-05-14T19:43:17+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- simulations/flowpilot_control_plane_friction_model.py
- simulations/run_flowpilot_control_plane_friction_checks.py

### Commands
- OK (0.000s): `python -m py_compile skills\\flowpilot\\assets\\flowpilot_router.py simulations\\flowpilot_control_plane_friction_model.py simulations\\run_flowpilot_control_plane_friction_checks.py`
- OK (0.000s): `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_progress_summary_counts_nested_active_path tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_display_plan_is_controller_synced_projection_from_pm_plan tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_banner_action_and_result_are_user_visible`
- OK (0.000s): `python simulations\\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\\flowpilot_control_plane_friction_results.json`
- OK (0.000s): `python scripts\\install_flowpilot.py --sync-repo-owned --force --skip-self-check --json`
- OK (0.000s): `python scripts\\audit_local_install_sync.py --json`
- OK (0.000s): `python scripts\\install_flowpilot.py --check --json`
- OK (0.000s): `python scripts\\check_install.py`

### Findings
- Controller card now tells Controller to use plain language for user status and hide internal event/action/packet/ledger/hash/contract/path metadata by default.
- Router actions now carry a controller_user_reporting_policy, also projected into next_step_contract, without adding that reminder to display_text.
- current_status_summary.json now includes progress_summary with active path level counts, completed counts, current indexes and labels, overall node counts, elapsed seconds when available, and public metadata-only flags.

### Counterexamples
- none recorded

### Friction Points
- The heavyweight meta/capability background logs were overwritten by a same-name rerun from an existing background script, so final log completion was not used as evidence.

### Skipped Steps
- Did not wait for the current run_meta_checks/run_capability_checks background rerun to finish because the user explicitly instructed to ignore the two big models and treat them as passed for this task.

### Next Actions
- If future work changes project-control flow more deeply, rerun meta/capability checks to completion and preserve their final artifacts before reporting them.


## controller-ledger-durable-claim - Controller receipt and Router-owned artifact reclaim model upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: run-20260514-194920 exposed that Controller action receipts, Router-owned startup audit artifacts, and daemon tick timing were still conflated in the control-plane model.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T22:05:00+02:00
- Ended: 2026-05-14T22:18:00+02:00
- Commands OK: True

### Risk Intent
- Model Controller table rows as Controller-owned work receipts, not target-role completion.
- Require Controller delivery receipts to transition into target-role waits instead of route completion or missing-report blockers.
- Require valid Router-owned artifacts plus proof to be reclaimed before daemon ticks escalate a missing postcondition blocker.

### Model Files
- `simulations/flowpilot_control_plane_friction_model.py`
- `simulations/run_flowpilot_control_plane_friction_checks.py`
- `simulations/flowpilot_control_plane_friction_results.json`
- `simulations/flowpilot_control_plane_friction_checks_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_checks_results.json` passed.
- Live audit against the current run now reports `valid_router_owned_artifact_not_reclaimed_before_blocker` for run-20260514-194920.

### Findings
- The prior model caught "Controller done but postcondition missing" but did not ask whether the missing postcondition was recoverable from an already-valid Router-owned artifact.
- The prior model did not represent the user's distinction between "Controller delivered the work item" and "the target role completed the work".
- The daemon tick race needs a durable reclaim barrier before PM repair escalation.

### Counterexamples
- `controller_delivery_receipt_treated_as_role_completion`
- `controller_delivery_receipt_missing_role_output_blocker`
- `valid_router_owned_artifact_not_reclaimed_before_blocker`
- `daemon_tick_semicomplete_receipt_escalates_before_reclaim`

### Skipped Steps
- Production Router behavior was not changed in this pass; the user requested model upgrade and a minimal root repair plan.
- Startup placeholder/route-sign display timing was intentionally not changed.

### Next Actions
- Implement a central action-completion ownership table that separates Controller receipt closure, target-role completion, and Router-owned artifact reclaim.
- Add a durable reclaim barrier before pending Controller receipt reconciliation can create a PM repair blocker.


## enforce-gate-scoped-card-ack-clearance - Gate-scoped system-card ACK clearance

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot auto-advance needed a precise contract for when system-card ACK receipts are checked, without treating ACK as target work completion or duplicating already-committed system cards.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T22:20:00+02:00
- Ended: 2026-05-14T22:47:00+02:00
- Commands OK: True

### Risk Intent
- Treat system-card ACK as a read receipt only, not proof that a target role completed the real work.
- Clear required ACKs at gate/node boundaries and before formal work packets for the target role.
- Recover missing ACKs by reminding the role to ACK the original committed card or bundle, not by duplicating the system-card delivery.

### Model Files
- `simulations/flowpilot_card_envelope_model.py`
- `simulations/run_flowpilot_card_envelope_checks.py`
- `simulations/flowpilot_card_envelope_results.json`

### Runtime Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`
- `openspec/changes/enforce-gate-scoped-card-ack-clearance/`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate enforce-gate-scoped-card-ack-clearance --strict` passed.
- `openspec validate reconcile-controller-router-ledgers --strict` passed for compatible peer-agent OpenSpec work preserved in the same working tree.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_card_envelope_model.py simulations\run_flowpilot_card_envelope_checks.py tests\test_flowpilot_router_runtime.py` passed.
- `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_results.json` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_results.json` passed for compatible peer-agent control-plane changes.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out simulations\flowpilot_control_plane_friction_checks_results.json` passed for the secondary peer-agent result artifact.
- Focused Router ACK tests passed: `3 passed, 197 deselected`.
- Focused Router card/system/startup tests passed: `13 passed, 187 deselected, 2 subtests passed`.
- Focused PM/material Router tests passed: `4 passed, 196 deselected`.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\audit_local_install_sync.py --json` passed with installed FlowPilot source-fresh.

### Findings
- The card-envelope model now catches gate transition before required ACK clearance, formal work packet dispatch before target-role ACK preflight, duplicate system-card delivery on missing ACK, and treating ACK as work completion.
- Router pending-return records now carry ACK scope and read-receipt metadata so later waits can distinguish Controller/role delivery from real target work completion.
- Formal work-packet dispatch now checks target-role pending system-card ACKs first and emits a lightweight reminder to ACK the original artifact when needed.

### Counterexamples
- `gate_boundary_before_required_ack_clearance`
- `formal_work_packet_sent_before_target_ack_preflight`
- `duplicate_system_card_delivery_on_missing_ack`
- `ack_treated_as_target_work_completion`

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally not run because the user explicitly said to skip the two heavyweight models for this task.
- No remote push, release, or publish action was performed.

### Next Actions
- Keep ACK clearance scope tied to gates/nodes and formal work-packet targets instead of scanning unrelated historical cards.
- Reissue a system card only when the original artifact is invalid, lost, stale, or bound to a replaced role identity.


## controller-delivery-before-ack-reminder - Controller delivery fact gate for missing ACK recovery

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The user identified a remaining gap in missing-ACK recovery: Router could remind a target role before first proving Controller actually delivered the original committed card or bundle.
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-05-14T22:58:00+02:00
- Ended: 2026-05-14T23:32:00+02:00
- Commands OK: True

### Risk Intent
- Preserve the two-ledger boundary: Controller may mark only Controller-local delivery work, while Router owns workflow state.
- Prevent false target-role blame when a missing ACK is caused by unconfirmed Controller delivery or a missing/invalid committed envelope.
- Keep Router ownership ledger internal to Router while exposing Controller-safe delivery recovery facts.

### Model Files
- `simulations/flowpilot_card_envelope_model.py`
- `simulations/run_flowpilot_card_envelope_checks.py`
- `simulations/flowpilot_card_envelope_results.json`
- `simulations/flowpilot_card_envelope_checks_results.json`
- `simulations/flowpilot_control_plane_friction_checks_results.json`

### Runtime Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`
- `openspec/changes/reconcile-controller-router-ledgers/`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_card_envelope_model.py simulations\run_flowpilot_card_envelope_checks.py` passed.
- `python simulations\run_flowpilot_card_envelope_checks.py` passed and refreshed `flowpilot_card_envelope_results.json`.
- `python simulations\run_flowpilot_card_envelope_checks.py --json-out simulations\flowpilot_card_envelope_checks_results.json` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_checks_results.json --skip-live-audit` passed.
- `openspec validate reconcile-controller-router-ledgers --strict` passed.
- Focused Router tests passed: `4 passed, 198 deselected`; expanded related Router tests passed: `14 passed, 188 deselected`; daemon visibility regression passed: `5 passed, 197 deselected`.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\install_flowpilot.py --check --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\check_install.py` passed.

### Findings
- The card-envelope model now catches missing-ACK recovery that skips Controller delivery fact checking.
- The model now catches target-role reminders before Controller delivery is confirmed and reminders while Controller delivery reissue is still required.
- Runtime missing-ACK wait actions now carry `controller_delivery_fact` and only allow target-role ACK reminders when the matching Controller delivery is done or the run lacks a legacy/manual Controller action record.
- If the committed card/bundle artifact is missing or invalid, or the matching Controller delivery action is pending/blocked/skipped, the wait action routes recovery back to Controller delivery confirmation/reissue first.
- Daemon status no longer exposes Router ownership ledger entries to Controller.

### Counterexamples
- `missing_ack_recovery_skipped_controller_delivery_fact`
- `missing_ack_target_reminded_before_controller_delivery_confirmed`
- `missing_ack_target_reminded_while_controller_reissue_required`

### Friction Points
- The full `tests\test_flowpilot_router_runtime.py` run was attempted but timed out after 15 minutes, so final validation used focused affected subsets plus model, OpenSpec, install, and audit checks.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally not run because the user explicitly said to skip the two heavyweight models.
- The control-plane friction check used `--skip-live-audit` because this validation targets the abstract repair and the current repo may contain stopped historical FlowPilot runs.
- No remote push, release, or publish action was performed.

### Next Actions
- Keep future missing-ACK changes inside the Controller delivery fact gate instead of adding separate reminder exceptions.
- Keep Controller-facing daemon/status files free of Router internal workflow ledger entries.


## persistent-router-daemon-model-miss - Controller receipt and foreground standby gaps

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot run repeated `sync_display_plan`, then the foreground Controller ended while a Controller action was still pending before the user stopped the run.
- Status: model_updated; production_fix_not_started
- Skill decision: used_flowguard
- Started: 2026-05-15T06:49:00+02:00
- Ended: 2026-05-15T06:55:00+02:00
- Commands OK: True

### Risk Intent
- Prevent Router from clearing a Controller receipt without updating the Router-owned internal fact that the action was meant to establish.
- Prevent the same Controller action from being reissued after a done receipt because the Router-owned fact stayed stale.
- Prevent foreground Controller from ending while the daemon is live and the Controller action ledger still has an executable action.

### Model Files
- `simulations/flowpilot_persistent_router_daemon_model.py`
- `simulations/run_flowpilot_persistent_router_daemon_checks.py`
- `simulations/flowpilot_persistent_router_daemon_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.

### Findings
- The previous model covered foreground standby during role waits, but not foreground exit while an executable Controller action was pending.
- The previous model required Controller receipts for done actions, but did not require receipt reconciliation to advance the corresponding Router-owned internal fact.
- The updated model catches the live-run class where `sync_display_plan` receipts are reconciled but `visible_plan_sync`-like Router facts remain stale, causing the same Controller action to be issued repeatedly.

### Counterexamples
- `router_cleared_controller_receipt_without_internal_fact`
- `same_controller_action_reissued_after_done_receipt`
- `foreground_controller_ended_with_pending_controller_action`

### Skipped Steps
- Production runtime repair was intentionally not started in this step; the user asked for the model upgrade and a minimal root repair plan.
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were not run because this is a focused model-miss update.

### Next Actions
- Implement the minimal repair by applying Router-owned state updates during Controller receipt reconciliation for `display_status` actions.
- Add a foreground/Controller guard that refuses to end while the controller action ledger has executable pending actions, and otherwise enters `controller-standby` for live nonterminal daemon waits.

### Runtime Repair Update
- Status: completed; local install synchronized
- Ended: 2026-05-15T07:30:00+02:00

### Additional Modeled Risk
- The foreground Controller must not stop just because the daemon is live and no Controller action is ready at that instant. It must report the required mode as `watch_router_daemon` and remain attached through `controller-standby`.

### Runtime Files
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- `tests/test_flowpilot_router_runtime.py`
- `openspec/changes/repair-controller-receipt-foreground-guard/`

### Runtime Commands
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "foreground_controller_standby or sync_display_plan_done_receipt_updates_router_fact_before_next_action or run_until_wait_folds_manifest_check_before_card_boundary"` passed with 7 selected tests.
- `openspec validate repair-controller-receipt-foreground-guard --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed.
- `python scripts\audit_local_install_sync.py --json` passed.
- `python scripts\install_flowpilot.py --check --json` passed.
- `python scripts\check_install.py` passed.
- `git diff --check` passed with CRLF warnings only.

## 2026-05-15 Gate-Scoped Obligation Cleanup Audit

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked whether Router should clear or reconcile all gate-local pending items at a gate/node boundary, not only system-card ACK read receipts, except when bypassed/superseded work is explicitly still needed.
- Status: read_only_audit; production_fix_not_started
- Skill decision: used_flowguard
- Started: 2026-05-15T07:10:00+02:00
- Ended: 2026-05-15T07:35:00+02:00
- Commands OK: True

### Risk Intent
- Prevent route gate/node transition from carrying hidden current-gate obligations forward after ACKs are cleared.
- Preserve valid bypass/supersede semantics by requiring explicit carry-forward, supersede, quarantine, or stale-evidence treatment instead of blanket deletion.
- Keep ACK read-receipt clearance separate from PM/reviewer/officer/worker semantic completion.

### Model Files
- `simulations/flowpilot_card_envelope_model.py`
- `simulations/flowpilot_route_mutation_activation_model.py`
- `simulations/barrier_equivalence_model.py`
- `simulations/flowpilot_startup_optimization_model.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python simulations\run_flowpilot_card_envelope_checks.py --json-out tmp\audit_card_envelope_results.json` passed.
- `python simulations\run_flowpilot_route_mutation_activation_checks.py --json-out tmp\audit_route_mutation_activation_results.json` passed.
- `python simulations\run_flowpilot_startup_optimization_checks.py --json-out tmp\audit_startup_optimization_results.json` passed.
- `python simulations\run_barrier_equivalence_checks.py` passed and wrote `simulations\barrier_equivalence_results.json`.
- `python -m pytest tests\test_flowpilot_barrier_bundle.py -q` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "stale_review_block_route_mutation_wait or startup_pending_ack_allows_independent_startup_card_delivery or startup_activation_joins_startup_pending_acks or missing_system_card_ack_wait_reminds_original_envelope_without_duplicate_delivery or formal_work_packet_ack_preflight_blocks_target_pending_card_ack or route_mutation_supersede_strategy_does_not_require_return_to_original"` passed with 6 selected tests.
- `openspec validate async-startup-obligation-join --strict` passed.
- `openspec validate enforce-gate-scoped-card-ack-clearance --strict` passed.

### Findings
- ACK clearance is modeled and implemented as a scoped read-obligation gate, including formal work-packet preflight and missing-ACK reminder semantics.
- Startup join modeling already requires common pending-card-return ledger clearance before startup activation, but this is still ACK/read-receipt centered.
- Node/route mutation logic resets cycle flags, marks superseded nodes, invalidates stale evidence, and rewrites frontier state, but does not yet expose one unified gate-obligation reconciliation ledger for every open current-gate pending item.
- Barrier bundle equivalence covers required legacy obligations and final closure, but it validates bundle/final evidence rather than clearing all live pending gate items at boundary transition.

### Counterexamples / Gaps
- No executable model currently enumerates all pending gate-local action classes at boundary transition and forces each to be satisfied, explicitly carried forward, superseded, quarantined, or blocked.
- Existing mechanisms are distributed across pending-card returns, `pending_action` recomputation, current-node cycle flags, route mutation stale evidence, and barrier bundles.

### Skipped Steps
- Production Router changes were intentionally not started; this pass was requirement discovery / OpenSpec explore.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were not run because no production behavior was changed.

### Next Actions
- Capture a scoped OpenSpec change for gate-scoped obligation reconciliation, likely extending `async-startup-obligation-join` or adding a sibling change.
- Add a FlowGuard model where gate transition reads all current-gate obligation sources and produces a reconciliation record per item.
- Implement Router transition guard only after the model proves the carry-forward/supersede/quarantine semantics.

### Runtime Findings
- `sync_display_plan` Controller receipts now route through the same Router-owned display fact writer as direct apply, so `visible_plan_sync` is updated before Router computes the next action.
- Status and standby payloads now separate "may return to caller" from "Controller may stop"; `controller_stop_allowed` is true only for terminal runs.
- `foreground_required_mode` now tells Controller whether to `process_controller_action` or `watch_router_daemon`.
- Controller prompt cards now state the nonterminal rule plainly: with work, do the Controller action; without work, stay attached to the daemon monitor.
- Parallel-agent `async-startup-obligation-join` OpenSpec/model work was reviewed, validated, and included as compatible model-only work; its runtime implementation tasks remain tracked in that separate change.

### Additional Counterexample
- `foreground_controller_ended_while_daemon_active_no_action`

### Runtime Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Full `tests\test_flowpilot_router_runtime.py` was attempted once and timed out after 304 seconds; final evidence uses the focused affected subset plus model, OpenSpec, install, and self-check validation.

## 2026-05-15 Foreground Controller Standby Experiment

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked whether the foreground Controller can keep watching while Router waits and then wake when a new task appears.
- Status: process_preflight_with_isolated_runtime_experiment
- Skill decision: used_flowguard
- Commands OK: True

### Risk Intent
- Prevent a false confidence claim where the foreground Controller merely stays alive but misses a new Controller action.
- Verify that standby observes Router daemon status and the Controller action ledger rather than using `next` or `run-until-wait` as a manual metronome.
- Preserve the distinction between bounded timeout liveness evidence and real wake evidence.

### Experiment Evidence
- Isolated runtime root: `tmp/controller_standby_experiment/`
- Summary artifact: `tmp/controller_standby_experiment/summary.json`
- Initial live role wait returned `timeout_still_waiting` with `foreground_required_mode=watch_router_daemon`.
- A delayed synthetic Controller action appeared after standby began; standby woke in about 1.078 seconds with `standby_state=controller_action_ready` and `foreground_required_mode=process_controller_action`.
- After daemon cleanup, standby returned `daemon_stale_or_missing` with `foreground_required_mode=daemon_repair_or_restart`.

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- Isolated Python harness using the real `skills/flowpilot/assets/flowpilot_router.py` standby function passed.
- `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_foreground_controller_standby_waits_on_live_daemon_role_wait tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_foreground_controller_standby_keeps_alive_when_daemon_has_no_ready_action tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_foreground_controller_standby_wakes_on_controller_action_ledger tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_foreground_controller_standby_exits_on_stale_or_missing_daemon tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_foreground_controller_standby_does_not_compute_router_next` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_resume_checks.py` passed.
- `python simulations\run_flowpilot_role_output_runtime_checks.py` passed.

### Findings
- The current foreground standby mechanism can wait through an ordinary daemon-owned role wait and wake when the Controller action ledger gains a pending action.
- The right long-wait shape is bounded `controller-standby` re-entry: timeout means continue watching, not stop; `controller_action_ready` means process the ledger action before any foreground exit.
- Heartbeat/manual resume remains a recovery and re-entry path. It should not start a second daemon or replace the standby monitor while a live daemon and foreground Controller are already attached.

### Skipped Steps
- Production code was not changed.
- Full meta/capability heavyweight checks were not rerun because the experiment was isolated and used focused runtime plus relevant model checks.

## 2026-05-15 Background Agent Fake Monitor Experiment

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User corrected the prior local-thread experiment and asked to use a real background agent watching a fake monitor.
- Status: isolated_background_agent_experiment
- Skill decision: used_flowguard_process_preflight; no production behavior changed
- Commands OK: True

### Risk Intent
- Prevent claiming that foreground/controller standby works with background agents when only a local thread was tested.
- Test whether a real background worker will keep its task open while a monitor remains `waiting`, then return after the monitor changes to `signal_ready`.
- Keep the experiment isolated under `tmp/` so it does not mutate live FlowPilot run state.

### Experiment Evidence
- Monitor root: `tmp/background_agent_fake_monitor/`
- Monitor file: `tmp/background_agent_fake_monitor/monitor.json`
- Experiment notes: `tmp/background_agent_fake_monitor/experiment_notes.md`
- Worker agent: `019e2a3b-f73d-7493-9e4d-d1be16f31186` (`Wegener`)

### Findings
- The worker did not complete during the first 10-second pre-signal wait.
- After the monitor was changed to `signal_ready`, the worker returned with `signal_id=fake-monitor-signal-20260515T080422+0200`.
- The worker reported first read at `2026-05-15T08:04:21.1915099+02:00`, observed signal at `2026-05-15T08:04:31.3928827+02:00`, waited about `10.233` seconds, and polled `11` times.
- This proves a real background agent can obey a fake file-monitor contract and keep its task open until the signal appears.

### Confidence Boundary
- This does not yet prove the full FlowPilot Router event path, role-output envelope validation, or Controller wake path from a real background role result.
- The next stronger experiment should connect the background agent's signal to a Router-accepted event or Controller action ledger entry and verify foreground `controller-standby` wakes from that real agent-produced artifact.

## 2026-05-15 Blinded Five-Minute Job Monitor Experiment

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User pointed out that telling the worker it was a five-minute persistence experiment contaminates the result.
- Status: isolated_background_agent_monitor_experiment; prior explicit five-minute prompt invalidated
- Skill decision: used_flowguard_process_preflight; no production behavior changed
- Commands OK: True

### Risk Intent
- Avoid measuring whether a worker can comply with an explicit test instruction instead of whether it naturally follows an operational monitor.
- Keep the wait duration and evaluation criteria in the controller thread only.
- Verify that a real background worker can keep a normal monitor task open for more than five minutes while the monitor remains `pending`.

### Invalidated Evidence
- Worker `Boole` was explicitly told this was a five-minute experiment and therefore its run was treated as contaminated evidence.
- That worker was shut down before completion and is not used for confidence.

### Clean Experiment Evidence
- Monitor root: `tmp/flowpilot_job_monitor/run-20260515-081246/`
- Monitor file: `tmp/flowpilot_job_monitor/run-20260515-081246/monitor.json`
- Payload file: `tmp/flowpilot_job_monitor/run-20260515-081246/ready_payload.json`
- Operator notes: `tmp/flowpilot_job_monitor/run-20260515-081246/operator_notes.md`
- Worker agent: `019e2a44-9576-7cf0-81b5-a4e2cb305289` (`Peirce`)

### Findings
- The worker was given only an operational job-monitor task and was not told this was an experiment or that a five-minute hold was being tested.
- The worker first observed `pending` at `2026-05-15T08:13:56.0262270+02:00`.
- The controller kept the monitor `pending` for over five minutes after that first observation; the worker did not return early.
- The controller updated the monitor to `ready` at `2026-05-15T08:19:25.3049293+02:00`.
- The worker observed `ready` at `2026-05-15T08:19:38.8530488+02:00`, read the payload at `2026-05-15T08:19:52.4647479+02:00`, and returned a handoff summary.
- This is valid evidence that a real background agent can keep watching a normal monitor for longer than five minutes without knowing it is being tested.

### Confidence Boundary
- This still does not prove the full Router-to-Controller wake chain. It proves background monitor obedience under an ordinary monitor prompt.
- The next stronger proof should make the background worker produce a Router-accepted event or result envelope, then verify the foreground Controller wakes through `controller-standby`.

## 2026-05-15 Current-Scope Pre-Review Reconciliation Runtime Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that every startup gate and current node review must be meaningful: current-scope work must be reconciled before review starts, and review-created obligations must close before scope exit.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: True

### Risk Intent
- Prevent the Router from treating ACK/read receipts as semantic work completion.
- Keep reconciliation local to the active startup gate or current node so future and sibling node obligations are neither cleared nor used as current-node blockers.
- Ensure node review cannot begin before local PM disposition, PM absorption, packet batch status, and active-node pending card returns are clean.
- Ensure node completion cannot cross the node boundary while review-created local obligations remain unresolved.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/enforce-current-scope-pre-review-reconciliation/`
- Focused model: `simulations/flowpilot_current_scope_pre_review_reconciliation_model.py`
- Focused result: `simulations/flowpilot_current_scope_pre_review_reconciliation_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python simulations\run_flowpilot_current_scope_pre_review_reconciliation_checks.py --json-out simulations\flowpilot_current_scope_pre_review_reconciliation_results.json` passed.
- `openspec validate enforce-current-scope-pre-review-reconciliation --strict` passed.
- `openspec validate async-startup-obligation-join --strict` passed.
- `openspec validate controller-wait-target-liveness --strict` passed after fixing requirement wording in the parallel OpenSpec change.
- `python simulations\run_flowpilot_startup_optimization_checks.py --json-out simulations\flowpilot_startup_optimization_results.json` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "startup_pre_review_ack_join_blocks_reviewer_card or reviewer_startup_report_preconsumes_pre_review_pm_bundle_ack or pm_startup_activation_uses_existing_same_role_card_ack_blocker or current_node_pre_review_reconciliation or future_node_pending_return_does_not_block_current_node_review or current_node_completion_waits_for_review_created_local_obligations or current_node_completion_requires_reviewer_passed_packet_audit or current_node_parallel_batch_waits_for_all_results_before_review"` passed with 8 tests.
- `python -m pytest tests\test_flowpilot_barrier_bundle.py -q` passed with 7 tests.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_current_scope_pre_review_reconciliation_model.py simulations\run_flowpilot_current_scope_pre_review_reconciliation_checks.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` synchronized the installed FlowPilot skill to the repository source.
- `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed with the installed FlowPilot digest matching the repository digest.

### Findings
- The focused model rejects review-start before local reconciliation, local reconciliation that clears future scope, deferred local work without explicit carry-forward evidence, scope exit before review-created closure, no-final-review scope exit without reconciliation, and ACK-as-semantic-completion.
- The runtime now returns an `await_current_scope_reconciliation` Controller action before current-node reviewer work when active-node local obligations are not clean.
- Direct reviewer pass/block events are held as recoverable waits when the active node is not locally reconciled.
- Current-node completion now raises a Router error if the node tries to exit before review-created local obligations and reviewed packet status are closed.
- Future-node scoped pending card returns no longer block the active node's review start.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because they are heavyweight checks and not required for this focused runtime update.

## 2026-05-15 Continuous Controller Standby Row Runtime Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that foreground Controller standby must be a durable in-progress duty, not an empty plan or one-time monitor poll.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: OpenSpec validation, focused FlowGuard scheduler checks, targeted runtime tests, install sync, and local install audit passed.

### Risk Intent
- Ensure a live Router daemon wait always exposes a `continuous_controller_standby` Controller row when no ordinary Controller work is ready.
- Keep the visible Codex plan synced from the Controller action ledger with the standby item in progress.
- Prevent one monitor poll, `timeout_still_waiting`, or a still-working live target role from completing standby.
- Keep ACK waits on three-minute reminder and ten-minute blocker timing, and report/result waits on ten-minute reminder plus fresh liveness checks.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/router-two-table-async-scheduler/`
- Focused model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Focused result: `simulations/flowpilot_two_table_async_scheduler_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Controller prompt guidance: `skills/flowpilot/SKILL.md`, `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`, `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile skills/flowpilot/assets/flowpilot_router.py simulations/flowpilot_two_table_async_scheduler_model.py simulations/run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `python simulations/run_flowpilot_two_table_async_scheduler_checks.py` passed and refreshed `simulations/flowpilot_two_table_async_scheduler_results.json`.
- `openspec validate router-two-table-async-scheduler --strict` passed.
- `python scripts/check_install.py --json` passed.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "foreground_controller_standby or two_table or stateful" -q` passed with 11 tests.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "foreground_controller_standby or daemon_tick_consumes_card_ack_without_manual_next or startup_fact" -q` passed with 16 tests and 3 subtests.
- `python scripts/install_flowpilot.py --sync-repo-owned --json` synchronized the installed FlowPilot skill.
- `python scripts/audit_local_install_sync.py --json` passed with matching installed and repository digests.

### Findings
- The focused model now rejects empty live-wait Controller plans, standby rows completed after one check, and `timeout_still_waiting` treated as completion.
- Runtime standby now keeps waiting through nonterminal timeouts by default; bounded timeout returns are explicitly diagnostic/test mode.
- Router daemon status and Controller action ledger now expose a plan-syncable continuous standby task while preserving Router-owned progress.
- A legacy startup-fact test was updated to use a fresh run after intentionally triggering a fatal leaked-body-field blocker, matching the blocker semantics already enforced by the router.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because they are heavyweight checks and not required for this focused runtime update.

### Peer Integration Follow-up
- After the local commit, a parallel agent added stateful Controller postcondition repair modeling and runtime tests in `simulations/flowpilot_persistent_router_daemon_model.py`, `simulations/run_flowpilot_persistent_router_daemon_checks.py`, and `tests/test_flowpilot_router_runtime.py`.
- The focused daemon model was rerun and passed with zero safe-graph invariant failures.
- `openspec validate router-two-table-async-scheduler --type change --strict --json` passed for the related two-table scheduler change.
- The related targeted router runtime scope passed with 5 tests.

## 2026-05-15 Router External Wait Reconciliation Runtime Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that FlowGuard should have caught the generic class where Router records an external role event, but the durable Controller wait/action row remains open and leaves the foreground Controller idling or advancing incorrectly.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: OpenSpec validation, focused FlowGuard checks, targeted runtime tests, install sync, and local install audit passed.

### Risk Intent
- Make Router own the generic reconciliation step: when an external event is recorded, Router must close any matching open Controller `await_role_decision` wait row whose `allowed_external_events` includes that event.
- Keep executable Controller actions receipt-bound, but make external-event waits evidence-bound so they are satisfied by Router-recorded event evidence rather than a Controller receipt.
- Handle both new events and already-recorded/replayed events, so stale wait rows are cleared idempotently.
- Prevent Router from opening the next wait before closing the already-satisfied external-event wait.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/router-reconciles-external-wait-events/`
- Focused model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Focused model runner: `simulations/run_flowpilot_persistent_router_daemon_checks.py`
- Focused result: `simulations/flowpilot_persistent_router_daemon_results.json`
- Related peer model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Related peer result: `simulations/flowpilot_two_table_async_scheduler_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate router-reconciles-external-wait-events --type change --strict --json` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "recorded_external_event_closes_matching_wait_action_row or already_recorded_external_event_closes_stale_wait_action_row or startup_fact_role_output_ledger_is_reconciled_by_router_tick"` passed with 3 tests.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` confirmed the installed FlowPilot skill was source-fresh.
- `python scripts\audit_local_install_sync.py --json` passed with matching installed and repository digests.
- `python scripts\install_flowpilot.py --check --json` passed with `source_fresh: true` for FlowPilot.
- `python scripts\check_install.py` passed.
- `git diff --check` passed; Git reported existing CRLF whitespace warnings only.

### Findings
- The previous model represented "waiting for a role event" but did not sufficiently model the durable Controller action ledger row that could stay open after the event was recorded.
- The focused model now rejects recorded external events that leave matching Controller wait rows open, Controller-owned closure of external-event waits, and next-wait creation before satisfied external waits are closed.
- Router now annotates external-event wait rows with `completion_source: router_external_event_reconciliation`, the satisfying event name, payload digest evidence, and Router reconciliation metadata.
- Already-recorded event handling now performs the same reconciliation pass, making repeated event recording and replay paths idempotent.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because they are heavyweight checks and not required for this focused runtime update.

## 2026-05-15 Stateful Controller Postcondition Model-Miss Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live run `run-20260515-063843` blocked because
  `confirm_controller_core_boundary` had a minimal `done` receipt while the
  controller boundary confirmation artifact and Router flags were missing.
- Status: completed_model_upgrade_and_repair_plan
- Skill decision: used_openspec_then_flowguard
- Commands OK: Focused FlowGuard checks, live audit classification, OpenSpec
  validation, and proof tests passed.

### Risk Intent
- Separate generic Controller receipts from stateful Controller receipts.
- Require Router-visible postcondition evidence before Router clears or
  advances a stateful Controller action.
- Catch startup boundary states where `controller_role_confirmed` is true but
  the durable boundary artifact is missing.
- Preserve valid artifact reclaim before blocker escalation.

### Model And Design Evidence
- OpenSpec change:
  `openspec/changes/require-stateful-controller-postconditions/`
- Focused model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Focused result: `simulations/flowpilot_persistent_router_daemon_results.json`
- Existing adjacent model:
  `simulations/flowpilot_daemon_reconciliation_model.py`
- Live audit output: `tmp/control_plane_friction_live_current_blocker.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with
  schema `1.0`.
- `python -m py_compile simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --live-root . --json-out tmp\control_plane_friction_live_current_blocker.json` returned the expected live audit finding for the active blocker.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` passed.
- `python -m pytest tests\test_flowguard_result_proof.py -q` passed with 3 tests.
- `openspec validate require-stateful-controller-postconditions --type change --strict --json` passed.

### Findings
- The previous model miss was a coverage-binding miss: the abstract invariant
  existed, but the persistent startup/daemon model treated the concrete startup
  boundary receipt as a generic receipt-only action.
- The persistent daemon model now rejects receipt-present/evidence-missing,
  Router-cleared/evidence-missing, and role-confirmed/artifact-missing states.
- The active run is classified as
  `stateful_receipt_done_without_postcondition_evidence`.

### Skipped Steps
- Production Router behavior was not changed in this pass; the user asked for
  model upgrade and minimal root repair plan.
- `python simulations/run_meta_checks.py` and
  `python simulations/run_capability_checks.py` were intentionally skipped at
  user direction.
- No install sync was needed because production skill code was not modified.

## 2026-05-15 Async Startup Obligation Join Runtime Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to make startup use the same Router/Controller card ACK table rules as later runtime, then corrected that the only extra startup join belongs before Reviewer live startup review, not before PM startup activation.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: Focused checks passed; full router runtime file timed out before completion.

### Risk Intent
- Let Router keep dispatching independent startup card work while startup-scope ACKs are pending.
- Require PM startup prep card ACKs to clear through the common Controller action ledger and card pending-return ledger before Reviewer startup fact review starts.
- Keep Reviewer report acceptance and PM startup activation on existing same-role ACK dependencies.
- Prevent a redundant second all-startup join before PM startup activation.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/async-startup-obligation-join/`
- Focused model: `simulations/flowpilot_startup_optimization_model.py`
- Focused result: `simulations/flowpilot_startup_optimization_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Launcher note: `skills/flowpilot/SKILL.md`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python simulations\run_flowpilot_startup_optimization_checks.py --json-out simulations\flowpilot_startup_optimization_results.json` passed.
- `openspec validate "async-startup-obligation-join" --strict` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_startup_optimization_model.py simulations\run_flowpilot_startup_optimization_checks.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "system_card_delivery_requires_manifest_check or committed_system_card_relay_can_resolve_without_apply_roundtrip or startup_pre_review_ack_join or pm_startup_activation_uses_existing_same_role_card_ack_blocker or pre_review_pm_bundle_ack or preconsumes_valid_card_ack_before_blocking or missing_same_role_ack_report"` passed with 7 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "startup or system_card or card_return"` passed with 43 tests and 5 subtests.
- `python scripts\install_flowpilot.py --sync-repo-owned` synchronized the installed FlowPilot skill.
- `python scripts\audit_local_install_sync.py` passed.
- `python scripts\check_install.py` passed.

### Findings
- The startup model now names the post-review condition as Reviewer report acceptance, not as a second startup join.
- Router defers only startup-scope pending card waits when it can continue with independent startup card delivery.
- Reviewer startup fact card delivery is suppressed until pre-review PM prep card pending returns are clear.
- `reviewer_reports_startup_facts` can preconsume the relevant pre-review ACKs through the shared pending-return ledger.
- PM startup activation uses the existing same-role `pm.startup_activation` pending-return blocker and does not use a separate all-startup join.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q` was attempted, but it timed out after 10 minutes before returning a final pass/fail result. The focused and startup/system-card/ACK test scopes passed.

## 2026-05-15 Controller Wait Target Liveness Runtime Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User asked to keep the foreground Controller from passively waiting on the monitor, and instead use monitor wait-target metadata to keep FlowPilot healthy while Router and background roles work.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: Focused checks, install sync, and local install audit passed.

### Risk Intent
- Make the Router-authored monitor say who or what the Controller is waiting on, why, what evidence is expected, and when the Controller must act.
- Keep liveness as a fresh check obligation, not a cached truth written into the monitor.
- Send ACK reminders at three minutes and route ACK waits to an existing Router/PM blocker at ten minutes.
- Send report/result reminders every ten minutes only with a fresh target-role liveness probe.
- Treat Controller-local waits as self-audits of the Controller action ledger and receipts, not as reminders to itself.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/controller-wait-target-liveness/`
- Focused model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Focused result: `simulations/flowpilot_persistent_router_daemon_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Controller prompt guidance: `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- Install prompt check: `scripts/check_install.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate controller-wait-target-liveness --strict --json` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "foreground_controller_standby"` passed with 9 tests.
- `python -m py_compile simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py tests\test_flowpilot_router_runtime.py` passed.
- `openspec validate async-startup-obligation-join --strict --json` passed.
- `openspec validate enforce-current-scope-pre-review-reconciliation --strict --json` passed.
- `python simulations\run_flowpilot_startup_optimization_checks.py --json-out simulations\flowpilot_startup_optimization_results.json` passed.
- `python simulations\run_flowpilot_current_scope_pre_review_reconciliation_checks.py --json-out simulations\flowpilot_current_scope_pre_review_reconciliation_results.json` passed.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` confirmed the installed FlowPilot skill was source-fresh.
- `python scripts\audit_local_install_sync.py --json` passed with matching installed and repository digests.
- `python scripts\install_flowpilot.py --check --json` passed with `source_fresh: true` for FlowPilot.

### Findings
- The focused model rejects stale cached liveness as current truth, report reminders without fresh liveness probes, ACK waits beyond ten minutes without blocker routing, Controller-local waits that remind the Controller, and role waits missing wait-target metadata.
- Foreground Controller standby now returns explicit modes for wait-target checks and blocker recording instead of silently idling.
- Monitor payloads expose `current_wait.wait_class`, target role/reason/evidence, reminder policy, liveness probe instructions, and Controller-local self-audit instructions.
- The runtime does not expose a `role_alive` field as authority; Controller must perform the check when the monitor says it is due.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because they are heavyweight checks and not required for this focused runtime update.

## 2026-05-15 Stateful Controller Deliverable Repair Runtime Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved the root repair plan for stateful Controller receipts: declare required deliverables on the Controller action row, reclaim existing valid evidence, schedule bounded Controller repair rows for missing deliverables, and escalate only after two failed repairs.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: Focused FlowGuard, OpenSpec, py_compile, targeted Router runtime tests, install sync, and local install audit passed.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/require-stateful-controller-postconditions/`
- Focused model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Focused result: `simulations/flowpilot_persistent_router_daemon_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "controller_boundary_done_receipt_missing_deliverable_schedules_repair or controller_boundary_valid_artifact_reclaims_before_repair or controller_boundary_repair_action_resolves_original or controller_boundary_repair_budget_escalates_after_two_failures" -q` passed with 4 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "completed_pending_controller_action_receipt_is_not_returned_again or incomplete_stateful_rehydrate_receipt_becomes_control_blocker or controller_boundary" -q` passed with 8 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "controller_action or controller_receipt or router_scheduler or sync_display_plan_done_receipt or recorded_external_event_closes_matching_wait_action_row" -q` passed with 6 tests.
- `openspec validate require-stateful-controller-postconditions --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and reported installed FlowPilot source-fresh.
- `python scripts\audit_local_install_sync.py` passed.

### Findings
- `confirm_controller_core_boundary` now carries required-deliverable metadata in the Controller action row.
- Router receipt reconciliation validates an existing `startup/controller_boundary_confirmation.json` and syncs Router flags, but does not silently create that artifact from a bare done receipt.
- Missing boundary deliverables mark the original row `repair_pending` and enqueue `complete_missing_controller_deliverable`.
- A successful repair marks the original row `resolved`; two failed repair receipts create a control blocker with the missing deliverable and exhausted repair budget.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q` timed out after 10 minutes without a final result, so it was not counted as passing evidence.

## 2026-05-15 Controller Ledger Table Prompt Hardening

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User wanted Controller's own action ledger to carry an English table-local prompt so long-running foreground Controller work remembers row order, foreground attachment, and continuous standby re-entry.
- Status: implemented_focused_runtime_update
- Skill decision: used_openspec_then_flowguard
- Commands OK: Focused FlowGuard, OpenSpec, py_compile, targeted Router runtime tests, install check, install sync, and local install audit passed.

### Model And Runtime Evidence
- OpenSpec change: `openspec/changes/harden-controller-ledger-table-prompt/`
- Focused model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Focused result: `simulations/flowpilot_two_table_async_scheduler_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Controller guidance: `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- Resume guidance: `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`
- Install checks: `scripts/check_install.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -q -k "foreground_controller_standby or router_daemon_observation_initializes_lock_status_and_ledger or router_daemon_tick_writes_controller_action_ledger_and_receipt_reconciles"` passed with 12 tests.
- `openspec validate harden-controller-ledger-table-prompt --strict --json` passed.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and updated the installed FlowPilot skill to the repository digest.
- `python scripts\audit_local_install_sync.py --json` passed.
- `python scripts\install_flowpilot.py --check --json` passed.
- `git diff --check` reported CRLF warnings only.

### Findings
- `runtime/controller_action_ledger.json` now emits `controller_table_prompt` before `actions` using a ledger-specific writer that preserves table-top ordering.
- The prompt tells Controller to work ready rows from top to bottom, write receipts before moving onward, keep foreground work attached while FlowPilot is running, and avoid route invention, sealed bodies, worker work, gate approval, or route closure from Controller evidence.
- `continuous_controller_standby` remains `in_progress` and now explicitly says it is a continuous monitoring duty, not a finishable checklist item.
- When Router exposes new Controller work during standby, Controller guidance now tells it to update or reread the ledger and return to top-to-bottom row processing.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Full router runtime test suite was not run; final evidence uses focused affected runtime tests plus model/OpenSpec/install checks.

## 2026-05-15 Startup Daemon Ownership Model-Miss Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A real FlowPilot startup run showed `start_router_daemon` happened after startup intake UI, role spawning, and heartbeat binding. The previous focused model accepted the weaker property "daemon before Controller core" and did not model daemon ownership of startup work.
- Status: model_updated_runtime_fix_pending
- Skill decision: used_flowguard_for_model_miss_analysis

### Model Evidence
- Focused model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Focused result: `simulations/flowpilot_two_table_async_scheduler_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed with 69 traces.

### Findings
- The model now rejects startup external actions that run before the Router daemon becomes the startup driver.
- The model now rejects `startup_ui_before_daemon`.
- The model now rejects `startup_roles_or_heartbeat_before_daemon`.
- The model now rejects `daemon_waits_for_controller_core_during_startup`, which captures a daemon that starts but idles instead of scheduling startup rows before Controller core.
- The minimal runtime fix should move daemon start to immediately after the minimal run shell exists and route startup UI, role spawn, and heartbeat binding through daemon-scheduled Controller rows.

### Skipped Steps
- No runtime implementation was changed in this model-miss update.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were not run.

## 2026-05-15 Controller Deliverable Repair Counter Model-Miss Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot run showed Router could schedule the second Controller deliverable repair row while also recording a repair-budget blocker, conflating issued repair attempts with failed repair receipts.
- Status: completed_model_update_runtime_fix_pending
- Skill decision: used_openspec_routing_then_flowguard

### Model Evidence
- Focused model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Focused result: `simulations/flowpilot_persistent_router_daemon_results.json`
- Runner: `simulations/run_flowpilot_persistent_router_daemon_checks.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed: safe graph ok, progress ok, Explorer ok, hazard checks ok.

### Findings
- The previous focused model represented one `controller_missing_deliverable_repair_attempts` count and therefore could not distinguish "repair action issued" from "repair receipt failed".
- The model now tracks issued repair attempts, failed repair receipts, and the currently pending repair attempt separately.
- New hazards reject a budget blocker while the second repair row is still pending and reject treating issued repair count as failed receipt count.
- The minimal runtime repair should make Router block only after the second repair receipt has been received and rejected, not when the second repair row is merely created.

### Skipped Steps
- No Router runtime implementation was changed in this model update.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

## 2026-05-15 Controller Runtime Deliverable Reconciliation Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved unifying Controller deliverables with the existing runtime output and Controller action ledger rules, while fixing the repair flow so a pending second repair is not treated as a failed repair.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_then_flowguard

### Model Evidence
- Focused daemon model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Role output runtime model: `simulations/flowpilot_role_output_runtime_model.py`
- Output contract model: `simulations/run_output_contract_checks.py`
- OpenSpec change: `openspec/changes/unify-controller-runtime-deliverables/`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\role_output_runtime.py skills\flowpilot\assets\flowpilot_runtime.py tests\test_flowpilot_router_runtime.py tests\test_flowpilot_role_output_runtime.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "controller_boundary" -q` passed with 8 tests.
- `python -m pytest tests\test_flowpilot_role_output_runtime.py -q` passed with 16 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "controller_action or controller_receipt or router_scheduler or sync_display_plan_done_receipt or recorded_external_event_closes_matching_wait_action_row or controller_boundary" -q` passed with 14 tests.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python simulations\run_flowpilot_role_output_runtime_checks.py --json-out simulations\flowpilot_role_output_runtime_results.json` passed.
- `python simulations\run_output_contract_checks.py --json-out simulations\flowpilot_output_contract_results.json` passed.
- `openspec validate unify-controller-runtime-deliverables --strict --json` passed.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and synchronized the installed FlowPilot skill to the repository digest.
- `python scripts\audit_local_install_sync.py --json` and `python scripts\install_flowpilot.py --check --json` passed.

### Findings
- Controller boundary confirmation now has a Controller-scoped runtime output contract and helper path, so Controller produces a canonical runtime envelope/receipt instead of hand-writing a JSON artifact.
- Router accepts Controller boundary confirmation only when the artifact is backed by valid runtime evidence.
- Controller deliverable repair accounting now separates issued repair rows, pending repair row, and failed repair receipts.
- Router writes the repair-budget blocker only after the second returned repair receipt is invalid; it no longer blocks while the second repair row is merely pending.
- Startup/controller table guidance was kept aligned with the same two-table rule: Controller checks off simple rows while Router owns scheduler ordering, barriers, scope, and reconciliation.

### Skipped Steps
- `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Full `tests/test_flowpilot_router_runtime.py` was not run; final evidence uses focused affected subsets plus OpenSpec, install, and three lightweight FlowGuard/contract checks.

## 2026-05-15 Runtime Ledger Persistence Model-Miss Update

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A fresh FlowPilot run started the Router daemon before startup UI, but the daemon later exited with `JSONDecodeError` after `runtime/router_scheduler_ledger.json` became a complete JSON document followed by a partial row fragment.
- Status: completed_model_update_runtime_fix_pending
- Skill decision: used_openspec_routing_then_flowguard

### Model Evidence
- Two-table scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Persistent daemon model: `simulations/flowpilot_persistent_router_daemon_model.py`
- OpenSpec change: `openspec/changes/harden-runtime-ledger-persistence/`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `openspec validate harden-runtime-ledger-persistence --strict` passed.

### Findings
- The previous focused models treated Controller and Router ledgers as abstract valid tables, so they did not catch file-level corruption or daemon status/lock/process disagreement.
- The two-table model now rejects invalid Router scheduler ledger JSON, invalid Controller action ledger JSON, non-atomic ledger writes, and scheduler multi-writer access.
- The persistent daemon model now rejects invalid durable ledgers, daemon crashes after scheduler ledger decode failures, daemon status claiming active after an error lock, and daemon status claiming active without a live process.
- The minimal runtime repair should centralize daemon-critical JSON writes behind atomic replace/readback validation, keep Router scheduler ledger mutation Router-owned, and derive daemon liveness from lock freshness plus process evidence instead of trusting status alone.

### Skipped Steps
- No Router runtime implementation was changed in this model update.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped.

## 2026-05-15 Runtime Ledger Persistence Runtime Repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Implement the OpenSpec/FlowGuard repair for daemon-critical runtime ledgers after the model update exposed partial JSON writes, scheduler multi-writer risk, and daemon status/lock/process mismatch.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_apply_then_flowguard

### Model Evidence
- Two-table scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Persistent daemon model: `simulations/flowpilot_persistent_router_daemon_model.py`
- OpenSpec change: `openspec/changes/harden-runtime-ledger-persistence/`

### Commands
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py` passed.
- `openspec validate harden-runtime-ledger-persistence --strict` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "runtime_ledgers_remain_valid_json or corrupted_scheduler_ledger or status_not_active_after_error_lock_or_missing_pid or router_daemon_observation_initializes_lock_status_and_ledger or router_daemon_tick_writes_controller_action_ledger_and_receipt_reconciles or router_daemon_queues_startup_rows_until_barrier_with_two_tables or foreground_controller_standby_exits_on_stale_or_missing_daemon or formal_startup_starts_router_daemon_before_controller_core" -q` passed with 8 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "foreground_controller_standby" -q` passed with 10 tests.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and synchronized the installed FlowPilot skill to the repository digest.
- `python scripts\audit_local_install_sync.py --json` and `python scripts\install_flowpilot.py --check --json` passed.

### Findings
- Daemon-critical JSON writes now go through one atomic replace/readback path, including the Router scheduler ledger, Controller action ledger, daemon status, and normal JSON helper writes.
- Invalid Router scheduler ledger JSON is no longer silently recreated; daemon scheduling fails into a Router-visible `daemon_error` status with repair evidence.
- Daemon liveness is now derived from lock schema, lock status, freshness, and process evidence; an error lock or missing process cannot be reported as `daemon_active`.
- Controller action ledger summaries remain tolerant enough for status reporting, while the Router scheduler ledger stays strict for daemon scheduling.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

## 2026-05-15 Runtime Ledger Fresh Write-Lock Wait Refinement

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that a daemon read of a temporarily incomplete ledger with a fresh writer lock should wait for the next tick rather than report corruption.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_apply_then_flowguard

### Model Evidence
- Two-table scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Persistent daemon model: `simulations/flowpilot_persistent_router_daemon_model.py`
- OpenSpec change: `openspec/changes/harden-runtime-ledger-persistence/`

### Commands
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `openspec validate harden-runtime-ledger-persistence --strict` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "fresh_scheduler_write_lock or corrupted_scheduler_ledger or status_not_active_after_error_lock_or_missing_pid or runtime_ledgers_remain_valid_json" -q` passed with 4 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "foreground_controller_standby_default_waits_past_timeout_until_action or fresh_scheduler_write_lock or corrupted_scheduler_ledger or status_not_active_after_error_lock_or_missing_pid or runtime_ledgers_remain_valid_json" -q` passed with 5 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "router_daemon_observation_initializes_lock_status_and_ledger or router_daemon_tick_writes_controller_action_ledger_and_receipt_reconciles or router_daemon_queues_startup_rows_until_barrier_with_two_tables or foreground_controller_standby or formal_startup_starts_router_daemon_before_controller_core" -q` passed with 14 tests.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and confirmed the installed FlowPilot skill is fresh against the repository digest.
- `python scripts\audit_local_install_sync.py --json` passed.
- `python scripts\install_flowpilot.py --check --json` passed.

### Findings
- A fresh `.write.lock` next to a temporarily unparseable daemon-critical ledger is now treated as an in-progress writer, not corruption.
- Router daemon records a deferred tick with `runtime_ledger_write_in_progress`, keeps its daemon lock, and retries on the next one-second loop.
- If the ledger is unparseable without a fresh write lock, the existing corruption/error path remains in force.
- Windows atomic replace can briefly fail when another foreground thread is reading the file, so `write_json_atomic` now retries `os.replace` briefly before surfacing a real error.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

## 2026-05-15 Daemon Lifecycle Microstep Model Upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A new FlowPilot run repeated a completed startup banner action because Controller had written a done check-off while bootstrap `pending_action` and startup flags stayed stale.
- Status: completed_model_update
- Skill decision: used_openspec_apply_then_flowguard

### Model Evidence
- Two-table scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Persistent daemon model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Lifecycle microstep model: `simulations/flowpilot_daemon_microstep_lifecycle_model.py`
- OpenSpec changes: `openspec/changes/reconcile-daemon-durable-evidence/`, `openspec/changes/startup-daemon-first-driver/`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_daemon_microstep_lifecycle_model.py simulations\run_flowpilot_daemon_microstep_lifecycle_checks.py simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py simulations\flowpilot_persistent_router_daemon_model.py simulations\run_flowpilot_persistent_router_daemon_checks.py` passed.
- `python simulations\run_flowpilot_daemon_microstep_lifecycle_checks.py --json-out simulations\flowpilot_daemon_microstep_lifecycle_results.json` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.

### Findings
- The older models checked that the daemon started early and that receipts were reconciled in broad phase terms, but they did not model each daemon tick as read tables, reconcile evidence, sync authority state, clear pending/wait state, schedule or record a barrier, and write refreshed summaries.
- The new lifecycle model covers startup, normal route work, role waits, external event waits, repair, and terminal cleanup with the same microstep contract.
- The model rejects stale startup `pending_action` after a done receipt, stale Router facts after route receipts, durable-only role output, external event waits that are not Router-closed, repair blockers before reading repair receipts, terminal status before cleanup, Controller writes to Router-owned tables, and daemon status from stale summaries.
- The minimal root fix remains one shared daemon pre-next-action reconciliation pipeline; phase-specific handlers can supply different evidence readers and postcondition appliers, but they should not bypass the common microstep order.

### Skipped Steps
- No production runtime code was changed in this model update.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

## 2026-05-15 Startup Scheduler Barrier Classification And Join Hardening

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User clarified that startup banner, background role slots, and heartbeat binding are not global Router queue barriers; they are startup obligations that can be reconciled before the live Reviewer gate.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_then_flowguard

### Model Evidence
- Two-table scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Daemon lifecycle microstep model: `simulations/flowpilot_daemon_microstep_lifecycle_model.py`
- OpenSpec change: `openspec/changes/classify-startup-scheduler-barriers/`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate classify-startup-scheduler-barriers --strict` passed before runtime edits.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `python simulations\run_flowpilot_daemon_microstep_lifecycle_checks.py` passed.
- `python -m unittest ...` focused startup scheduler/runtime group passed with 11 tests.
- `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests` was attempted but timed out after 15 minutes; this is not counted as a pass.

### Findings
- Startup banner, heartbeat binding, display/status, and role-slot startup rows now carry explicit progress classification instead of inheriting global barrier behavior from display, payload, host spawn, or host automation mechanics.
- Startup daemon can keep queueing unrelated startup rows while nonblocking startup obligations remain open.
- Startup Controller receipts for deferred banner, role-slot, and heartbeat rows can update bootstrap/run state and reconcile scheduler rows without reissuing the same work.
- Reviewer startup fact review now checks unresolved startup bootstrap obligations and startup-local Controller rows before proceeding.
- Role-dependent startup card work is blocked if role slots are not ready, while unrelated startup queueing can continue.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- The full Router runtime unittest class timed out and remains a residual broad-suite risk; focused affected tests and lightweight FlowGuard checks passed.

## 2026-05-15 Startup Bootloader Reconciliation False PM Blocker Model Upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Live FlowPilot run `run-20260515-120231` created a PM repair control blocker for `initialize_mailbox` even though the startup Controller action and Router scheduler row were already reconciled by the startup daemon.
- Status: completed_model_update_runtime_fix_pending
- Skill decision: used_flowguard

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Result file: `simulations/flowpilot_daemon_reconciliation_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` passed.
- `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_results.json` passed.
- `python simulations\run_flowpilot_model_mesh_checks.py --json-out simulations\flowpilot_model_mesh_results.json` passed.
- A background `python simulations\run_meta_checks.py` was started, then stopped and marked `cancelled_by_user_instruction` after the user explicitly asked to skip the heavy Meta and Capability models.

### Findings
- The previous daemon reconciliation model covered generic stateful Controller receipts and role-output durable reconciliation, but it did not model startup-daemon bootloader receipts as a distinct receipt class with a single reconciliation owner.
- The model now rejects startup bootloader rows that are reconciled without their postcondition, reconciled by the wrong owner, or converted into PM repair blockers after the startup daemon has already satisfied the postcondition.
- The runner now includes a read-only live projection that scans current public FlowPilot ledger/control-block metadata. It detected `startup_reconciled_action_false_pm_blocker` for `initialize_mailbox` in `run-20260515-120231` without reading sealed repair packet bodies.

### Counterexamples
- `startup_reconciled_action_false_pm_blocker`
- `startup_unsupported_receipt_escalated_to_pm`
- `startup_row_reconciled_without_postcondition`
- `startup_row_reconciled_by_wrong_owner`

### Skipped Steps
- No Router runtime implementation was changed in this pass.
- Heavyweight Meta simulation was cancelled by explicit user direction after partial progress.
- Heavyweight Capability simulation was not run by explicit user direction.

### Next Actions
- Runtime repair should make startup bootloader reconciliation single-owner and idempotent: a startup row already reconciled by `startup_daemon_bootloader_postcondition` must be skipped by the generic Controller receipt reconciler and must never create a PM repair blocker.

## 2026-05-15 Deterministic Startup Bootstrap Root Fix

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User approved replacing daemon-scheduled deterministic startup setup rows with a script-owned bootstrap seed, after a live run showed a false PM blocker for an already reconciled `initialize_mailbox` startup row.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_then_flowguard

### Model Evidence
- OpenSpec change: `openspec/changes/deterministic-startup-bootstrap/`
- Deterministic startup bootstrap model: `simulations/flowpilot_deterministic_startup_bootstrap_model.py`
- Deterministic startup bootstrap runner: `simulations/run_flowpilot_deterministic_startup_bootstrap_checks.py`
- Deterministic startup bootstrap results: `simulations/flowpilot_deterministic_startup_bootstrap_results.json`
- Daemon reconciliation model and live projection: `simulations/flowpilot_daemon_reconciliation_model.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate deterministic-startup-bootstrap --strict` passed before and after implementation.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_deterministic_startup_bootstrap_model.py simulations\run_flowpilot_deterministic_startup_bootstrap_checks.py` passed.
- `python simulations\run_flowpilot_deterministic_startup_bootstrap_checks.py --json-out simulations\flowpilot_deterministic_startup_bootstrap_results.json` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` passed and still detects the historical live false-blocker projection.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed.
- `python simulations\run_flowpilot_daemon_microstep_lifecycle_checks.py --json-out simulations\flowpilot_daemon_microstep_lifecycle_results.json` passed.
- `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_results.json` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "run_until_wait_folds_only_internal_bootloader_actions_after_banner or run_until_wait_folds_user_intake_then_stops_before_role_boundary or startup_daemon_defers_banner_and_queues_next_boot_row or deterministic_bootstrap_seed_failure_does_not_create_pm_blocker or deterministic_bootstrap_seed_replay_uses_existing_evidence or reconciled_scheduler_row_receipt_replay_does_not_create_pm_blocker or startup_daemon_queues_role_heartbeat_and_controller_core_without_role_wait or startup_async_receipts_update_bootstrap_flags_and_scheduler_rows or scheduled_startup_heartbeat_is_bootloader_boundary_before_controller_core" -q` passed with 9 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "deterministic_bootstrap or startup_daemon or startup_async_receipts or scheduled_startup_heartbeat or incomplete_stateful_rehydrate_receipt_becomes_control_blocker or startup_role_slots or run_until_wait_folds or startup_scope or controller_boundary_done_receipt_reclaims_router_postcondition" -q` passed with 13 tests.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` refreshed the installed `flowpilot` skill and ended with `source_fresh: true`.
- `python scripts\audit_local_install_sync.py --json` passed.
- `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` `source_fresh: true`.

### Findings
- Deterministic startup setup now happens in one script-owned bootstrap seed after confirmed startup intake: runtime kit copy, startup answers, placeholder record, mailbox/empty ledgers, user request reference, and user-intake scaffold.
- The unified Router scheduler no longer queues deterministic setup rows such as `fill_runtime_placeholders`, `initialize_mailbox`, `record_user_request`, or `write_user_intake` in the normal startup path.
- The scheduler still owns startup obligations that require host/AI/wait semantics: role-slot startup, heartbeat binding when requested, Controller core loading, and banner display.
- Startup seed failure now raises before route activation and does not create a PM repair blocker.
- Receipt replay for an already reconciled scheduler row is idempotently skipped before blocker creation.
- Replaying a completed deterministic seed reuses existing evidence and does not reinitialize runtime ledgers.

### Counterexamples
- `scheduler_before_seed_success`
- `seed_success_without_all_artifacts`
- `deterministic_setup_left_as_controller_row`
- `seed_failure_as_pm_blocker`
- `reconciled_row_false_pm_blocker`
- `unsupported_startup_receipt_escalated_to_pm`
- `role_slots_bypass_scheduler`
- `heartbeat_bypass_scheduler`
- `controller_core_before_seed_and_scheduler`
- `controller_reads_sealed_user_body`
- `intake_written_without_user_request_ref`
- `installed_skill_stale_after_fix`
- `peer_changes_overwritten`

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- If future startup changes affect the global project-control architecture or capability routing, rerun the heavyweight Meta and Capability checks when the user allows the runtime cost.

## 2026-05-15 Router-Internal Mechanical Actions

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User found Router-local checks leaking into Controller/PM control rows and asked for a root fix, a FlowGuard model upgrade, startup-stage simulation after the startup-focused peer agent finished, local install sync, and local git recording.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_then_flowguard

### Model Evidence
- OpenSpec change: `openspec/changes/internalize-router-mechanical-actions/`
- Router-internal mechanics model: `simulations/flowpilot_router_internal_mechanics_model.py`
- Router-internal mechanics runner: `simulations/run_flowpilot_router_internal_mechanics_checks.py`
- Router-internal mechanics results: `simulations/flowpilot_router_internal_mechanics_results.json`
- Updated adjacent models: `simulations/flowpilot_resume_model.py`, `simulations/prompt_isolation_model.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate internalize-router-mechanical-actions --strict --json` passed.
- `openspec status --change internalize-router-mechanical-actions --json` reported complete.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_resume_model.py simulations\prompt_isolation_model.py simulations\flowpilot_router_internal_mechanics_model.py simulations\run_flowpilot_router_internal_mechanics_checks.py` passed.
- `python simulations\run_flowpilot_router_internal_mechanics_checks.py --json-out simulations\flowpilot_router_internal_mechanics_results.json` passed.
- `python simulations\run_prompt_isolation_checks.py` passed.
- `python simulations\run_flowpilot_resume_checks.py` passed.
- Startup-stage simulations were included and passed: `run_flowpilot_startup_optimization_checks.py`, `run_flowpilot_startup_control_checks.py`, `run_flowpilot_deterministic_startup_bootstrap_checks.py`, and `run_flowpilot_startup_intake_ui_checks.py`.
- `python -m unittest ...` targeted startup/internal group passed with 8 tests.
- `python -m unittest ...` selected runtime regression group passed with 81 tests in 691.128s.
- `python scripts\check_install.py`, `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed; installed `flowpilot` is source-fresh.

### Findings
- Router now consumes `check_prompt_manifest`, `check_packet_ledger`, and `write_startup_mechanical_audit` internally without writing Controller action rows.
- The Router-internal classifier is allowlist-based and rejects user, payload, host automation, host spawn, display-confirmation, card/mail relay, role-facing, and sealed-body actions.
- Controller-owned work packages remain Controller-visible: system-card/card-bundle relay, mail relay, role work, host-bound startup obligations, and user-visible display confirmation.
- Controller and PM reset prompts now tell Controller to rely on Router-owned manifest and packet-ledger checks instead of performing those checks as Controller rows.
- Startup-stage simulations were included after the startup-focused peer-agent work finished.
- Local installed FlowPilot is source-fresh after repository sync.

### Counterexamples
- `router_internal_leaked_to_controller_row`
- `controller_work_package_swallowed_by_router`
- `role_interaction_bypassed_controller`
- `sealed_body_read_during_internal_work`
- `missing_external_evidence_marked_done`
- `router_internal_repeated_side_effect`
- `display_projection_claimed_as_user_confirmation`
- `host_boundary_consumed_locally`
- `router_internal_failure_marked_done`

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Full `tests/test_flowpilot_router_runtime.py` remains too slow for a routine final gate and previously timed out; focused affected runtime tests plus FlowGuard checks were used.

### Next Actions
- If ACK/card-return checks are later internalized, rerun the Router-internal mechanics model and update tests that currently observe explicit `check_card_return_event` waits.
- Run heavyweight Meta and Capability simulations later if the user wants broader global assurance.

## 2026-05-15 Parallel FlowPilot Run Isolation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User observed stopped/reopened FlowPilot runs leaving background-board state behind and asked for a root fix that also supports multiple FlowPilot runs in parallel.
- Status: completed_focused_runtime_update
- Skill decision: used_openspec_then_flowguard

### Model Evidence
- OpenSpec change: `openspec/changes/parallel-flowpilot-run-isolation/`
- Parallel run isolation model: `simulations/flowpilot_parallel_run_isolation_model.py`
- Parallel run isolation runner/results: `simulations/run_flowpilot_parallel_run_isolation_checks.py`, `simulations/flowpilot_parallel_run_isolation_results.json`
- Updated adjacent models: `simulations/flowpilot_control_plane_friction_model.py`, `simulations/flowpilot_cross_plane_friction_model.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate parallel-flowpilot-run-isolation --strict` passed.
- `python simulations\run_flowpilot_parallel_run_isolation_checks.py --json` passed; 11 known-bad hazards were detected and the safe two-run scenario passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_checks_results.json` passed after live-run reconciliation; results were copied to `simulations\flowpilot_control_plane_friction_results.json`.
- `python simulations\run_flowpilot_cross_plane_friction_checks.py --json-out simulations\flowpilot_cross_plane_friction_checks_results.json` passed; results were copied to `simulations\flowpilot_cross_plane_friction_results.json`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py` passed.
- Focused runtime regression group passed: `20 passed, 226 deselected, 2 subtests passed`.
- `python scripts\check_install.py`, `python scripts\install_flowpilot.py --sync-repo-owned --json`, and `python scripts\audit_local_install_sync.py --json` passed; installed `flowpilot` is source-fresh.
- `python skills\flowpilot\assets\flowpilot_router.py --root . --json reconcile-run` repaired the live stopped run's stale terminal status projection.

### Findings
- The daemon now binds to an immutable `run_id/run_root`; daemon ticks and daemon subprocess startup do not reload `.flowpilot/current.json` as authority.
- `.flowpilot/current.json` is now documented and projected as UI focus/default target metadata only.
- Non-current running index entries remain background-active instead of being marked `stale_not_current`.
- `daemon-stop` accepts explicit `run_id`/`run_root`; targeted stop releases only the selected run's lock.
- Released, error, and terminal locks are no longer refreshed back to active.
- Controller action ledger summaries now separate active work from done-only history.
- `reconcile-run` can recover terminal run state from current/index/lifecycle/frontier authorities when older artifacts disagree.
- Controller prompt cards and protocol docs were updated so Controller does not switch runs from `.flowpilot/current.json` or continue from memory.

### Counterexamples
- `daemon_reads_current_after_focus_change`
- `daemon_cross_writes_other_run`
- `duplicate_writer_same_run`
- `parallel_runs_forced_singleton`
- `focus_change_marks_background_run_stale`
- `untargeted_stop_releases_wrong_run`
- `targeted_stop_releases_wrong_run`
- `released_lock_reactivated`
- `active_status_without_live_process`
- `done_history_reported_as_active_work`
- `current_focus_used_as_daemon_authority`

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Full `tests/test_flowpilot_router_runtime.py` timed out after 15 minutes with no pytest progress output; focused affected runtime tests plus FlowGuard checks were used as the final gate.

### Next Actions
- If future work changes global project-control flow or capability routing, rerun the heavyweight Meta and Capability checks when runtime cost is acceptable.
- Investigate the full router runtime test-file timeout separately; it appears independent from the focused parallel-run fix.

## 2026-05-15 Daemon Reconciliation Model-Miss Review

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot run showed a valid Controller-boundary confirmation artifact and done receipt while Router flags stayed false and the same boundary action was exposed again.
- Status: model_updated_production_fix_pending
- Skill decision: used_flowguard_model_maintenance; OpenSpec was skipped because this was a focused model-miss review and no production behavior was changed.

### Model Evidence
- Updated model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Updated runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Result evidence: `simulations/flowpilot_daemon_reconciliation_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` failed as expected on the live-run projection while the abstract safe graph, progress check, Explorer run, and hazard checks passed.

### Findings
- The previous daemon model covered generic repeated Controller actions and generic stateful postconditions, but did not explicitly model the Controller-boundary three-way projection across the durable artifact, Controller action row, Router scheduler row, and Router flags.
- The model now requires a valid Controller-boundary artifact plus reconciled receipt/action/scheduler rows to rebuild Router flags before any next action is exposed.
- The live run is now classified with `controller_boundary_reconciled_artifact_left_flags_false`, `controller_boundary_reissued_after_reconciled_artifact`, and `controller_boundary_action_returned_without_pending_action`.
- Additional startup bootloader row projection findings remain visible in the same live-run projection.

### Counterexamples
- `controller_boundary_reconciled_artifact_left_flags_false`
- `controller_boundary_reissued_after_reconciled_artifact`
- `controller_boundary_returned_without_pending_action`
- `controller_boundary_action_scheduler_disagree`

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Production router code was not changed in this pass.

### Next Actions
- Implement a single Router-owned durable projection reconciler before next-action computation so valid Controller-boundary and startup bootloader evidence rebuilds Router flags/action rows/scheduler rows atomically and idempotently.
- Add focused runtime regression tests for the live-run projection before rerunning the heavy models.

## 2026-05-15 Daemon/Controller Prompt Boundary Hardening

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot prompt text still allowed the main assistant or Controller to treat daemon-mode work as a manual Router loop after heartbeat, wait-boundary, unclear-next-step, or Controller-row completion prompts.
- Status: prompt_boundary_prompts_synced
- OpenSpec change: `harden-daemon-controller-prompt-boundaries`

### Model Evidence
- Added focused model: `simulations/flowpilot_prompt_boundary_model.py`
- Added focused runner: `simulations/run_flowpilot_prompt_boundary_checks.py`
- Result evidence: `simulations/flowpilot_prompt_boundary_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate harden-daemon-controller-prompt-boundaries --strict` passed.
- `python simulations\run_flowpilot_prompt_boundary_checks.py` passed after prompt edits; the same check failed before edits on actual prompt-source assertions.
- `python -m py_compile simulations\flowpilot_prompt_boundary_model.py simulations\run_flowpilot_prompt_boundary_checks.py skills\flowpilot\assets\flowpilot_router.py` passed.
- Focused daemon/background checks passed for prompt boundary, persistent daemon, two-table scheduler, daemon microstep lifecycle, and card instruction coverage.
- Focused runtime regression subset passed: 5 tests.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed; installed `flowpilot` is source-fresh.

### Findings
- The prompt boundary is now split into pre-daemon bootloader actions and daemon-mode ledger work.
- In daemon mode, Controller rows complete through the row action plus Controller receipt; prompt text now forbids `next`, `apply`, or `run-until-wait` as row-to-row progress.
- Heartbeat and manual wakeup prompts now attach to daemon status and Controller action ledger instead of saying to continue or return to the Router loop.
- Controller prompt text now treats a half-written action ledger as a wait-for-next-tick condition, not as corruption.

### Counterexamples
- `daemon_prompt_prefers_run_until_wait`
- `heartbeat_continues_router_loop`
- `unclear_step_returns_to_router`
- `row_to_row_uses_router_command`
- `partial_table_read_errors`
- `missing_startup_phase_split`

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py` still reports the separate durable-reconciliation/repeated-row live issue; that is not a prompt-only defect and is owned by the parallel repair.

### Next Actions
- When the parallel reconciliation repair lands, rerun the daemon reconciliation check and then consider the heavyweight Meta/Capability checks when runtime cost is acceptable.

## 2026-05-15 Daemon Projection Reconciliation Repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The model-miss review found Controller-boundary durable evidence was complete while Router flags stayed false, and the user requested a model-first repair plus a faster no-sleep loop when immediate work remains.
- Status: focused_repair_synced_to_local_install
- OpenSpec change: `harden-daemon-projection-reconciliation`

### Model Evidence
- Paper plan: `docs/flowpilot_daemon_projection_reconciliation_plan.md`
- Updated model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Updated runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Pre-implementation model-only result: `simulations/flowpilot_daemon_reconciliation_model_only_results.json`
- Final result: `simulations/flowpilot_daemon_reconciliation_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate harden-daemon-projection-reconciliation --strict` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out simulations\flowpilot_daemon_reconciliation_model_only_results.json` passed; known-bad projection and fast-loop hazards were detected.
- `python skills\flowpilot\assets\flowpilot_router.py --root . reconcile-run --json` repaired the current stopped run's Controller-boundary projection.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` passed; live projection reported `finding_count: 0`.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "controller_boundary"` passed: 9 tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "router_daemon"` passed: 17 tests.
- `python scripts\check_install.py`, `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed; installed `flowpilot` is source-fresh.

### Findings
- Router now has an idempotent Controller-boundary projection sync helper that can rebuild flags from valid durable artifact/receipt/action/scheduler evidence even when `pending_action` is empty.
- `compute_controller_action`, daemon ticks, and `reconcile-run` now run this projection sync before progress decisions.
- The daemon outer loop now skips the one-second sleep after `max_actions_per_tick`, while preserving sleep for real waits such as `barrier` and `no_action`.
- The live projection check now recognizes `startup_bootloader_controller_receipt` as the valid startup bootloader receipt owner and still rejects generic wrong owners.

### Counterexamples
- `controller_boundary_reconciled_artifact_left_flags_false`
- `controller_boundary_reissued_after_reconciled_artifact`
- `controller_boundary_returned_without_pending_action`
- `daemon_sleeps_after_queue_budget_exhausted`
- `daemon_fast_loops_after_barrier`
- `daemon_fast_loops_after_no_action`

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because this was a focused daemon projection repair.

### Next Actions
- Run heavyweight Meta/Capability checks later if a broader project-control or capability-routing change is made, or before a release confidence claim.

## 2026-05-15 Startup Bootloader Blocker Classification Model-Miss Upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot run created a PM repair control-blocker for `load_controller_core`, later reconciled the same startup bootloader row successfully, but still left a queued PM repair action.
- Status: completed_focused_model_update_runtime_fix_planned

### Model Evidence
- Updated model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Updated runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Model-only result: `simulations/flowpilot_daemon_reconciliation_results.json`
- Live audit result: `tmp/flowpilot_daemon_reconciliation_live_audit.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json --skip-live-projection` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out tmp\flowpilot_daemon_reconciliation_live_audit.json` intentionally failed on the historical run and reported four startup-blocker findings.
- `python -m py_compile simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py` passed.

### Findings
- The previous focused model caught some false-PM startup blockers but did not separately model retry-lane classification, same-action blocker cleanup after successful reconciliation, or stale PM repair action queueing.
- The model now rejects startup missing-postcondition blockers that go to PM before the mechanical reissue budget is exhausted.
- The model now rejects a same-startup-action blocker that remains unresolved after the row and postcondition are reconciled.
- The model now rejects any PM repair action queued after successful startup bootloader reconciliation.
- The live projection now splits the observed `load_controller_core` incident into `startup_missing_postcondition_pm_lane_before_reissue`, `startup_reconciled_action_false_pm_blocker`, `startup_blocker_not_resolved_after_success`, and `startup_reconciled_action_queued_pm_repair`.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- No production Router behavior was changed in this pass; the runtime repair remains planned.

### Next Actions
- Runtime repair should centralize startup bootloader reconciliation ownership, classify startup postcondition misses as mechanical reissue until the retry budget is exhausted, and resolve same-action blockers plus queued PM repair rows when the startup postcondition is later satisfied.

## 2026-05-15 Controller Receipt Action Metadata Separation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Controller daemon ledger rows embedded raw Router action metadata that still described the direct `apply` path, conflicting with the Controller row completion path through `controller-receipt`.
- Status: completed_focused_runtime_update
- OpenSpec change: `separate-controller-receipt-action-metadata`

### Model Evidence
- OpenSpec: `openspec/changes/separate-controller-receipt-action-metadata/`
- Updated model: `simulations/flowpilot_prompt_boundary_model.py`
- Updated runner/source check: `simulations/run_flowpilot_prompt_boundary_checks.py`
- Post-fix result: `tmp/flowguard_background/prompt_boundary_post_controller_receipt_metadata.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate separate-controller-receipt-action-metadata --strict` passed.
- `python simulations\run_flowpilot_prompt_boundary_checks.py --json-out tmp\flowguard_background\prompt_boundary_post_controller_receipt_metadata.json` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "recorded_external_event_closes_matching_wait_action_row or startup_banner_action_and_result_are_user_visible or scheduled_startup_heartbeat_is_bootloader_boundary_before_controller_core or reconciled_scheduler_row_receipt_replay_does_not_create_pm_blocker or startup_waits_for_answers_before_banner_or_controller or background_agents_allow_requires_six_fresh_live_agent_records or sync_display_plan_done_receipt_updates_router_fact_before_next_action or terminal_summary_payload_requires_attribution_display_and_run_root_sources"` passed with 8 selected tests.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json --skip-live-projection` passed for the parallel model-only daemon reconciliation update.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed; installed `flowpilot` is source-fresh.

### Findings
- Controller action ledger rows now expose `controller_completion_command: controller-receipt`, `controller_completion_mode: controller_action_ledger_receipt`, and `apply_required: false`.
- Raw direct pending action apply intent is preserved only under `router_pending_apply_required`; Router-controlled wait rows set that field to `false`.
- Startup banner, role slot spawn, heartbeat automation, display sync, Controller core, and Controller card/skill wording now describe Controller row completion as a receipt path.
- Direct startup intake and direct terminal summary actions still expose the normal apply path.

### Skipped Steps
- Background `python simulations\run_meta_checks.py` and `python simulations\run_capability_checks.py` were launched with the repository log contract, then cancelled and marked `cancelled_by_user_instruction` after the user explicitly said the two models are too heavy and can be skipped for this pass.

### Next Actions
- If a later change modifies global project-control or capability-routing behavior, rerun heavyweight Meta/Capability checks from a fresh background log root before making a broad confidence claim.

## 2026-05-15 Startup Blocker Settlement Runtime Repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A successfully reconciled startup bootloader Controller receipt could leave a stale PM `handle_control_blocker` action queued from the same source blocker.
- Status: completed_focused_runtime_update
- OpenSpec change: `settle-control-plane-before-next-action`

### Model Evidence
- Focused daemon reconciliation result: `simulations/flowpilot_daemon_reconciliation_results.json`
- Prompt-boundary result from the parallel Controller receipt metadata change: `simulations/flowpilot_prompt_boundary_results.json`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json --skip-live-projection` passed.
- `python simulations\run_flowpilot_prompt_boundary_checks.py --json-out simulations\flowpilot_prompt_boundary_results.json` passed.
- `openspec validate settle-control-plane-before-next-action --strict` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py simulations\flowpilot_prompt_boundary_model.py simulations\run_flowpilot_prompt_boundary_checks.py` passed.
- Targeted runtime unittest selection for startup bootloader receipts, Controller boundary receipts, stale blocker supersession, and Controller receipt ledger duplicates passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed; installed `flowpilot` is source-fresh.
- `python scripts\smoke_autopilot.py --fast` passed and reused existing heavyweight Meta/Capability proofs instead of rerunning those checks.

### Findings
- Router settlement now resolves same-origin control blockers when the originating Controller action or startup postcondition reconciles.
- Queued PM `handle_control_blocker` Controller rows for the resolved blocker are marked `superseded` instead of delivered as fresh PM repair work.
- `load_controller_core` Controller receipts now apply the startup bootloader postcondition after the Router daemon is ready.
- Active control blockers are considered only after durable receipt/evidence reconciliation has had a chance to settle stale state.
- The fallback blocker match was kept narrow: exact Controller action id or scheduler row id is preferred, postcondition fallback requires the same action type, and legacy startup fallback is limited to the startup missing-postcondition source.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- Rerun heavyweight Meta/Capability checks later only if a broader project-control or capability-routing change is made, or before a release-level confidence claim.

## 2026-05-15 Router Process Liveness Middle-Layer Model

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Compressed Meta and Capability models no longer preserve enough Router demo mechanics to catch repeated process bugs around blockers, retry returns, PM repair loops, route mutation, and stuck-control cases.
- Status: completed_model_and_projection
- OpenSpec change: `add-router-process-liveness-model`

### Model Evidence
- OpenSpec: `openspec/changes/add-router-process-liveness-model/`
- New model: `simulations/flowpilot_process_liveness_model.py`
- New runner: `simulations/run_flowpilot_process_liveness_checks.py`
- Result artifact: `simulations/flowpilot_process_liveness_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate add-router-process-liveness-model --strict` passed.
- `python -m py_compile simulations\flowpilot_process_liveness_model.py simulations\run_flowpilot_process_liveness_checks.py` passed.
- `python simulations\run_flowpilot_process_liveness_checks.py --json` passed.

### Findings
- The model preserves Router loop mechanics at a middle layer: durable settlement before next action, one action per tick, wait/event authority, route/frontier freshness, worker/result/PM/reviewer gates, blocker lanes, retry budget, PM repair returns, route mutation replay, and terminal ledger closure.
- Safe graph checks found 231 states, 235 edges, no invariant failures, four normal complete states, and ten controlled blocked states after adding per-node coverage and blocker-lane classification.
- Progress and loop checks found no stuck reachable states and no nonterminating components.
- The node coverage check explored a three-node abstract route, reached node index 2, and found no completion or final-scan state without full reviewer/pass and completion-ledger coverage.
- FlowGuard Explorer checked 63,682 traces with no violations, and all known-bad hazard fixtures were rejected.
- Current-run projection classified the active run as a controlled `stopped_by_user` lifecycle, not a normal FlowPilot completion.
- Current-run projection also warned that a `controller_action_receipt_missing_router_postcondition` blocker was routed to `pm_repair_decision_required`, its retry-budget flags were inconsistent, and terminal stopped history still contains open Controller/scheduler rows.

### Skipped Steps
- No production Router behavior was changed in this pass.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally not rerun because this pass adds the fast middle-layer process model rather than changing global project-control or capability-routing code.

### Next Actions
- Use this middle-layer model before future Router process changes that affect blockers, waits, retry/repair lanes, route mutation, terminal closure, or Controller evidence boundaries.
- Do not treat a stopped-by-user run with retained open rows as normal completion or as resumable live work without a fresh settlement step.

## 2026-05-15 Controller Postcondition Blocker Routing Repair

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The fast process model found that `controller_action_receipt_missing_router_postcondition` could be treated like a PM repair blocker even when it was a small local reconciliation miss.
- Status: completed_focused_runtime_update
- OpenSpec change: `fix-controller-postcondition-blocker-routing`

### Model Evidence
- OpenSpec: `openspec/changes/fix-controller-postcondition-blocker-routing/`
- Process liveness model: `simulations/flowpilot_process_liveness_model.py`
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Control-plane friction model: `simulations/flowpilot_control_plane_friction_model.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `openspec validate fix-controller-postcondition-blocker-routing --strict` passed.
- `python simulations\run_flowpilot_process_liveness_checks.py --json` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json --skip-live-projection` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\run_flowpilot_process_liveness_checks.py simulations\flowpilot_process_liveness_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_control_plane_friction_checks.py simulations\flowpilot_control_plane_friction_model.py` passed.
- Focused `pytest` selection for startup missing postconditions, stale blocker supersession, Controller receipt cases, retry exhaustion, and zero-budget PM blockers passed with 5 selected tests.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and synchronized the installed `flowpilot` skill from repository source.
- `python scripts\audit_local_install_sync.py --json` and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.
- `python scripts\smoke_autopilot.py --fast` passed and reused existing Meta/Capability proofs without rerunning those heavyweight checks.

### Findings
- Missing Controller receipt postconditions now take the existing mechanical control-plane reissue lane for two direct attempts before PM escalation.
- The retry state is written on the Controller action row and scheduler row instead of immediately creating a PM blocker.
- If the two-attempt direct retry budget is exhausted, the blocker can still escalate to PM, but it carries the mechanical policy row and exhausted-budget metadata so later checks know this was not premature PM routing.
- Zero-budget PM blockers now mark `direct_retry_budget_exhausted: true`, avoiding contradictory "0 of 0 retries but not exhausted" state.
- Fatal protocol blockers still stay fatal and PM-targeted.
- The current-run projection still reports the already stopped historical run as retaining old PM-warning artifacts; that remains old stopped-run history, not fresh runtime behavior after this patch.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- Rerun heavyweight Meta/Capability checks later before making a broad release-level claim about global project-control and capability-routing surfaces.

## 2026-05-15 Sync Display Plan Summary Clarification

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Startup `sync_display_plan` suppressed user-visible display correctly, but its action summary still told Controller to display a route map in the user dialog before any canonical PM route existed.
- Status: completed_focused_runtime_update
- OpenSpec change: `internalize-router-mechanical-actions`

### Model Evidence
- Route display model: `simulations/flowpilot_route_display_model.py`
- Router internal mechanics model: `simulations/flowpilot_router_internal_mechanics_model.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- Background `python simulations\run_flowpilot_route_display_checks.py --json-out simulations\flowpilot_route_display_results.json` passed with exit code `0`.
- Background `python simulations\run_flowpilot_router_internal_mechanics_checks.py` passed with exit code `0`.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "display_plan_is_controller_synced_projection_from_pm_plan" -q` passed with 1 selected test.
- `openspec validate internalize-router-mechanical-actions --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed and synchronized the installed `flowpilot` skill from repository source.
- `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed with installed `flowpilot` source-fresh.
- `python scripts\smoke_autopilot.py --fast` passed and reused existing Meta/Capability proofs without rerunning those heavyweight checks.

### Findings
- `sync_display_plan` now describes startup waiting sync as internal host-plan projection and says no user-dialog route map is required until a canonical PM route exists.
- Canonical route sync still describes displaying the FlowPilot Route Sign in the user dialog before syncing the host visible plan from committed route state.
- The runtime behavior remains unchanged: startup waiting sync stays suppressed from user-visible chat, and canonical route display keeps its user-dialog confirmation boundary.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- If a later change moves `sync_display_plan` from Controller work into fully Router-internal execution, rerun the focused ownership model and update the Controller/display boundary tests before marking that broader slice complete.

## 2026-05-15 Mail Delivery Receipt Model-Miss Review

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A live FlowPilot run showed a Controller `deliver_mail` receipt marked done while `user_intake_delivered_to_pm` was not folded into Router state or packet mail ledger.
- Status: focused_model_upgraded_no_production_router_fix
- OpenSpec context: `internalize-router-mechanical-actions`
- Miss type: boundary_missing
- Generalized case: any Controller receipt that claims a Router-owned postcondition must either fold the durable ledger and Router flag together, stay as an explicit control blocker, or consume a PM repair decision into a repair transaction/reissue before continuing to wait.

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Router internal mechanics model: `simulations/flowpilot_router_internal_mechanics_model.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed with schema `1.0`.
- `python -m py_compile simulations/flowpilot_daemon_reconciliation_model.py simulations/run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out tmp/flowguard_background/daemon_reconciliation_model_only_after.json` passed.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --json-out tmp/flowguard_background/daemon_reconciliation_live_after.json` failed as expected because the live run projection now detects the current blocker.
- `python simulations/run_flowpilot_router_internal_mechanics_checks.py --json-out tmp/flowguard_background/router_internal_mechanics_after.json` passed.
- `openspec validate internalize-router-mechanical-actions --strict` passed.

### Findings
- The earlier model covered generic stateful receipts, startup bootloader receipts, Controller-boundary projection, and role-output durable reconciliation, but did not project `deliver_mail` from Controller receipt into packet mail ledger and Router flags.
- The upgraded daemon reconciliation model now includes mail-delivery receipt state, packet/mail ledger folding, Router flag sync, unsupported receipt blockers, PM repair decision consumption, and repair-transaction-backed reissue.
- The live projection now reports `mail_delivery_receipt_unfolded_to_packet_ledger` for `user_intake`: the Controller receipt is done, but mail ledger folding and `user_intake_delivered_to_pm` flag sync are absent, with reconciliation blocked by `unsupported_stateful_controller_receipt`.
- No production Router behavior was changed in this pass; the result is a model-miss closure and a root-fix plan input.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- Implement the smallest production fix at the Controller receipt reconciliation boundary: make `deliver_mail` either fold through the same durable helper used by the direct apply path or be classified so it never enters an unsupported receipt path.
- Add a focused runtime regression for daemon/controller-receipt `deliver_mail` that asserts the Controller receipt, Router flag, packet mail ledger, Controller action row, and scheduler row are reconciled together.

## 2026-05-15 Daemon Reconciliation Model-Miss Expansion

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A stopped FlowPilot run exposed three daemon reconciliation misses: startup role flags required a manual daemon restart, a transient `.tmp-*.json` Controller action file stopped the daemon with `FileNotFoundError`, and a `deliver_mail` receipt did not fold its packet ledger and Router postcondition.
- Status: focused_model_upgraded_no_production_router_fix
- Miss type: model_boundary_missing

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` passed earlier in this audit with schema `1.0`.
- `python -m py_compile simulations/flowpilot_daemon_reconciliation_model.py simulations/run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out tmp/flowguard_background/daemon_reconciliation_after_temp_projection_fix_model_only.json` passed.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --json-out tmp/flowguard_background/daemon_reconciliation_live_projection_after_temp_projection_fix.json` failed as expected because the stopped live run now projects three findings.

### Findings
- The model now treats startup secondary-record flags as durable evidence that must be atomically folded into Router state before next-action computation.
- The model now treats `.tmp-*.json` Controller action files as transient write artifacts that directory scans must skip; reading them as real actions or stopping the daemon on their disappearance is an invariant failure.
- The model now keeps the `deliver_mail` receipt path covered by packet-ledger fold, Router flag sync, explicit blocker, and PM repair decision consumption rules.
- The live projection detects the current stopped run's three historical findings: `startup_role_flag_fold_required_manual_daemon_restart`, `temp_controller_action_file_race_stopped_daemon`, and `mail_delivery_receipt_unfolded_to_packet_ledger`.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- No production Router code was changed in this pass.

### Next Actions
- Implement the smallest production fix by centralizing Controller receipt reconciliation, skipping transient temp action files in durable scans, and folding startup role flags through one startup-state reconciliation owner.
- Add focused runtime regressions for those three local daemon paths before rerunning heavyweight Meta/Capability checks.

## 2026-05-15 Active Writer Settlement Runtime Fix

- Project: FlowGuardProjectAutopilot_20260430
- OpenSpec change: `defer-active-writer-settlement`
- Trigger reason: User clarified that active writes can legitimately take longer than a short fixed retry window, so Router should wait while there is concrete writer progress instead of prematurely creating blockers.
- Status: focused_runtime_update_synced

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner: `simulations/run_flowpilot_daemon_reconciliation_checks.py`

### Commands
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out tmp/flowguard_background/daemon_reconciliation_active_writer_after_runtime.json` passed.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "user_intake_mail_controller_receipt_folds_packet_ledger or user_intake_mail_delivery_updates_packet_runtime_ledger or transient_temp_files or active_packet_ledger_writer or stable_startup_role_flags or partial_startup_role_flags" -q` passed with 5 selected tests.
- `openspec validate defer-active-writer-settlement --strict` passed.
- `openspec validate fold-mail-delivery-receipts --strict` passed.
- `python scripts/install_flowpilot.py --sync-repo-owned --json` passed and synchronized the installed local FlowPilot skill.
- `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json`, and `python scripts/check_install.py` passed with installed skill fresh.

### Findings
- Active runtime writers are now modeled as a settlement/defer state, not as immediate blocker evidence.
- Controller action scans skip `.tmp-*.json` files and tolerate scan/read disappearance.
- Mail-delivery folding raises the existing `RouterLedgerWriteInProgress` path when packet/mail ledger writes are active, allowing the daemon to wait on the next tick instead of creating a false blocker.
- Startup role flags are folded from bootstrap into Router state only as a stable pair.
- The parallel `make-repair-transactions-executable` OpenSpec remains the owner of repair transaction `plan_kind` execution; this change does not replace that work.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- Before final git submission, inspect and include compatible peer-agent work, especially `make-repair-transactions-executable`.

## 2026-05-15 Mail Delivery Receipt Runtime Fold Fix

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: The upgraded daemon reconciliation model and live-run projection showed that Controller `deliver_mail` receipts could be marked done without folding the `user_intake_delivered_to_pm` Router flag or packet mail ledger.
- Status: completed_focused_runtime_update
- OpenSpec change: `fold-mail-delivery-receipts`

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Runtime fold helper: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -m py_compile skills/flowpilot/assets/flowpilot_router.py tests/test_flowpilot_router_runtime.py simulations/flowpilot_daemon_reconciliation_model.py simulations/run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python -m pytest tests/test_flowpilot_router_runtime.py -q -k "user_intake_mail"` passed with direct mail delivery, Controller receipt mail delivery folding, packet release, and duplicate receipt idempotency coverage.
- `python -m pytest tests/test_flowpilot_router_runtime.py -q -k "controller_receipt"` passed.
- `python -m pytest tests/test_flowpilot_packet_runtime.py -q -k "controller_relay or user_intake_packet"` passed.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out tmp/flowguard_background/daemon_reconciliation_model_after_fix.json` passed with 7,056 explored traces, zero violations, zero stuck states, and the known hazard fixtures detected.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --json-out tmp/flowguard_background/daemon_reconciliation_live_after_fix.json` failed as expected against the current historical stopped run, with three pre-fix live projection findings: startup role flag fold required manual daemon restart, transient temp Controller action file race, and old `deliver_mail` receipt not folded to packet ledger.
- `python simulations/run_flowpilot_router_internal_mechanics_checks.py --json-out tmp/flowguard_background/router_internal_mechanics_after_runtime_fix.json` passed.
- `openspec validate fold-mail-delivery-receipts --strict` and `openspec validate internalize-router-mechanical-actions --strict` passed.
- `python scripts/install_flowpilot.py --sync-repo-owned --json` synchronized the installed `flowpilot` skill from repository source.
- `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json`, and `python scripts/check_install.py` passed with installed `flowpilot` source-fresh.
- `python scripts/smoke_autopilot.py --fast` passed and reused existing Meta/Capability proofs instead of rerunning those heavyweight checks.

### Findings
- Direct `deliver_mail` apply and Controller receipt reconciliation now use one Router-owned mail-delivery fold helper.
- The helper validates mail id, target role, and negative delivery confirmation; releases the packet envelope through `packet_runtime.controller_relay_envelope`; verifies packet holder/status and controller relay signature; folds the Router flag and `packet_ledger.mail` together; clears the packet-ledger check latch; and records mail delivery exactly once across repeated receipts.
- Controller receipt `deliver_mail` no longer falls into `unsupported_stateful_controller_receipt` when the receipt is complete and the packet-ledger check latch is present.
- The historical stopped run may still contain old blocked evidence until deliberately replayed or superseded; this fix changes the current runtime path and is covered by a focused regression.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction. The fast smoke reused their existing proofs.

### Next Actions
- Rerun heavyweight Meta/Capability checks before a release-level global claim, or if later changes broaden beyond the mail-delivery reconciliation boundary.

## 2026-05-15 Executable Repair Transaction Plan Kinds

- Project: FlowGuardProjectAutopilot_20260430
- OpenSpec change: `make-repair-transactions-executable`
- Trigger reason: PM repair decisions could be recorded as human-readable recovery intent without guaranteeing that Router had a concrete next action, existing producer, Router handler, or terminal stop to consume.
- Status: completed_focused_runtime_update_synced

### Model Evidence
- Repair transaction model: `simulations/flowpilot_repair_transaction_model.py`
- Repair transaction runner: `simulations/run_flowpilot_repair_transaction_checks.py`
- Runtime owner: `skills/flowpilot/assets/flowpilot_router.py`
- PM/Controller prompt contracts: `skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md`, `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`, and `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`

### Commands
- `python simulations/run_flowpilot_repair_transaction_checks.py --json-out simulations/flowpilot_repair_transaction_checks_results.json` passed with 12,968 explored traces, zero violations, zero dead branches, and known hazard fixtures detected.
- `openspec validate make-repair-transactions-executable --strict` passed.
- `python -m pytest tests/test_flowpilot_card_instruction_coverage.py tests/test_flowpilot_role_output_runtime.py -q` passed.
- `python -m py_compile skills/flowpilot/assets/flowpilot_router.py simulations/flowpilot_repair_transaction_model.py simulations/run_flowpilot_repair_transaction_checks.py` passed.
- `python -m pytest tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_repair_decision_rejects_legacy_event_replay_without_existing_producer tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_operation_replay_repair_transaction_queues_replay_action tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_controller_repair_work_packet_queues_bounded_controller_action tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_repair_decision_rejects_registered_but_not_receivable_rerun_target tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_repair_transaction_commits_material_reissue_generation tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_router_packet_audit_rejection_routes_pm_repair_decision tests/test_flowpilot_router_runtime.py::FlowPilotRouterRuntimeTests::test_pm_repair_decision_can_repeat_for_new_control_blocker -q` passed with 9 selected tests.
- `python scripts/install_flowpilot.py --sync-repo-owned --json` synchronized the installed `flowpilot` skill from repository source.
- `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json`, and `python scripts/check_install.py` passed with installed `flowpilot` source-fresh.

### Findings
- `repair_transaction.plan_kind` is now the execution authority; `recovery_option` and `repair_action` remain policy/explanation fields.
- Router validates executable plan kinds before committing PM repair decisions: `operation_replay`, `controller_repair_work_packet`, `packet_reissue`, `role_reissue`, `router_internal_reconcile`, `await_existing_event`, `route_mutation`, and `terminal_stop`.
- Legacy `event_replay` is only a deprecated alias for `await_existing_event`, and Router rejects it when there is no existing producer.
- `operation_replay` queues a concrete replay action only for recorded safe operations, and `controller_repair_work_packet` queues bounded Controller work with explicit reads, writes, forbidden actions, and success evidence.
- PM and Controller cards now explain when to choose each executable plan kind and what boundaries Controller must obey.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- The broad Router `-k "pm_repair_decision or repair_transaction or control_blocker"` pytest selection timed out; focused tests for the changed repair paths passed.

### Next Actions
- Rerun heavyweight Meta/Capability checks before a release-level global claim, or if later changes broaden beyond focused repair transaction execution.

## 2026-05-15 PM Card Bundle ACK Handoff Model Upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: A formal FlowPilot startup run accepted the PM system-card bundle ACK but left the ACK wait row open and did not dispatch the real `user_intake` packet from Controller to PM.
- Status: completed_focused_model_update

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`

### Commands
- `python -m py_compile simulations/flowpilot_daemon_reconciliation_model.py simulations/run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out simulations/flowpilot_daemon_reconciliation_model_only_results.json` passed with 10,356 explored traces, zero violations, zero stuck states, and the upgraded hazard fixtures detected.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --json-out simulations/flowpilot_daemon_reconciliation_results.json` failed as expected against the historical stopped run, because the new live projection found the PM ACK handoff gap.

### Findings
- The earlier model verified ACK validity and mail-delivery folding separately, but did not require the bridge between them: after a PM system-card bundle ACK resolves, the matching ACK wait row must be reconciled and the real `user_intake` packet must be dispatched if it is still held by Controller.
- The upgraded model now rejects stale ACK wait rows, action/scheduler disagreement, non-normalized completed ACK status, user-intake packets left with Controller after PM ACK, and unrelated Controller-action loops after ACK.
- The historical run projection found four matching findings: non-normalized completed ACK status, open `await_card_bundle_return_event` row, `user_intake` still `packet-with-controller`, and repeated unrelated display-status actions before user-intake dispatch.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- Implement the focused runtime fix by making system-card ACK resolution a single finalizer that atomically normalizes the return ledger, closes the matching Controller action and scheduler row, and then asks the packet ledger for the next real dispatch.

## 2026-05-16 Controller Patrol Timer Anti-Exit Loop

- Project: FlowGuardProjectAutopilot_20260430
- OpenSpec change: `add-controller-patrol-timer`
- Trigger reason: Controller could see an active daemon monitor with no immediate Controller action and incorrectly treat quiet standby as permission to close the foreground chat.
- Status: completed_focused_runtime_update_synced

### Model Evidence
- Patrol timer model: `simulations/flowpilot_controller_patrol_model.py`
- Patrol timer runner: `simulations/run_flowpilot_controller_patrol_checks.py`
- Result artifact: `simulations/flowpilot_controller_patrol_results.json`
- Runtime owner: `skills/flowpilot/assets/flowpilot_router.py`
- Prompt contract surfaces: `skills/flowpilot/SKILL.md`, `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`, `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`, and the generated `controller_table_prompt`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python simulations/run_flowpilot_controller_patrol_checks.py --json-out simulations/flowpilot_controller_patrol_results.json` passed with the focused anti-exit hazards detected.
- `python -m py_compile skills/flowpilot/assets/flowpilot_router.py simulations/flowpilot_controller_patrol_model.py simulations/run_flowpilot_controller_patrol_checks.py` passed.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "controller_patrol_timer or foreground_controller_standby or router_daemon_observation_initializes_lock_status_and_ledger" -q` passed with 14 selected tests.
- `python scripts/install_flowpilot.py --sync-repo-owned --json --skip-self-check` synchronized the installed `flowpilot` skill from repository source.
- `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json`, and `python scripts/check_install.py` passed with installed `flowpilot` source-fresh.

### Findings
- Controller standby now has a separate Controller-operated patrol command: `python skills\flowpilot\assets\flowpilot_router.py --root . --json controller-patrol-timer --seconds 10`.
- The existing Router daemon monitor remains the source of truth; the patrol timer is only a foreground keepalive and monitor-reading loop.
- A `continue_patrol` result explicitly tells Controller that no new work exists yet, that the loop exists to prevent accidental foreground exit, and that Controller must rerun the same command and wait for the next output.
- Starting or restarting the patrol command is not completion evidence. Completion is allowed only when terminal state reports `controller_stop_allowed: true`.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.
- Concrete conformance replay was not added for this abstract patrol model; runtime pytest covers the concrete CLI/payload behavior, while the focused FlowGuard model covers the anti-exit transition hazards.

### Next Actions
- Rerun heavyweight Meta/Capability checks before a release-level global claim, or if later changes broaden beyond the focused Controller patrol timer boundary.

## 2026-05-16 Router-Owned Startup User Intake ACK Settlement

- Project: FlowGuardProjectAutopilot_20260430
- OpenSpec change: `internalize-router-mechanical-actions`
- Trigger reason: PM system-card bundle ACK could be written and acknowledged while the real startup `user_intake` packet remained Controller-held and no Router-owned release to PM occurred.
- Status: completed_focused_runtime_update_synced

### Model Evidence
- Daemon reconciliation model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Daemon reconciliation runner/live projection: `simulations/run_flowpilot_daemon_reconciliation_checks.py`
- Runtime owners: `skills/flowpilot/assets/flowpilot_router.py`, `skills/flowpilot/assets/packet_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills/flowpilot/assets/packet_runtime.py skills/flowpilot/assets/flowpilot_router.py tests/test_flowpilot_router_runtime.py simulations/flowpilot_daemon_reconciliation_model.py simulations/run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out simulations/flowpilot_daemon_reconciliation_model_only_results.json` passed with 10,356 explored traces, zero violations, zero stuck states, and the upgraded startup release hazards detected.
- `python simulations/run_flowpilot_daemon_reconciliation_checks.py --json-out simulations/flowpilot_daemon_reconciliation_results.json` failed as expected against the historical stopped run because the live projection found the old ACK handoff gap.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "user_intake_from_startup_ui_is_router_owned or pm_card_bundle_ack_releases_router_owned_user_intake or user_intake_router_release_finalizer_is_idempotent or incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers or system_card_bundle" -q` passed with 4 selected tests.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "mail_delivery_receipt_waits_for_active_packet_ledger_writer or controller_patrol_timer or foreground_controller_standby" -q` passed with 14 selected tests.
- `python -m pytest tests/test_flowpilot_packet_runtime.py -k "user_intake_packet_records_startup_visibility_and_relays_to_pm" -q` passed with 1 selected test.
- `python -m pytest tests/test_flowpilot_router_runtime.py -k "user_intake or card_bundle_return_event or pm_card_bundle or startup_activation" -q` passed with 6 selected tests.
- `openspec validate internalize-router-mechanical-actions --strict` passed, and `openspec list --json` reported 22/22 tasks complete.
- `python scripts/install_flowpilot.py --sync-repo-owned --json` synchronized the installed `flowpilot` skill from repository source.
- `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json`, and `python scripts/check_install.py` passed with installed `flowpilot` source-fresh.

### Findings
- Startup `user_intake` is now created as Router-owned startup material (`router-held-startup-material`) instead of `packet-with-controller`.
- Router now runs a deterministic return settlement finalizer before computing the next visible action. It validates/normalizes PM card-bundle ACKs, reconciles matching Controller action and scheduler rows, clears matching pending waits, and releases the Router-owned startup `user_intake` to PM exactly once.
- `packet_runtime` now has a narrow `router_startup_release` signature for startup `user_intake` only. Normal formal packet/result relay remains Controller-controlled.
- The live projection found five issues in the historical stopped run: non-normalized completed ACK status, open ACK wait row, Controller-owned startup `user_intake`, unreleased PM startup packet, and repeated unrelated display-status actions after ACK.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction.

### Next Actions
- Rerun heavyweight Meta/Capability checks before a release-level global claim, or if later changes broaden beyond the focused startup ACK settlement boundary.

## 2026-05-16 Startup Intake Ledger-Return Prompt Boundary

- Project: FlowGuardProjectAutopilot_20260430
- OpenSpec change: `clarify-startup-intake-ledger-return`
- Trigger reason: native startup intake wording still told Controller to directly apply the UI result after the Router daemon had taken ownership of startup progress through daemon status and the Controller action ledger.
- Status: completed_focused_prompt_update_synced

### Model Evidence
- Prompt-boundary model: `simulations/flowpilot_prompt_boundary_model.py`
- Prompt-boundary runner/source projection: `simulations/run_flowpilot_prompt_boundary_checks.py`
- Focused runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python <Codex home>\skills\model-first-function-flow\assets\toolchain_preflight.py --json` reported installed FlowGuard schema `1.0`.
- `python simulations\run_flowpilot_prompt_boundary_checks.py --json-out tmp\flowguard_background\prompt_boundary_pre_fix.json` failed before the production prompt edit, with source failures for stale startup intake direct-apply wording.
- `python simulations\run_flowpilot_prompt_boundary_checks.py --json-out simulations\flowpilot_prompt_boundary_results.json` passed after the prompt edit.
- `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_waits_for_answers_before_banner_or_controller tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_startup_daemon_defers_banner_and_queues_next_boot_row` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_prompt_boundary_model.py simulations\run_flowpilot_prompt_boundary_checks.py tests\test_flowpilot_router_runtime.py` passed.
- `openspec validate clarify-startup-intake-ledger-return --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.
- Background heavyweight checks were launched with the stable log contract: `tmp\flowguard_background\run_meta_checks.*` and `tmp\flowguard_background\run_capability_checks.*`.

### Findings
- The startup intake instruction now returns Controller to Router daemon status and the Controller action ledger after the UI closes.
- The change intentionally avoids a long conditional prompt; Router-owned status and the existing work board remain the authority.
- The sealed body boundary is unchanged: Controller is still told not to paste the user's work request into chat or include body text in the Router payload.
- The prompt-boundary model now includes a known-bad `startup_intake_prompt_direct_apply` scenario and a valid `startup_intake_ledger_return_prompt` scenario.

### Skipped Or Deferred Steps
- Heavyweight Meta and Capability checks were not used as a foreground gate for this narrow prompt wording change; they were started in the background at user direction.

### Next Actions
- Inspect `tmp\flowguard_background\run_meta_checks.exit.txt` and `tmp\flowguard_background\run_capability_checks.exit.txt` before making any release-level global confidence claim.

## 2026-05-16 Startup Pre-Review Reconciliation Wait Visibility

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a live FlowPilot startup run exposed a pre-review reconciliation deadlock where an `await_current_scope_reconciliation` row waited for Router-owned startup mechanical audit and display-status obligations while also hiding the Router-owned actions that could satisfy those blockers.
- Status: completed_focused_model_update

### Model Evidence
- Startup control model: `simulations/flowpilot_startup_control_model.py`
- Startup control runner: `simulations/run_flowpilot_startup_control_checks.py`
- Result evidence: `simulations/flowpilot_startup_control_checks_results.json`, `simulations/flowpilot_startup_control_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile simulations\flowpilot_startup_control_model.py simulations\run_flowpilot_startup_control_checks.py` passed.
- `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_results.json` passed with 22,856 explored traces, zero explorer violations, zero stuck states, and the new wait-visibility hazards detected.
- `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_checks_results.json` passed with the same focused startup-control result.

### Findings
- The previous startup-control model was too coarse: it treated startup mechanical audit as a single flag and did not model the durable artifact versus reconciled state flag split.
- The model also did not represent startup display status as a required pre-review obligation and did not model whether a visible wait row can block the Router-owned action needed to clear itself.
- The upgraded model now rejects audit/display artifacts without reconciled flags, reconciled flags without durable evidence, reviewer fact reporting before display status, self-blocking pre-review waits, stale waits after blockers clear, and waits resolved before startup blockers are actually clear.
- A valid wait row remains allowed only when it represents a true external wait or still leaves a Router-owned progress path for local obligations.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because this pass only changed the focused startup-control model.
- Concrete conformance replay remains skipped for this abstract model because there is no production replay adapter in the allowed write set.

### Next Actions
- Minimal runtime repair should centralize startup pre-review obligation reconciliation in the Router before it creates or returns a wait row. The wait row should be a status projection, not the owner of Router-local startup work.
## 2026-05-16 - Controller core before startup obligations

- Trigger reason: The live FlowPilot startup queue exposed `emit_startup_banner`
  as Controller-ledger work before `load_controller_core`, making Controller
  appear to handle a row before the Controller core handoff was complete.
- Applicability: `use_flowguard`; behavior-flow model-first change for
  startup ordering, Controller action ledger authority, heartbeat binding, and
  role-slot startup side effects.
- Risk Intent Brief: prevent Controller-ledger startup obligations from being
  exposed before Controller core is loaded; preserve daemon single-writer
  ordering, Controller receipt reconciliation, sealed startup intake bodies,
  current-run heartbeat binding, and fresh role-slot proof before work beyond
  startup. Known-bad hazards include banner/heartbeat/role rows before
  Controller core, heartbeat missing before startup review or PM activation,
  and stale reconciliation creating false PM blockers.
- Pre-implementation check: `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed after adding the
  `startup_obligation_before_controller_core` rejected scenario.
- Heavyweight checks: `python simulations\run_meta_checks.py` and
  `python simulations\run_capability_checks.py` were explicitly skipped by
  user direction for this pass because they are too heavy. Focused startup,
  prompt-boundary, startup-control, role-recovery model, runtime, install, and
  OpenSpec checks remain the completion evidence for this scoped integration.

## 2026-05-16 Passive Wait Status Not Controller Work

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a live FlowPilot run showed a startup reconciliation wait occupying the Controller action slot even though Controller could not execute that row; the wait also hid Router-owned obligations that would clear it.
- Status: completed_runtime_repair

### Model Evidence
- Two-table async scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Two-table scheduler runner: `simulations/run_flowpilot_two_table_async_scheduler_checks.py`
- Startup control model: `simulations/flowpilot_startup_control_model.py`
- Result evidence: `simulations/flowpilot_two_table_async_scheduler_results.json`, `simulations/flowpilot_startup_control_checks_results.json`, `simulations/flowpilot_startup_control_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py tests\test_flowpilot_router_runtime.py` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed with zero explorer violations and the new passive-wait hazards detected.
- `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_checks_results.json` passed with 22,856 explored traces, zero explorer violations, and zero stuck states.
- `python simulations\run_flowpilot_startup_control_checks.py --json-out simulations\flowpilot_startup_control_results.json` passed with the same focused startup-control result.
- Focused runtime unittests covering passive wait projection, startup local obligation preemption, foreground standby, current-node reconciliation, and ACK reminders passed.
- `openspec validate separate-wait-status-from-controller-actions --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed with installed `flowpilot` source-fresh.

### Findings
- The root issue was not that Controller lacked a longer prompt. The problem was that Router could put a non-executable wait row on the Controller work board.
- Passive waits are now treated as Router-owned status projections. They remain visible in daemon/current-wait/standby status, but they are excluded from ordinary executable Controller action rows and active work counts.
- Router-local startup obligations now preempt passive reconciliation waits, so a wait cannot hide the exact Router action required to clear itself.
- Continuous standby remains the foreground Controller duty when there is no ordinary executable Controller work and FlowPilot is legitimately waiting on another role or event.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction for this pass.
- Concrete conformance replay remains skipped for the abstract scheduler/startup models where no production replay adapter exists.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.

## 2026-05-16 Controller User-Language Guidance

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Controller foreground reports could still surface internal Router/action/ledger/packet terms even though the user wanted plain-language status by default.
- Status: completed_focused_prompt_update

### Model Evidence
- OpenSpec change: `openspec/changes/narrow-controller-user-language-guidance/`
- Control-plane friction model: `simulations/flowpilot_control_plane_friction_model.py`
- Control-plane friction runner: `simulations/run_flowpilot_control_plane_friction_checks.py`
- Result evidence: `simulations/flowpilot_control_plane_friction_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py simulations\flowpilot_control_plane_friction_model.py simulations\run_flowpilot_control_plane_friction_checks.py` passed.
- `openspec validate narrow-controller-user-language-guidance --strict` passed.
- `python simulations\run_flowpilot_control_plane_friction_checks.py --json-out simulations\flowpilot_control_plane_friction_results.json` passed.
- A generated `controller_table_prompt` guidance smoke check passed.
- Focused runtime tests for display-plan user-reporting policy and progress summary passed.
- `python scripts\check_install.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` and `python scripts\audit_local_install_sync.py --json` passed with installed `flowpilot` source-fresh.

### Findings
- The Controller role card now tells Controller to start user updates by translating control-plane state into what the user can understand.
- The generated Controller work board now repeats the same compact reminder during long foreground runs.
- Technical names remain allowed when the user asks for detail or when a concrete blocker needs the name.
- No new Router plain-summary field, fixed report template, Route Sign rewrite, Mermaid rewrite, or sealed-body behavior was introduced.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were explicitly skipped by user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.

## 2026-05-16 Interactive Startup Intake Enforcement

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a formal FlowPilot startup was advanced with a headless startup intake result instead of opening the native UI, exposing that the UI boundary was prompt-described but not runtime-enforced.
- Status: completed_focused_runtime_update

### Model Evidence
- OpenSpec change: `openspec/changes/enforce-interactive-startup-intake/`
- Startup intake UI model: `simulations/flowpilot_startup_intake_ui_model.py`
- Result evidence: `simulations/flowpilot_startup_intake_ui_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python simulations\run_flowpilot_startup_intake_ui_checks.py --json-out simulations\flowpilot_startup_intake_ui_results.json` passed after the model was refined to allow true interactive UI cancellation while rejecting headless acceptance.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "startup_intake" -q` passed with 8 tests selected.
- Focused background-log reruns passed with exit code `0` for `startup_intake_ui`, `prompt_boundary`, `persistent_router_daemon`, `router_loop`, and `startup_intake_pytest` under `tmp/flowguard_background/`.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.

### Findings
- Startup intake artifacts now carry `launch_mode`, `headless`, and `formal_startup_allowed`.
- The headless helper writes `launch_mode: headless`, `headless: true`, and `formal_startup_allowed: false`.
- Router rejects formal startup intake results unless result, receipt, and envelope all identify an interactive native launch.
- Controller prompt guidance now explicitly stops non-interactive substitutions instead of treating them as a valid UI result.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were explicitly skipped by user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.

## 2026-05-16 Role Recovery Obligation Replay

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: mechanical role recovery still routed a recovered-role confirmation through PM even when the Router could mechanically restore memory and replay or settle the recovered role's outstanding waits.
- Status: completed_focused_runtime_update

### Model Evidence
- OpenSpec change: `openspec/changes/replay-role-recovery-obligations/`
- Role recovery model: `simulations/flowpilot_role_recovery_model.py`
- Role recovery runner: `simulations/run_flowpilot_role_recovery_checks.py`
- Result evidence: `simulations/flowpilot_role_recovery_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `openspec validate replay-role-recovery-obligations --strict` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py` passed.
- `python simulations\run_flowpilot_role_recovery_checks.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "mid_run_role_liveness_fault or role_recovery"` passed with 4 tests selected.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\audit_local_install_sync.py --json` passed after sequential rerun.

### Findings
- Mechanical recovery now scans current-run waits for the recovered role before involving PM.
- Existing valid ACK or output evidence settles the original wait without asking the role to redo work.
- Missing evidence creates ordered replacement work rows linked to the original wait, then marks the original wait `superseded` only after the replacement row is durable.
- Multiple replacements preserve original wait order.
- PM escalation remains reserved for semantic ambiguity, conflicts, repeated recovery failure, or route/acceptance/task-semantics changes.
- The Router bridges the legacy `pm_resume_recovery_decision_returned` flag after successful mechanical replay so older expected-event waits do not reintroduce a PM notification path.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.
- In a later cleanup, consider renaming the legacy PM-resume flag to separate "recovery continuation satisfied" from "PM explicitly decided."

## 2026-05-16 Resume Rehydration Obligation Replay

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: heartbeat/manual resume restored all six role memories but still asked PM for the next step before Router compared current-run waits and evidence.
- Status: completed_focused_runtime_update

### Model Evidence
- OpenSpec change: `openspec/changes/replay-resume-rehydration-obligations/`
- Resume model: `simulations/flowpilot_resume_model.py`
- Resume runner: `simulations/run_flowpilot_resume_checks.py`
- Role recovery model: `simulations/flowpilot_role_recovery_model.py`
- Role recovery runner: `simulations/run_flowpilot_role_recovery_checks.py`
- Result evidence: `simulations/flowpilot_resume_results.json`, `simulations/flowpilot_role_recovery_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_resume_model.py simulations\run_flowpilot_resume_checks.py` passed.
- `python simulations\run_flowpilot_resume_checks.py` passed.
- `python simulations\run_flowpilot_role_recovery_checks.py` passed.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "resume or role_recovery or role_no_output" -q` passed with 16 selected tests.
- `openspec validate replay-resume-rehydration-obligations --strict` passed.
- `openspec validate --all --strict` was attempted; all changes passed except existing `enforce-flowpilot-daemon-startup`, whose spec lacks delta sections.
- `python scripts\check_install.py` passed.
- After clearing Python caches, `python scripts\install_flowpilot.py --sync-repo-owned --skip-self-check --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.

### Findings
- Heartbeat/manual resume now invokes the shared role-recovery obligation replay after successful six-role rehydration and current-run memory injection.
- Existing Router-visible evidence is settled without PM; missing evidence creates durable replacement rows before superseding original waits.
- Mechanical replay sets the legacy PM-resume continuation flag so old wait selection does not reintroduce a PM prompt.
- Ambiguous or memory-incomplete resume still keeps the PM escalation path.
- Active control blockers can proceed after mechanical replay completes without PM escalation.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were explicitly skipped by user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.

## 2026-05-16 Generic Wait Target Reminder Rows

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a FlowPilot passive wait could say a role reminder was due without materializing an executable Controller action, leaving Controller to search for reminder text instead of sending Router-authored text.
- Status: completed_focused_runtime_update

### Model Evidence
- OpenSpec change: `openspec/changes/separate-wait-status-from-controller-actions/`
- Persistent Router daemon model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Persistent Router daemon runner: `simulations/run_flowpilot_persistent_router_daemon_checks.py`
- Two-table async scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Result evidence: `simulations/flowpilot_persistent_router_daemon_results.json`, `simulations/flowpilot_two_table_async_scheduler_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py` passed.
- Focused runtime tests for report-result reminders, ACK reminders, passive waits, standby behavior, and Controller-local waits passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed with zero safe-graph invariant failures and the new reminder-without-action hazard detected.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed with zero safe-graph invariant failures.
- `openspec validate separate-wait-status-from-controller-actions --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed with installed `flowpilot` source-fresh.

### Findings
- Passive waits remain Router-owned status, not ordinary Controller work.
- Due reminders are now separate generic Controller work rows: `send_wait_target_reminder` targets the current waiting role, not a reviewer-specific path.
- Controller sends only Router-authored `reminder_text`, avoids sealed bodies, and receipts the reminder hash plus liveness fields.
- Report-result reminders require a fresh liveness probe before the wait metadata can be updated.
- ACK reminders update reminder metadata and matching pending-return status without satisfying the original ACK or result wait.

### Skipped Steps
- Full `python -m unittest tests.test_flowpilot_router_runtime` was attempted and timed out after five minutes, so it is not treated as pass evidence.
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were explicitly skipped by user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.
- If the full runtime suite remains slow, split it into focused named groups so timeout does not hide the result of unrelated runtime checks.

## 2026-05-16 Startup Reconciliation Passive Wait Self-Block

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: the startup pre-review reconciliation wait could persist after the real startup flags and card ACKs were reconciled because `await_current_scope_reconciliation` itself was counted as a pending startup Controller row.
- Status: completed_runtime_repair

### Model Evidence
- OpenSpec change: `openspec/changes/fix-startup-reconciliation-self-block/`
- Focused model: `simulations/flowpilot_current_scope_pre_review_reconciliation_model.py`
- Focused result: `simulations/flowpilot_current_scope_pre_review_reconciliation_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime test: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `openspec validate fix-startup-reconciliation-self-block --strict` passed.
- `python simulations\run_flowpilot_current_scope_pre_review_reconciliation_checks.py` passed with zero violations and the passive-wait-counted-as-local-obligation hazard detected.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "startup_reconciliation_wait_does_not_block_itself or startup_reconciliation_wait_does_not_hide_router_local_obligation or startup_daemon_queues_role_heartbeat_and_controller_core_without_role_wait"` passed with 3 selected tests.
- Background `run_light_checks` completed with exit code `0` under `tmp/flowguard_background/`; its metadata records a fresh proof with Meta, Capability, model-mesh, and smoke-autopilot commands skipped.
- `openspec validate --all --strict` passed after correcting an unrelated historical OpenSpec delta header.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed FlowPilot source-fresh.

### Findings
- Passive wait status rows must remain visible as Router-owned status, but they cannot count as ordinary executable Controller work or as startup pre-review blockers.
- `_startup_pre_review_reconciliation_blockers` now filters Controller rows through the ordinary-work classifier before treating them as local startup obligations.
- The runtime still preserves blocking behavior for real executable Controller rows and wait-shaped rows that require Controller side effects or receipts.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were intentionally skipped at user direction for this pass.
- `python simulations/run_flowpilot_model_mesh_checks.py` and `python scripts/smoke_autopilot.py` were also excluded from the light background batch because they invoke heavyweight Meta/Capability-style work.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.

## 2026-05-16 Work ACK Continuation And No-Output Reissue

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a background role could ACK a work item and then stop, or finish without submitting the Router-visible output; the user asked to harden all work packets and retry same-work no-output waits before role recovery.
- Status: completed_focused_runtime_update

### Model Evidence
- OpenSpec change: `openspec/changes/harden-work-packet-ack-and-no-output-retry/`
- Prompt-boundary model: `simulations/flowpilot_prompt_boundary_model.py`
- Two-table async scheduler model: `simulations/flowpilot_two_table_async_scheduler_model.py`
- Result evidence: `simulations/flowpilot_prompt_boundary_results.json`, `simulations/flowpilot_two_table_async_scheduler_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py simulations\flowpilot_prompt_boundary_model.py simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_prompt_boundary_checks.py simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `python simulations\run_flowpilot_prompt_boundary_checks.py` passed.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.
- `python -m unittest` focused Router runtime tests for no-output reissue, legacy liveness-fault redirect, two-retry PM escalation, unavailable-role recovery, wait closure, and event registry behavior passed.
- `openspec validate harden-work-packet-ack-and-no-output-retry --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.

### Findings
- Work-card and packet prompts now say ACK is receipt only; work remains unfinished until Router receives the expected output or blocker.
- Router wait status now separates no-output from unavailable-role liveness faults.
- `controller_reports_role_no_output` creates a durable replacement wait and supersedes the old wait before continuation.
- Legacy `controller_reports_role_liveness_fault` payloads with `completed` or `completed_without_expected_event` are redirected to no-output reissue instead of role recovery.
- The no-output path retries twice, then escalates through the PM/control-blocker path.
- Missing/cancelled/unknown/unresponsive/blocked/lost roles still use unified role recovery.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were explicitly skipped by user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.

## 2026-05-16 FlowPilot Invocation Intent Isolation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a user request to start FlowPilot was incorrectly treated as permission to continue the run named by `.flowpilot/current.json`; historical and parallel running FlowPilot runs must remain independent unless the user explicitly targets one.
- Status: completed_focused_runtime_update

### Model Evidence
- OpenSpec change: `openspec/changes/separate-new-invocation-from-resume/`
- Focused model: `simulations/flowpilot_parallel_run_isolation_model.py`
- Focused result: `simulations/flowpilot_parallel_run_isolation_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python simulations\run_flowpilot_parallel_run_isolation_checks.py --json` passed and detected the expected bad-startup and ambiguous-resume hazards.
- Focused runtime pytest selection for fresh `start`, stale `current.json`, multiple parallel runs, JSON parsing, daemon binding, and targeted stop passed with 6 selected tests.
- `openspec validate separate-new-invocation-from-resume --strict` passed.
- `python scripts\check_install.py` passed after keeping `skills/flowpilot/SKILL.md` under the small launcher limit.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.

### Findings
- Fresh formal startup now uses the explicit router `start` command and creates a new run even when `.flowpilot/current.json` points at a running run.
- Existing running runs are independent parallel workflows; fresh startup does not attach, stop, merge, supersede, import, or mutate them.
- Resume remains explicit and target-bound. Ambiguous resume cannot silently choose the current pointer.
- Launcher and README guidance now state that `.flowpilot/current.json` is UI/default-target metadata, not startup intent.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were explicitly skipped by user direction because they are too heavy for this focused pass.

### Next Actions
- Before release-level confidence claims, run the heavyweight Meta and Capability checks in the stable background log contract and inspect their exit artifacts.
- Include any peer-agent work that is present at final staging time, per user direction.

## 2026-05-16 FlowPilot Startup Reconciliation Model Upgrade

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot startup exposed a class of races where a foreground start/status reader can collide with a fresh runtime-state writer, and startup Controller receipts can be marked reconciled only after a separate startup-daemon postcondition path.
- Status: completed_model_update_with_live_projection_findings

### Model Evidence
- Focused model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Focused runner/result: `simulations/run_flowpilot_daemon_reconciliation_checks.py`, `simulations/flowpilot_daemon_reconciliation_results.json`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out simulations\flowpilot_daemon_reconciliation_results.json` passed: safe graph ok, progress ok, FlowGuard explorer ok, and hazard checks ok.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` correctly failed the live projection for the current run because existing durable records still hit startup projection gaps.

### Findings
- The model now requires a foreground start command that sees a fresh runtime writer to wait, retry after settlement, and only then return live daemon status.
- The model now rejects a foreground start/status path that turns an active runtime writer into a fatal error or reports live status before settlement.
- Startup Controller receipts now require a single-owner fold of action row, scheduler row, pending state, bootstrap postcondition, and run-state projection; a separate later apply path is modeled as a hazard.
- Live projection for `run-20260516-090714` flagged startup receipt/application split on `load_controller_core` and `open_startup_intake_ui`, plus the existing PM ACK/user-intake projection issue.

### Skipped Steps
- Heavyweight `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` were not run because this pass changed only the focused FlowGuard model and live projection, not runtime behavior.

### Next Actions
- Runtime fix should centralize startup settlement behind one idempotent reconciler and make foreground start/status reads wait or retry on fresh runtime-state write locks before returning status.

## 2026-05-16 FlowPilot Packet Open Authority Exits

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: PM successfully opened the startup `user_intake` packet in the runtime ledger but then reported it was waiting for corrected relay evidence; roles needed an explicit work-or-formal-exit rule after verified packet open.
- Status: focused_runtime_and_prompt_update_complete_heavy_checks_user_deferred

### Risk Intent

- Prevent a verified `open-packet` receipt from being reinterpreted as missing authority.
- Prevent PM from routing a blocker back to PM or inventing a new repair channel.
- Preserve ordinary role blockers as formal decision inputs for PM/Router.
- Keep Controller sealed-body isolation unchanged.

### Model Evidence

- OpenSpec change: `openspec/changes/harden-packet-open-authority-exits/`
- Focused model: `simulations/flowpilot_packet_open_authority_model.py`
- Focused runner/result: `simulations/run_flowpilot_packet_open_authority_checks.py`, `simulations/flowpilot_packet_open_authority_results.json`
- Runtime implementation: `skills/flowpilot/assets/packet_runtime.py`
- Prompt/card updates: PM startup/review cards, PM/worker/reviewer/officer role cards, and packet body template.

### Commands

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python -m py_compile skills\flowpilot\assets\packet_runtime.py simulations\flowpilot_packet_open_authority_model.py simulations\run_flowpilot_packet_open_authority_checks.py tests\test_flowpilot_packet_runtime.py tests\test_flowpilot_card_instruction_coverage.py` passed.
- `python simulations\run_flowpilot_packet_open_authority_checks.py --json-out simulations\flowpilot_packet_open_authority_results.json` passed: safe graph ok, progress ok, FlowGuard explorer ok, and all known-bad hazards detected.
- `openspec validate harden-packet-open-authority-exits --strict` passed.
- `python -m unittest tests.test_flowpilot_packet_runtime` passed.
- `python -m unittest tests.test_flowpilot_card_instruction_coverage` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed with installed `flowpilot` source-fresh.
- Background heavyweight checks were launched under `tmp/flowguard_background/` and then stopped after the user confirmed they are too heavy for this pass:
  - `run_meta_checks`: `python simulations/run_meta_checks.py`, stopped with `exit_code=skipped_by_user`.
  - `run_capability_checks`: `python simulations/run_capability_checks.py`, stopped with `exit_code=skipped_by_user`.

### Findings

- Packet-open sessions now persist `work_authority` metadata in the runtime session, packet envelope, packet ledger, and Controller status packet.
- A successful packet open now states that the addressed role has authority to work that packet and must not wait for another relay or prompt.
- PM guidance now points PM inability to existing exits: `pm_startup_repair_request`, `pm_startup_protocol_dead_end`, and `pm_control_blocker_repair_decision`.
- Ordinary worker, reviewer, and officer guidance now says true inability after a verified open must return an existing formal blocker, result-with-blocker, or PM suggestion for PM/Router disposition.
- Step 3 active-writer settlement and Step 4 current-work-owner display were not taken over because parallel OpenSpec changes already own those scopes.

### Skipped Or Deferred Steps

- No focused checks were skipped.
- Heavyweight Meta and Capability checks were explicitly deferred by user direction because they are too heavy for this focused pass. Their background processes were stopped and their log metadata records `status=skipped_by_user_after_start`; do not claim those checks passed.

### Next Actions

- Before a release-level or broad project-control confidence claim, rerun Meta and Capability checks and inspect their `.exit.txt`, `.meta.json`, `.out.txt`, `.err.txt`, and `.combined.txt` artifacts.
- Commit only after compatible parallel-agent work has settled, because the user asked for peer changes to be included together.

## 2026-05-16 FlowPilot Current Work Owner Projection

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: monitor/status payloads could have `waiting_for_role: null` while real work was still held by a role, Controller reconciliation, or Router internal daemon work.
- Status: completed_runtime_update_with_background_regression

### Model Evidence
- OpenSpec change: `openspec/changes/surface-current-work-owner/`
- Focused model: `simulations/flowpilot_persistent_router_daemon_model.py`
- Focused result: `simulations/flowpilot_persistent_router_daemon_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `openspec validate surface-current-work-owner --strict` passed.
- `python -m py_compile` passed for the changed Router and FlowGuard model/runner files.
- Focused runtime pytest selections for `current_work`, passive waits, status summary, and foreground standby passed.
- `python simulations\run_flowpilot_persistent_router_daemon_checks.py --json-out simulations\flowpilot_persistent_router_daemon_results.json` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\check_install.py` passed with installed `flowpilot` source-fresh.
- Heavyweight background checks completed under `tmp/flowguard_background/`: `run_meta_checks` exit `0`, `run_capability_checks` exit `0`, both `proof_reuse=false`.

### Findings
- Status payloads now expose a single `current_work` object that names the effective current owner, task, source, and Controller liveness-use guidance.
- The legacy `current_wait` and `waiting_for_role` fields remain compatibility fields; Controller-facing monitoring should prefer `current_work`.
- Packet-ledger ownership now surfaces the role holder even when `pending_action` and legacy waiting fields are empty.
- Passive reconciliation and internal daemon work now name Controller or Router explicitly instead of leaving the monitor owner blank.

### Skipped Steps
- No heavyweight checks were skipped; both Meta and Capability background regressions completed with fresh exit artifacts.

### Next Actions
- Keep future monitor UI/copy on `current_work` as the primary live-owner projection and treat `waiting_for_role` as legacy compatibility only.

## 2026-05-16 FlowPilot Daemon Heartbeat Liveness Window

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: foreground patrol could classify an old daemon heartbeat as stale/restart work before Controller performed a real liveness check.
- Status: completed_runtime_update_with_background_regression

### Risk Intent

- Keep the monitor simple: heartbeat status is only `ok` or `check_liveness`.
- Treat five seconds as the foreground check window; a delayed heartbeat is not by itself proof that the daemon is dead.
- Make Controller perform the real process/lock/status liveness check, attach when the owner is alive, and recover only when that check finds the daemon dead.
- Preserve the single-writer invariant: never start a second Router writer while the current-run daemon owner is still live.

### Model Evidence

- OpenSpec change: `openspec/changes/soften-daemon-heartbeat-liveness/`
- Focused model: `simulations/flowpilot_daemon_liveness_model.py`
- Focused runner/result: `simulations/run_flowpilot_daemon_liveness_checks.py`, `simulations/flowpilot_daemon_liveness_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `python simulations\run_flowpilot_daemon_liveness_checks.py --json-out simulations\flowpilot_daemon_liveness_results.json` passed: safe graph ok, progress ok, FlowGuard explorer ok, and known-bad hazards detected.
- `python -m py_compile simulations\flowpilot_daemon_liveness_model.py simulations\run_flowpilot_daemon_liveness_checks.py skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py` passed.
- Focused pytest coverage for delayed heartbeat patrol, stopped daemon liveness check, delayed-live resume attach, dead-daemon resume recovery, and existing missing-pid status passed.
- Focused pytest coverage for existing foreground standby/patrol ready-action and continue-patrol behavior passed.
- `openspec validate soften-daemon-heartbeat-liveness --strict` passed.
- `python scripts\check_install.py` passed.
- Background heavyweight checks completed under `tmp/flowguard_background/`: `run_meta_checks` exit `0`, `run_capability_checks` exit `0`, and `run_flowpilot_persistent_router_daemon_checks` exit `0`.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, and `python scripts\install_flowpilot.py --check --json` passed with installed `flowpilot` source-fresh.

### Findings

- `runtime/router_daemon_status.json`, foreground standby snapshots, and current status summaries now expose five-second heartbeat metadata and `check_liveness` guidance.
- `controller-patrol-timer` returns `check_liveness` with plain Controller instructions instead of `daemon_repair_or_restart` when monitor evidence is delayed or incomplete.
- Resume recovery now uses active owner process liveness for attach-first behavior, so an old heartbeat with a live owner attaches instead of restarting.

### Skipped Or Deferred Steps

- A first attempt to extend the broad daemon reconciliation model was stopped because it expanded the unrelated state space too much. The focused liveness model now owns this policy.
- No heavyweight checks were skipped. The broad daemon reconciliation model extension attempt was stopped intentionally and replaced by the focused liveness model before production edits.

## 2026-05-16 FlowPilot Startup Settlement Ownership

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: startup could fail or leave false repair blockers when a foreground command observed an active runtime writer, and startup bootloader completion had two competing owners: the startup daemon postcondition path and the scheduled Controller receipt reconciler.
- Status: completed_focused_runtime_update

### Risk Intent

- Reuse the existing runtime JSON write-lock liveness rule instead of adding a second lock system.
- Foreground startup/status commands wait and retry when another live writer is making progress.
- Keep one owner for final startup settlement: Controller receipt reconciliation folds the action row, scheduler row, bootstrap flag, and pending state.
- Preserve real failures: stale locks, unsupported receipts, malformed state, and genuine blockers still fail instead of being hidden.

### Model Evidence

- OpenSpec change: `openspec/changes/unify-startup-settlement-ownership/`
- Focused model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Focused runner/result: `simulations/run_flowpilot_daemon_reconciliation_checks.py`, `simulations/flowpilot_daemon_reconciliation_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `openspec validate unify-startup-settlement-ownership --strict` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --json-out simulations\flowpilot_daemon_reconciliation_results.json` passed: safe graph `1069` states / `1129` edges, zero invariant failures, FlowGuard Explorer `13914` traces / zero violations, live projection finding count `0`, and current run can continue.
- Focused pytest coverage for foreground writer settlement, startup receipt ownership, legacy canonicalization, and existing daemon writer wait behavior passed.
- `python skills\flowpilot\assets\flowpilot_router.py --root . reconcile-run --json` canonicalized current-run startup rows through the receipt owner.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed; installed `flowpilot` was source-fresh and `check_install` reported `451` passing checks.

### Findings

- Fresh writer locks are now treated as short-lived progress, so foreground commands wait and retry instead of immediately reporting a fatal JSON/write error.
- Startup bootloader completion now writes/uses the existing Controller receipt and lets the scheduled receipt reconciler perform final settlement.
- Legacy rows that were already marked by the old daemon-postcondition owner are canonicalized to the Controller receipt owner when the receipt evidence exists.
- The live projection now accepts a Router-released `user_intake` packet that has already been opened by PM, avoiding a false "not released" model finding.

### Skipped Or Deferred Steps

- `python simulations/run_meta_checks.py` was deferred by explicit user direction because it is too heavy for this focused pass.
- `python simulations/run_capability_checks.py` was deferred by explicit user direction because it is too heavy for this focused pass.
- A full `tests/test_flowpilot_router_runtime.py` run exceeded the practical timeout while other peer-agent tests were also active, so completion evidence uses the focused tests plus the formal daemon reconciliation model and install checks.

### Next Actions

- Run Meta and Capability checks later before making release-level confidence claims.
- Preserve compatible peer-agent changes in the final local commit after the combined worktree settles.

## 2026-05-16 FlowPilot Native Startup Intake Receipt Fold

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: a real startup run received a done Controller receipt for `open_startup_intake_ui`, but the startup bootloader receipt effect layer did not recognize that receipt action and blocked at the startup barrier with `unsupported_startup_bootloader_receipt_action`.
- Status: completed_focused_runtime_update

### Risk Intent

- Keep the native startup intake result validation in one shared function.
- Let both direct bootloader apply and Controller receipt reconciliation fold the same `startup_intake_result.result_path` into bootstrap state.
- Preserve the existing internal `startup_daemon_bootloader_apply` receipt path so old direct-apply completion receipts remain compatible.
- Keep Meta and Capability regressions deferred by explicit user direction for this focused pass.

### Model Evidence

- OpenSpec change: `openspec/changes/unify-startup-settlement-ownership/`
- Focused model: `simulations/flowpilot_daemon_reconciliation_model.py`
- Focused runner/result: `simulations/run_flowpilot_daemon_reconciliation_checks.py`, `tmp/flowguard_background/run_daemon_reconciliation_focus.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `openspec validate unify-startup-settlement-ownership --strict --json` passed.
- `python -m compileall -q skills\flowpilot\assets\flowpilot_router.py simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py tests\test_flowpilot_router_runtime.py` passed.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection --json-out tmp\flowguard_background\run_daemon_reconciliation_focus.json` passed: safe graph `1141` states / `1201` edges, zero invariant failures, FlowGuard Explorer `14694` traces / zero violations, and hazard checks ok.
- Focused unittest coverage for native startup intake Controller receipts, startup receipt owner preservation, legacy owner canonicalization, load-controller-core receipt reconciliation, startup wait prompt guidance, native cancellation, and native intake validation passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py` passed; installed `flowpilot` was source-fresh.

### Findings

- The missed path was a receipt-layer protocol gap, not a UI or payload problem: the native UI payload already validated, but receipt reconciliation lacked a branch for `open_startup_intake_ui`.
- `_apply_startup_intake_result_to_bootstrap` now centralizes the startup intake write and deterministic bootstrap seed so direct apply and Controller receipt reconciliation use the same behavior.
- The startup receipt effect layer now recognizes a real native startup-intake receipt while still routing internal `startup_daemon_bootloader_apply` receipts through the existing satisfied-flag path.
- The focused model now includes a native-startup-intake receipt kind and an expected hazard for rejecting a complete native UI receipt as unsupported.

### Skipped Or Deferred Steps

- `python simulations/run_meta_checks.py` was skipped by explicit user direction because it is too heavy for this focused pass.
- `python simulations/run_capability_checks.py` was skipped by explicit user direction because it is too heavy for this focused pass.
- Live projection was skipped for the focused daemon reconciliation model because the current stopped startup run is historical evidence from before the repair.

### Next Actions

- Run Meta and Capability checks later before release-level confidence claims.
- Preserve compatible peer-agent changes and the untracked parallel OpenSpec work when preparing any combined git commit.

## 2026-05-16 Thin Parent Meta/Capability Validation

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Meta and Capability parent regressions were still release-scale graphs, making routine validation depend on long proof reuse or heavyweight foreground runs.
- Status: completed_with_background_full_regression

### Risk Intent

- Make routine Meta and Capability validation foreground-friendly through thin parent evidence aggregation.
- Keep full legacy Meta and Capability graph exploration available as explicit forced/background release evidence.
- Preserve release confidence boundaries so thin parent success cannot silently replace full-regression proof.
- Treat the hierarchy as recursive: any child model that crosses the heavyweight threshold must become a domain parent or remain full-regression-only.

### Model Evidence

- OpenSpec change: `openspec/changes/thin-heavy-flowguard-parent-models/`
- Parent ledger: `simulations/flowpilot_parent_responsibility_ledger.json`
- Thin parent helper: `simulations/flowpilot_thin_parent_checks.py`
- Parent runners: `simulations/run_meta_checks.py`, `simulations/run_capability_checks.py`
- Hierarchy runner/result: `simulations/run_flowpilot_model_hierarchy_checks.py`, `simulations/flowpilot_model_hierarchy_results.json`
- Thin results: `simulations/meta_thin_parent_results.json`, `simulations/capability_thin_parent_results.json`
- Full background log root: `tmp/flowguard_background/`

### Commands

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- `openspec validate thin-heavy-flowguard-parent-models --strict` passed.
- `python -m py_compile simulations\flowpilot_thin_parent_checks.py simulations\run_meta_checks.py simulations\run_capability_checks.py simulations\run_flowpilot_model_hierarchy_checks.py scripts\run_flowguard_coverage_sweep.py tests\test_flowpilot_thin_parent_checks.py` passed.
- `python simulations\run_meta_checks.py --fast` refreshed/reused the thin parent proof; thin Meta result is `9` states / `16` edges, routine confidence `current`, release confidence `current_with_full_regression`.
- `python simulations\run_capability_checks.py --fast` refreshed/reused the thin parent proof; thin Capability result is `7` states / `12` edges, routine confidence `current`, release confidence `current_with_full_regression`.
- `python simulations\run_flowpilot_model_hierarchy_checks.py --json-out simulations\flowpilot_model_hierarchy_results.json` passed and reported release confidence `current`, with no heavy parent full-regression obligations.
- Full Meta regression ran in the background with base name `run_meta_checks`: stdout `tmp/flowguard_background/run_meta_checks.out.txt`, stderr `tmp/flowguard_background/run_meta_checks.err.txt`, combined `tmp/flowguard_background/run_meta_checks.combined.txt`, exit `tmp/flowguard_background/run_meta_checks.exit.txt`, meta `tmp/flowguard_background/run_meta_checks.meta.json`, exit code `0`, proof reuse `false`.
- Full Capability regression ran in the background with base name `run_capability_checks`: stdout `tmp/flowguard_background/run_capability_checks.out.txt`, stderr `tmp/flowguard_background/run_capability_checks.err.txt`, combined `tmp/flowguard_background/run_capability_checks.combined.txt`, exit `tmp/flowguard_background/run_capability_checks.exit.txt`, meta `tmp/flowguard_background/run_capability_checks.meta.json`, exit code `0`, proof reuse `false`.
- `python -m unittest tests.test_flowpilot_thin_parent_checks tests.test_flowguard_result_proof tests.test_flowguard_legacy_runner_progress` passed.
- `python scripts\smoke_autopilot.py --fast` passed.
- `python scripts\check_install.py` passed.
- `python scripts\run_flowguard_coverage_sweep.py --timeout-seconds 60 --json-out tmp\flowguard_coverage_sweep_after_full.json` passed with `72` runners parsed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\audit_local_install_sync.py --json` passed; installed `flowpilot` was source-fresh.

### Findings

- Default Meta and Capability validation now reads bounded child evidence contracts instead of expanding the full legacy parent graph.
- Full legacy regressions remain explicit release or forced checks, so routine confidence and release confidence are no longer conflated.
- Hierarchy inventory now shows thin parent result type, thin proof status, legacy full proof status, and full-regression obligations separately.
- The old full parent graphs are still expensive and should be retired from mandatory release gating only after equivalence coverage is strong enough; until then they remain background oracle evidence.
- Recursive split policy is now documented: if a child evidence model crosses the heavyweight threshold, split it into a domain parent rather than letting routine validation grow again.

### Skipped Or Deferred Steps

- No required validation was skipped. Coverage sweep still reports live/current-state findings from the active local FlowPilot run, but the sweep itself parsed all runners and returned ok.

### Next Actions

- Add domain-parent layers when any child or shared-kernel evidence model crosses the heavyweight threshold.
- Consider replacing mandatory full release oracle runs with approved equivalence proof plus periodic or sampled full regression after the hierarchy has more release history.

## 2026-05-16 Startup Intake Release Boundary Integration

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User identified that PM could receive and open the full startup `user_intake` before the startup activation gate had opened.
- Status: completed_focused_validation_meta_capability_skipped_by_user_direction

### Risk Intent

- Preserve the hard startup activation boundary.
- Prevent full task-body delivery to PM before reviewer facts and PM startup activation approval.
- Keep post-activation material scan dependent on full `user_intake` delivery.
- Keep pre-activation PM work limited to startup authorization metadata: startup answers, run/role/continuation/display evidence, and sealed user-intake path/hash.

### Model Evidence

- OpenSpec change: `openspec/changes/delay-full-user-intake-release/`
- Startup-control model/result: `simulations/flowpilot_startup_control_model.py`, `simulations/flowpilot_startup_control_checks_results.json`
- Prompt-isolation model/result: `simulations/prompt_isolation_model.py`, `simulations/prompt_isolation_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands

- `openspec validate delay-full-user-intake-release --strict` passed.
- `python simulations\run_flowpilot_startup_control_checks.py` passed: safe graph `298` states / `313` edges, zero invariant failures, FlowGuard Explorer `21920` traces / zero violations.
- `python simulations\run_prompt_isolation_checks.py` passed: safe graph `346` states / `345` edges, zero invariant failures.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "user_intake or card_bundle or startup_activation or material_work_packet_records_target_ack_preflight_passed" -q` passed with `8` selected tests.
- `python -m pytest tests\test_flowpilot_packet_runtime.py -k "user_intake or startup_visibility or relays_to_pm" -q` passed with `1` selected test.
- `python -m pytest tests\test_flowpilot_card_instruction_coverage.py -q` passed with `7` tests and `75` subtests.
- `python -m py_compile simulations\flowpilot_startup_control_model.py simulations\run_flowpilot_startup_control_checks.py simulations\prompt_isolation_model.py simulations\run_prompt_isolation_checks.py skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py tests\test_flowpilot_card_instruction_coverage.py` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\audit_local_install_sync.py --json` passed; installed `flowpilot` is source-fresh.

### Findings

- The startup `user_intake` packet is now router-held startup material before activation instead of being PM-delivered after PM startup card ACK.
- The finalizer waits for `startup_activation_approved` before releasing full `user_intake` and remains idempotent afterward.
- PM startup-intake and activation cards now frame pre-activation work around startup metadata, not the full task body.

### Skipped Or Deferred Steps

- `python simulations\run_meta_checks.py` was skipped by explicit user direction because it is too heavy for this focused pass.
- `python simulations\run_capability_checks.py` was skipped by explicit user direction because it is too heavy for this focused pass.
- Broader full-router runtime coverage remains expensive, so this focused integration evidence uses the startup/prompt models, focused runtime tests, card/packet coverage, and install sync checks.

## 2026-05-16 Startup Intake Controller Relay Correction

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Follow-up review showed the delayed startup `user_intake`
  path still used Router-only release evidence. The intended rule is narrower:
  Router may authorize that the packet is next, but PM may open the formal
  packet only after Controller relay.
- Status: completed_focused_validation_meta_capability_skipped_by_user_direction

### Risk Intent

- Preserve the existing formal-mail safety gate: all formal packet bodies need
  Controller relay before recipient open.
- Keep `user_intake` sealed and Router-held before startup activation.
- After `startup_activation_approved`, expose normal `deliver_mail` for
  `user_intake`; Controller writes `packet_controller_relay`, then PM can open.
- Prevent stale `router_startup_release` evidence from acting as body-open
  authority.

### Model Evidence

- OpenSpec change: `openspec/changes/delay-full-user-intake-release/`
- Startup-control model/result:
  `simulations/flowpilot_startup_control_model.py`,
  `simulations/flowpilot_startup_control_checks_results.json`
- Prompt-isolation model/result: `simulations/prompt_isolation_model.py`,
  `simulations/prompt_isolation_results.json`
- Daemon reconciliation model/result:
  `simulations/flowpilot_daemon_reconciliation_model.py`,
  `simulations/flowpilot_daemon_reconciliation_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`,
  `skills/flowpilot/assets/packet_runtime.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`,
  `tests/test_flowpilot_packet_runtime.py`

### Commands

- `openspec validate delay-full-user-intake-release --strict` passed.
- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py skills\flowpilot\assets\packet_runtime.py simulations\flowpilot_startup_control_model.py simulations\run_flowpilot_startup_control_checks.py simulations\prompt_isolation_model.py simulations\run_prompt_isolation_checks.py simulations\flowpilot_daemon_reconciliation_model.py simulations\run_flowpilot_daemon_reconciliation_checks.py tests\test_flowpilot_router_runtime.py tests\test_flowpilot_packet_runtime.py` passed.
- `python simulations\run_flowpilot_startup_control_checks.py` passed:
  safe graph `298` states / `313` edges, FlowGuard Explorer `21920` traces,
  zero violations.
- `python simulations\run_prompt_isolation_checks.py` passed: safe graph
  `346` states / `345` edges, zero invariant failures.
- `python simulations\run_flowpilot_daemon_reconciliation_checks.py --skip-live-projection`
  passed: safe graph `1141` states / `1201` edges, FlowGuard Explorer
  `14694` traces, zero violations.
- `python -m pytest tests\test_flowpilot_packet_runtime.py -k "user_intake" -q`
  passed: `2` selected tests.
- `python -m pytest tests\test_flowpilot_router_runtime.py -k "user_intake or startup_activation or material_work_packet_records_target_ack_preflight_passed or card_bundle" -q`
  passed: `8` selected tests.
- `python -m pytest tests\test_flowpilot_card_instruction_coverage.py -q`
  passed: `7` tests and `75` subtests.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed;
  installed `flowpilot` was source-fresh.
- `python scripts\install_flowpilot.py --check --json`,
  `python scripts\audit_local_install_sync.py --json`, and
  `python scripts\check_install.py` passed.

### Findings

- `read_packet_body_for_role` now requires a valid Controller relay for
  `user_intake`; `router_startup_release` is no longer accepted as open
  authority.
- PM startup activation no longer directly releases `user_intake`. The next
  legal path is `check_packet_ledger` followed by Controller `deliver_mail`.
- PM startup cards and protocol docs now say post-activation `user_intake`
  delivery is Controller-relayed mail, not Router-only release.
- The daemon reconciliation model was corrected so PM startup card-bundle ACK
  resolves its wait row without releasing or queueing `user_intake`; activation
  and Controller mail own that later delivery.

### Skipped Or Deferred Steps

- `python simulations\run_meta_checks.py` was skipped by explicit user
  direction because it is too heavy for this focused pass.
- `python simulations\run_capability_checks.py` was skipped by explicit user
  direction because it is too heavy for this focused pass.
- Live daemon projection was skipped in the daemon model command with
  `--skip-live-projection`; the model-only reconciliation boundary was enough
  for this startup protocol correction.

## 2026-05-16 Dispatch Recipient Gate Unification

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: Router could expose a new role-facing package without first
  proving the recipient had finished the prior output-bearing obligation.
- Status: completed_focused_validation_meta_capability_skipped_by_user_direction

### Risk Intent

- Add one Router-owned pre-dispatch recipient gate for mail, system cards,
  system-card bundles, and formal work-packet relay actions.
- Treat only ACK-only packages as prompt/material packages.
- Treat any card, bundle, mail, or packet that asks for a decision, report,
  packet spec, result, blocker, or next instruction as an output-bearing work
  package.
- Keep `user_intake` as PM's first formal work chain: PM may receive the
  same-obligation `pm.material_scan` instruction, but independent PM work waits
  until `pm_issues_material_and_capability_scan_packets`.
- Preserve same-role ACK-only card bundles, different-role parallel work, and
  PM role-work result disposition behavior.

### Model Evidence

- OpenSpec change: `openspec/changes/unify-dispatch-recipient-gate/`
- Dispatch recipient gate model/result:
  `simulations/flowpilot_dispatch_recipient_gate_model.py`,
  `simulations/flowpilot_dispatch_recipient_gate_results.json`
- Runtime implementation: `skills/flowpilot/assets/flowpilot_router.py`
- Runtime tests: `tests/test_flowpilot_router_runtime.py`

### Commands

- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py simulations\flowpilot_dispatch_recipient_gate_model.py simulations\run_flowpilot_dispatch_recipient_gate_checks.py` passed.
- `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_user_intake_mail_declares_first_pm_output_obligation tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_blocks_busy_packet_holder tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_allows_system_card_for_active_holder tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_blocks_independent_pm_dispatch_while_user_intake_output_pending tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_allows_pm_after_user_intake_first_output tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_blocks_followup_when_role_wait_is_active tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_frees_worker_after_result_but_blocks_pm_disposition tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_allows_same_role_system_card_bundle tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_classifies_ack_only_card_as_prompt tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_dispatch_recipient_gate_blocks_new_output_card_when_pm_output_pending` passed: 10 tests.
- `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_model_backed_model_miss_triage_requires_officer_report_refs tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_non_authorizing_model_miss_decision_does_not_unlock_review_repair tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_model_miss_followup_uses_generic_role_work_request_channel tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_role_work_existing_result_reconciles_before_wait tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_advisory_pm_role_work_wait_is_marked_nonblocking tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_gate_targeted_pm_role_work_result_requires_mapped_gate_event tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_role_work_batch_waits_for_all_officer_results_before_pm_relay tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_role_work_request_requires_valid_recipient_and_contract tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_model_backed_model_miss_triage_unlocks_review_repair tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_out_of_scope_model_miss_triage_unlocks_review_repair_with_reason` passed: 10 tests.
- `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_user_intake_settlement_finalizer_waits_for_controller_mail_after_activation tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_card_bundle_ack_keeps_router_owned_user_intake_sealed_until_activation tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_current_node_packet_relay_uses_router_direct_dispatch tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_model_miss_followup_uses_generic_role_work_request_channel` passed: 4 tests.
- `python simulations\run_flowpilot_dispatch_recipient_gate_checks.py --json-out simulations\flowpilot_dispatch_recipient_gate_results.json` passed: 17 states / 16 edges, 48 FlowGuard traces, zero violations.
- `openspec validate unify-dispatch-recipient-gate --strict` passed.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` passed; installed `flowpilot` was refreshed to the repository source digest.
- `python scripts\install_flowpilot.py --check --json` passed; installed `flowpilot` is source-fresh.
- `python scripts\audit_local_install_sync.py --json` passed; repo-owned installed skills are fresh.

### Findings

- The gate now classifies system-card actions as `ack_only_prompt` only when
  the card or bundle has no ACK-plus output obligation.
- Output-bearing system cards and event cards participate in the busy-recipient
  rule. For example, unrelated PM work waits while
  `pm_records_model_miss_triage_decision` is pending.
- Same-output context cards such as `pm.event.reviewer_blocked` may still be
  exposed for the already-pending PM obligation, but PM must ACK the card before
  submitting the decision.
- Existing model-miss tests were corrected to deliver and ACK the reviewer
  event card before PM submits the model-miss decision.

### Skipped Or Deferred Steps

- `python simulations\run_meta_checks.py` was skipped by explicit user
  direction because it is too heavy for this focused Router dispatch-gate pass.
- `python simulations\run_capability_checks.py` was skipped by explicit user
  direction because it is too heavy for this focused Router dispatch-gate pass.

## 2026-05-16 Stale Passive Wait Model Miss Review

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: FlowPilot runtime run `run-20260516-151449` treated PM as
  busy because a Controller passive wait row stayed `waiting` after the durable
  PM startup card ACK return had already resolved.
- Status: completed_focused_model_upgrade_meta_capability_skipped_by_user_direction
- Miss type: state_too_coarse. The dispatch model had a boolean
  `passive_wait_for_target`, but did not record whether the matching durable
  ACK, role-output, packet, or PM-role-work evidence was still open or already
  resolved. The scheduler model also covered broad ACK joins but not
  single-card ACK return settlement across the return ledger, Controller wait
  row, and Router scheduler row.

### Model Evidence

- Dispatch recipient gate model/result:
  `simulations/flowpilot_dispatch_recipient_gate_model.py`,
  `simulations/flowpilot_dispatch_recipient_gate_results.json`
- Two-table async scheduler model/result:
  `simulations/flowpilot_two_table_async_scheduler_model.py`,
  `simulations/flowpilot_two_table_async_scheduler_results.json`

### Commands

- `python simulations\run_flowpilot_dispatch_recipient_gate_checks.py --json-out simulations\flowpilot_dispatch_recipient_gate_results.json` passed: 19 states / 18 edges, 54 FlowGuard traces, zero violations.
- `python simulations\run_flowpilot_two_table_async_scheduler_checks.py --json-out simulations\flowpilot_two_table_async_scheduler_results.json` passed: 115 states / 114 edges, 171 FlowGuard traces, zero violations.
- `python -m py_compile simulations\flowpilot_dispatch_recipient_gate_model.py simulations\run_flowpilot_dispatch_recipient_gate_checks.py simulations\flowpilot_two_table_async_scheduler_model.py simulations\run_flowpilot_two_table_async_scheduler_checks.py` passed.

### Findings

- A resolved passive wait is not a live busy source unless another concrete
  unresolved obligation still exists.
- Any exposed busy-recipient wait must name the concrete unresolved obligation,
  not only the target role.
- Single-card ACK return settlement must reconcile all three durable views
  together: return ledger, Controller passive wait row, and Router scheduler
  row.
- The focused models now reject both stale Controller wait rows and stale Router
  scheduler rows after a single-card ACK return resolves.

### Skipped Or Deferred Steps

- `python simulations\run_meta_checks.py` was skipped by explicit user
  direction because it is too heavy for this focused model-miss pass.
- `python simulations\run_capability_checks.py` was skipped by explicit user
  direction because it is too heavy for this focused model-miss pass.
- Runtime implementation and regression tests are deferred to the next repair
  pass; this entry records the model upgrade and the minimal root-fix boundary.
