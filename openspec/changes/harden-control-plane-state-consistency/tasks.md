## 1. OpenSpec And FlowGuard

- [x] 1.1 Add OpenSpec proposal, design, specs, and tasks for control-plane state consistency.
- [x] 1.2 Validate the OpenSpec change strictly.
- [x] 1.3 Keep the new control-plane state consistency FlowGuard model green and use its repair-candidate result as the implementation boundary.

## 2. Runtime Tests First

- [x] 2.1 Add focused coverage for material scan result receipt folding advancing durable batch lifecycle and Router projection.
- [x] 2.2 Add focused coverage for PM role-work supersession terminalizing old requests and removing them from active busy indexes.
- [x] 2.3 Add focused coverage for dispatch gate allowing a replacement when the old request is unrelayed/Controller-held but still blocking truly target-held work.
- [x] 2.4 Add focused coverage for stale daemon snapshot save preserving newer foreground evidence.
- [x] 2.5 Add focused coverage for wait reminder durable cooldown dedupe.
- [x] 2.6 Add focused coverage for `# Contract Self-Check` result body sections projecting into envelope metadata.

## 3. Production Repair

- [x] 3.1 Implement lifecycle-aware Controller receipt folds for packet/result relay actions that update durable batch state and Router projections.
- [x] 3.2 Implement PM role-work supersession terminalization and replacement metadata propagation.
- [x] 3.3 Implement true-holder dispatch recipient busy classification for PM role-work requests.
- [x] 3.4 Implement freshness-aware Router state save/merge behavior for daemon and foreground interleavings.
- [x] 3.5 Implement stable wait reminder cooldown recovery from durable records.
- [x] 3.6 Implement compatible packet result self-check heading parsing.

## 4. Verification

- [x] 4.1 Run focused unit/runtime tests for the touched boundaries.
- [x] 4.2 Run focused FlowGuard checks: control-plane state consistency, controller receipt evidence fold, dispatch recipient gate, daemon reconciliation, and persistent router daemon where applicable.
  - Note: daemon reconciliation passed in model-only mode with `--skip-live-projection`; the non-skipped live-run audit fails on an existing `.flowpilot` run projection gap. `run_flowpilot_persistent_router_daemon_checks.py` was attempted and timed out after 7 minutes, so it is not counted as passed evidence.
- [x] 4.3 Run background meta and capability regressions using `tmp/flowguard_background/` artifacts and inspect final exit/status/proof metadata.

## 5. Sync And Git

- [x] 5.1 Sync repo-owned FlowPilot assets into the local installed skill.
- [x] 5.2 Run install audit/check and verify source freshness.
- [x] 5.3 Review local git state, preserve unrelated peer edits, and create local git version evidence if requested by the user.
