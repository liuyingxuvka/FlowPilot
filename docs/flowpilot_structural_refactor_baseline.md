# FlowPilot Structural Refactor Baseline

Date: 2026-05-17

This note freezes the baseline for the behavior-preserving structure reduction
pass. The goal is structure only: no new features, no protocol semantics
changes, no persisted JSON shape changes, and no release/publish/deploy action.

## Baseline

- Branch: `codex/behavior-preserving-structural-refactor`
- Baseline commit: `2215a65cc8a293ae24684e9d9b32d486c9cf32fd`
- Baseline version: `0.9.6`
- Rollback strategy: use the baseline commit and branch history as the
  authoritative backup for `skills/flowpilot/assets/flowpilot_router.py`.
  A tracked duplicate of the 39k-line router is intentionally not added.
- Peer coordination: no `CODEX_COORD_DIR`, `docs/coordination.md`, or
  `.codex/coord/` protocol was present; the work starts from a clean git
  status after the prior `pre-release-repair-privacy-sync` change completed.

## Baseline Validation

- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
  returned `1.0`.
- OK: `python scripts\check_install.py --json`.
- OK: `python -m unittest tests.test_flowpilot_router_runtime_controller tests.test_flowpilot_router_runtime_ack_return tests.test_flowpilot_router_runtime_closure tests.test_flowpilot_user_flow_diagram`.
  The baseline focused suite ran 44 tests.

## Structural Audit

| File | Lines | Largest Function |
| --- | ---: | --- |
| `skills/flowpilot/assets/flowpilot_router.py` | 39,028 | `_record_external_event_unchecked` at 865 lines |
| `tests/test_flowpilot_router_runtime.py` | 15,226 | `test_resume_reentry_loads_state_before_resume_cards` at 187 lines |
| `simulations/meta_model.py` | 7,053 | `apply` at 3,751 lines |
| `simulations/capability_model.py` | 8,123 | `apply` at 3,766 lines |
| `scripts/check_install.py` | 1,633 | `main` at 1,069 lines |

## Router Hotspots

- `skills/flowpilot/assets/flowpilot_router.py:36742`
  `_record_external_event_unchecked` mixes event validation, preconsumption,
  payload normalization, idempotency, event writes, flag updates, and state
  persistence.
- `skills/flowpilot/assets/flowpilot_router.py:35623`
  `compute_controller_action` scans multiple action sources in a fixed priority
  order.
- `skills/flowpilot/assets/flowpilot_router.py:36091`
  `apply_controller_action` applies many action types behind one large branch.
- `skills/flowpilot/assets/flowpilot_router.py:29302`
  `_write_route_mutation` is the current route-domain extraction anchor.

## Event Areas

- Heartbeat/manual resume: `heartbeat_or_manual_resume_requested`.
- Stop/cancel: startup cancellation and controlled terminal stop flows.
- Heartbeat binding: `host_records_heartbeat_binding`.
- Route activation: `pm_activates_reviewed_route`.
- Route mutation: PM repair/replacement route mutation and recheck flows.
- Card/ACK: card ACK, bundle ACK, pending return ledger, and settlement
  finalizers.

## Current Focused Test Entrypoints

- `tests.test_flowpilot_router_runtime_controller`
- `tests.test_flowpilot_router_runtime_ack_return`
- `tests.test_flowpilot_router_runtime_closure`
- `tests.test_flowpilot_router_runtime_dispatch_gate`
- `tests.test_flowpilot_router_runtime_startup_daemon`
- `tests.test_flowpilot_router_runtime_terminal`
- `tests.test_flowpilot_router_startup_runtime`
- `tests.test_flowpilot_user_flow_diagram`
- Selected methods from `tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests`
  for route activation, route mutation, resume, cards, startup, and closure.

## Required Validation Commands

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
openspec validate behavior-preserving-router-structure-reduction --strict --json
python simulations\run_flowpilot_structural_refactor_checks.py
python -m py_compile <changed-python-files>
python -m unittest tests.test_flowpilot_router_runtime_controller tests.test_flowpilot_router_runtime_ack_return tests.test_flowpilot_router_runtime_closure tests.test_flowpilot_user_flow_diagram
python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_requires_topology_and_resets_route_hard_gates tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_and_final_ledger_have_required_preconditions tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof
python scripts\check_install.py --json
python scripts\check_public_release.py --json
python scripts\install_flowpilot.py --sync-repo-owned --json
python scripts\audit_local_install_sync.py --json
```

Heavy model checks, when their files are touched:

```powershell
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

For long-running execution, use the repository background log contract under
`tmp/flowguard_background/` and inspect stdout, stderr, combined, exit, and
metadata artifacts before claiming completion.
