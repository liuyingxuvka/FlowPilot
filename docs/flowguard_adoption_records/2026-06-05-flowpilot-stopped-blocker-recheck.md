## flowpilot-stopped-blocker-recheck-reattachment

- Project: FlowGuardProjectAutopilot_20260430
- Trigger reason: User requested the planned FlowPilot stopped-blocker recovery fix completed end to end with OpenSpec and FlowGuard, installed-skill sync, and local git sync.
- Status: implemented_validated_installed_synced_local_git_pending
- Skill decision: predictive KB preflight, OpenSpec apply, FlowGuard existing-model preflight, DevelopmentProcessFlow, focused stopped-blocker model, runtime tests, install sync.
- Started: 2026-06-05T08:30:00+02:00
- Ended: 2026-06-05T10:57:01+02:00
- Commands OK: true

### Model Files
- `simulations/flowpilot_stopped_blocker_recheck_model.py`
- `simulations/run_flowpilot_stopped_blocker_recheck_checks.py`
- `simulations/flowpilot_stopped_blocker_recheck_results.json`
- `docs/flowguard_project_topology.json`
- `docs/flowguard_project_topology.md`

### Runtime And Prompt Files
- `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- `skills/flowpilot/assets/flowpilot_new.py`
- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_resume_decision.md`

### Findings
- Added `resolve-stopped-blocker --resolution reattach_required_recheck --user-requested`.
- `stop_for_user` now preserves `pm_stop_previous_status` so a PM-stopped target can be restored before recheck.
- Reattachment moves stopped blockers to `awaiting_recheck`, issues fresh FlowGuard or Reviewer packets, and does not clear the blocker directly.
- Review blockers with `blocker_class=flowguard_failure` freshen FlowGuard first; the fresh FlowGuard pass opens a fresh Reviewer packet tied to the same blocker.
- Break-glass and PM resume guidance now route repaired stopped blockers through the formal recheck command instead of direct clear or PM loops.
- Installed FlowPilot skill digest matches repository source after sync.

### Counterexamples
- Reattachment without `--user-requested` is rejected and leaves the blocker stopped.
- Break-glass repair cannot directly mark the blocker cleared.
- Old accepted FlowGuard/Reviewer packets are not reused for reattachment.
- PM repair-decision reissue remains a separate explicit user-requested path and is not ordinary resume behavior.

### Commands
- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned schema `1.0`.
- OK: `python -m flowguard project-audit --root .`.
- OK: `openspec validate reattach-stopped-blocker-recheck --strict`.
- OK: `python simulations/run_flowpilot_stopped_blocker_recheck_checks.py`.
- OK: `python -m py_compile` for touched runtime, CLI, model, runner, and tests.
- OK: `python -m pytest tests/test_flowpilot_core_runtime.py tests/test_flowpilot_new_entrypoint.py -q` returned `64 passed, 35 subtests passed`.
- OK: `python scripts/flowguard_project_topology.py build`.
- OK: `python scripts/flowguard_project_topology.py check`.
- OK: `python simulations/run_meta_checks.py --full --json-out tmp/flowguard_background/run_meta_checks_stopped_blocker_full.json --proof-out tmp/flowguard_background/run_meta_checks_stopped_blocker_full.proof.json --thin-json-out tmp/flowguard_background/run_meta_checks_stopped_blocker_full_thin.json --thin-proof-out tmp/flowguard_background/run_meta_checks_stopped_blocker_full_thin.proof.json`.
- OK: `python simulations/run_capability_checks.py --full --json-out tmp/flowguard_background/run_capability_checks_stopped_blocker_full.json --proof-out tmp/flowguard_background/run_capability_checks_stopped_blocker_full.proof.json --thin-json-out tmp/flowguard_background/run_capability_checks_stopped_blocker_full_thin.json --thin-proof-out tmp/flowguard_background/run_capability_checks_stopped_blocker_full_thin.proof.json`.
- OK: `python scripts/install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts/audit_local_install_sync.py --json`.
- OK: `python scripts/install_flowpilot.py --check --json`.
- OK: `python scripts/check_install.py --json`.

### Skipped Steps
- No compatibility parser, old-router fallback, old packet-shape fallback, or broad schema migration was added.
- No GitHub push, tag, release, deploy, or public publication was performed.

### Next Actions
- Commit the scoped local changes without staging unrelated peer-agent work.
- Archive the OpenSpec change after maintainer review if this behavior is accepted.
