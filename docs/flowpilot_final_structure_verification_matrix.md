# FlowPilot Final Structure Verification Matrix

Date: 2026-05-17

Use this matrix to select validation for the final structure convergence pass
and future maintenance that touches the same boundaries.

## Universal Checks

| Boundary | Required Commands |
| --- | --- |
| Any production Python change | `python -m py_compile <changed-python-files>` |
| Any OpenSpec artifact change | `openspec validate final-flowpilot-structure-convergence --strict --json` |
| Any FlowGuard model or router-protocol change | `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` |
| Any `skills/flowpilot` source change | `python scripts/install_flowpilot.py --sync-repo-owned --json`; `python scripts/install_flowpilot.py --check --json`; `python scripts/audit_local_install_sync.py --json`; `python scripts/check_install.py --json` |
| Any public package boundary change | `python scripts/check_public_release.py --json` |
| Final local repository check | `git diff --check`; `git status --short --branch` |

## Router Runtime Tests

| Touched Files | Focused Checks | Slow/Background Checks |
| --- | --- | --- |
| `tests/test_flowpilot_router_runtime.py`, `tests/router_runtime/*.py` | Router runtime inventory check proving every aggregate test is covered exactly once; focused `python -m unittest tests.router_runtime.<domain>` for migrated domains | Use `python scripts/run_test_tier.py --tier router --background --background-dir tmp/flowguard_background --json`; slow domains must write `.out.txt`, `.err.txt`, `.combined.txt`, `.exit.txt`, and `.meta.json` artifacts |

## Runtime Facades

| Touched Files | Focused Checks | Notes |
| --- | --- | --- |
| `skills/flowpilot/assets/role_output_runtime.py`, `role_output_runtime_*.py` | `python -m unittest tests.test_flowpilot_role_output_runtime`; import smoke for public facade; CLI parse smoke where practical | Preserve public imports, output keys, progress record shape, and direct-router authority validation |
| `skills/flowpilot/assets/packet_runtime.py`, `packet_runtime_*.py` | Packet runtime unit tests; import smoke for public facade; CLI parse smoke where practical | Split only when the boundary is obvious and lower risk than leaving the code in place |

## Router Production Facade

| Touched Area | Focused Checks | Risk Notes |
| --- | --- | --- |
| External event intake or reconciliation | Event contract checks; focused router runtime tests for explicit envelope, wait reconciliation, durable event writes, duplicate/idempotent submissions, and terminal finalization | High risk: ordering, durable writes, state persistence, and Router errors must stay stable. The finalization helper may move only post-side-effect common tail behavior. |
| Controller action application | Controller runtime domains and dispatch/packet/card tests for touched action families | Medium to high risk: preserve action names and role authority |
| PM role-work, bootloader, receipt reconciliation, system-card bundles, final ledger | Matching runtime domains plus closure/terminal tests where applicable | Split only behind existing public functions and helpers |

## Child FlowGuard Models

| Touched Files | Focused Checks | Result Evidence |
| --- | --- | --- |
| `simulations/flowpilot_control_plane_friction_model.py` and helpers | Focused control-plane friction check command for this model | Update or inspect the matching result JSON before claiming equivalence |
| `simulations/flowpilot_router_loop_model.py` and helpers | Focused router-loop model check command | Hazards and invariant failures must remain equivalent |
| `simulations/flowpilot_daemon_reconciliation_model.py` and helpers | Focused daemon reconciliation model check command | Known bad reconciliation hazards must still be detected |
| `simulations/flowpilot_persistent_router_daemon_model.py` and helpers | Focused persistent daemon model check command | Split only if the focused check remains practical |

The persistent daemon model is a deferred candidate for this pass. Do not split
it only to reduce line count; first identify a stable state/transition boundary
and a focused checker that proves equivalence.

## Parent Model Evidence

| Check | Command | Completion Rule |
| --- | --- | --- |
| Model hierarchy | `python simulations/run_flowpilot_model_hierarchy_checks.py` | Result JSON must be valid and current |
| Meta layered full | `python simulations/run_meta_checks.py --full` | Run through `tmp/flowguard_background/run_meta_checks.*`; inspect exit code and metadata |
| Capability layered full | `python simulations/run_capability_checks.py --full` | Run through `tmp/flowguard_background/run_capability_checks.*`; inspect exit code and metadata |

The old `--legacy-full` parent checks are compatibility oracles only. They are
not routine completion evidence for this pass unless explicitly requested.
