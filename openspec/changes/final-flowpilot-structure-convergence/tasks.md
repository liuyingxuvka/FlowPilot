## 0. Baseline And Coordination

- [x] 0.1 Record current `main`, dirty worktree context, backup path, and file-size hotspot baseline.
- [x] 0.2 Verify FlowGuard import and OpenSpec status before production-code edits.
- [x] 0.3 Add or update a structure-convergence baseline note and verification matrix skeleton.
- [x] 0.4 Validate this OpenSpec change strictly before behavior-bearing edits.

## 1. Router Runtime Test Implementation Split

- [x] 1.1 Move aggregate router runtime test helpers into `tests/router_runtime/common.py`.
- [x] 1.2 Move startup/bootstrap/foreground/controller test implementations into domain modules.
- [x] 1.3 Move packet/ACK/dispatch/control-blocker/material/quality test implementations into domain modules.
- [x] 1.4 Move route-mutation/resume/terminal/closure/card test implementations into domain modules.
- [x] 1.5 Preserve aggregate compatibility loading and prove all 304 tests are covered exactly once.
- [x] 1.6 Run focused fast domains plus slow packet/route-mutation domains through background evidence.

## 2. Runtime Facade Convergence

- [x] 2.1 Split `role_output_runtime.py` schema/contract/progress/envelope/CLI helpers behind the existing facade.
- [x] 2.2 Split remaining `packet_runtime.py` CLI/audit/controller-handoff helpers if they still materially improve readability.
  - `packet_runtime.py` was left as the existing public facade because the earlier helper split already created stable boundaries; no additional low-risk split was found.
- [x] 2.3 Preserve public imports and CLI behavior for packet and role-output runtimes.
- [x] 2.4 Run role-output, packet-runtime, output-contract, install, and CLI parse checks.

## 3. Router Facade Hotspot Convergence

- [x] 3.1 Split external event commit/reconciliation tail helpers from `_record_external_event_unchecked`.
- [x] 3.2 Split controller action application helpers from `apply_controller_action`.
- [x] 3.3 Split PM role-work, bootloader, system-card bundle, receipt reconciliation, and final-ledger helpers where the boundary is stable.
  - Additional PM role-work, bootloader, receipt reconciliation, system-card bundle, and final-ledger splits were intentionally deferred because the remaining candidates are state-ordering sensitive and need separate focused models before movement.
- [x] 3.4 Preserve event names, state shape, wait semantics, packet authority, and controller/PM/reviewer role boundaries.
- [x] 3.5 Run router focused domains for every touched boundary.

## 4. Child FlowGuard Model Convergence

- [x] 4.1 Split `flowpilot_control_plane_friction_model.py` into state/transition/hazard/audit/invariant modules.
- [x] 4.2 Split `flowpilot_router_loop_model.py` into state/transition/hazard/invariant modules.
- [x] 4.3 Split `flowpilot_daemon_reconciliation_model.py` and `flowpilot_persistent_router_daemon_model.py` where practical.
  - `flowpilot_daemon_reconciliation_model.py` was split. `flowpilot_persistent_router_daemon_model.py` remains deferred until a stable focused split boundary is identified.
- [x] 4.4 Split additional 1k+ child models only when the split has a clear ownership boundary and focused check.
- [x] 4.5 Run each touched child model check and update result JSON.

## 5. Verification Matrix And Documentation

- [x] 5.1 Create or update a verification matrix mapping touched files to focused commands and slow background commands.
- [x] 5.2 Update HANDOFF, README, FlowGuard adoption log, and baseline notes with the final structure and validation evidence.
- [x] 5.3 Record any behavior bug found during simplification with matching model/test evidence.
  - No new behavior bug was found during this final pass. The earlier explicit event-envelope repair remains documented with model/test evidence.

## 6. Final Validation And Sync

- [x] 6.1 Run compile checks for touched Python files.
- [x] 6.2 Run OpenSpec strict validation for active changes.
- [x] 6.3 Run focused unit/model checks and slow background checks required by the verification matrix.
- [x] 6.4 Run model hierarchy and layered Meta/Capability `--full` checks through background artifacts.
- [x] 6.5 Run install sync, install check, local install freshness audit, smoke, public-boundary/privacy checks, and `git diff --check`.
- [x] 6.6 Run KB postflight and record reusable maintenance lessons.
- [x] 6.7 Commit the validated result on local `main` with no extra local work branches.
