# FlowPilot Final Structure Convergence Baseline

Date: 2026-05-17

This note freezes the baseline for the final structure convergence pass. The
goal is to finish the remaining maintainability work after the earlier Python
structure simplification: keep public behavior stable, reduce the largest
remaining Python and test surfaces, and leave future maintenance with clear
module ownership and validation commands.

## Baseline

- Working branch: local `main` only.
- Baseline commit: `72ed21edabaa9a4d6372c07d87495d328c508532`.
- Local rollback backup: `tmp/maintenance_backup_main_20260517-122423/`.
- Existing dirty files before this pass:
  - `docs/flowguard_adoption_log.md`
  - `simulations/flowpilot_model_hierarchy_results.json`
- OpenSpec change: `final-flowpilot-structure-convergence`.
- FlowGuard decision: `use_flowguard`, mode `model_first_change`.
- FlowGuard import check: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` returned `1.0`.
- OpenSpec strict validation passed for this change before production-code
  edits.

## Remaining Hotspots

| File | Lines | Main Maintenance Concern |
| --- | ---: | --- |
| `skills/flowpilot/assets/flowpilot_router.py` | 35,828 | large compatibility facade with long event/action functions |
| `tests/test_flowpilot_router_runtime.py` | 13,979 | aggregate implementation source for 304 router runtime tests |
| `skills/flowpilot/assets/role_output_runtime.py` | 1,715 | schema, contract, progress, envelope, and CLI responsibilities share one file |
| `skills/flowpilot/assets/packet_runtime.py` | 1,364 | remaining packet CLI/audit responsibilities may still warrant a focused split |
| `simulations/flowpilot_control_plane_friction_model.py` | 4,871 | state, transition, hazard, audit, and invariant logic share one child model |
| `simulations/flowpilot_router_loop_model.py` | 2,649 | router-loop transition and hazard logic share one child model |
| `simulations/flowpilot_daemon_reconciliation_model.py` | 1,902 | daemon reconciliation transition and hazard logic share one child model |
| `simulations/flowpilot_persistent_router_daemon_model.py` | 1,769 | persistent daemon model still combines several concerns |

## Guardrails

- Preserve public imports, CLI commands, event names, persisted JSON shapes,
  output keys, packet authority, wait semantics, and role boundaries unless a
  real validation-backed bug repair is found.
- Keep compatibility facades in place. This change may move bodies behind
  existing entrypoints; it must not remove the entrypoints.
- Keep the current layered Meta and Capability `--full` checks as the
  release-grade parent evidence path. Do not run the old `--legacy-full` path
  unless it is explicitly requested.
- No remote push, tag, release, deployment, binary build, or public publication
  is part of this pass.
- Do not treat background progress logs as completion. Long checks complete
  only when stdout, stderr, combined output, exit code, metadata, and proof
  reuse evidence have been inspected.

## Required Final Evidence

At minimum, final completion must include:

- OpenSpec strict validation for active changes.
- Compile checks for all touched Python files.
- Focused unit/model checks for each touched boundary.
- Router runtime inventory proof for migrated test domains.
- Child model focused checks for any split model.
- `python simulations/run_flowpilot_model_hierarchy_checks.py`.
- Background layered `python simulations/run_meta_checks.py --full`.
- Background layered `python simulations/run_capability_checks.py --full`.
- `python scripts/install_flowpilot.py --sync-repo-owned --json`.
- `python scripts/install_flowpilot.py --check --json`.
- `python scripts/audit_local_install_sync.py --json`.
- `python scripts/check_install.py --json`.
- `python scripts/check_public_release.py --json`.
- `python scripts/smoke_autopilot.py`.
- `git diff --check`.
- Local commit on `main` after validation.

## Final Structure Outcome

- `tests/test_flowpilot_router_runtime.py` is now a 304-test compatibility
  loader; domain-owned test bodies live under `tests/router_runtime/`.
- `role_output_runtime.py` is now a public facade backed by schema, contract,
  progress, envelope, and CLI helper modules.
- `flowpilot_router.py` remains the compatibility facade. This pass moved
  additional Controller action bodies and the common external-event finalization
  tail behind focused helper modules without changing event names or persisted
  state shape.
- The control-plane friction, router-loop, and daemon reconciliation child
  FlowGuard models now delegate state, transitions, invariants, hazards, and
  audit helpers to focused modules.
- `packet_runtime.py` and `flowpilot_persistent_router_daemon_model.py` were
  intentionally not split further in this pass. The former had already reached
  a stable facade/helper shape; the latter needs a separate lower-risk model
  boundary before movement.

## Final Evidence Snapshot

- Router background suites under `tmp/flowguard_background/` passed:
  `router_startup_runtime` 80 tests, `router_foreground_controller` 66 tests,
  `router_packets_cards_ack` 68 tests, `router_route_mutation` 65 tests, and
  `router_terminal_closure` 96 tests.
- Current-code event-finalization focus checks passed for wait closure,
  already-recorded replay, startup activation, gate-decision replay, terminal
  replay, and route-mutation/final-ledger preconditions.
- Touched child model checks passed: control-plane friction 242 states / 241
  edges, router loop 175 states / 174 edges, daemon reconciliation 1141 states
  / 1201 edges.
- Model hierarchy passed with 32 registered child models and current release
  confidence.
- Layered parent regressions passed through the required background artifacts:
  `run_meta_checks` and `run_capability_checks`, both exit code 0 with no proof
  reuse.
