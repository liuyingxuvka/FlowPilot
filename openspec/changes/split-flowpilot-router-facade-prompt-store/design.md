## Boundary

The public entrypoint remains:

- `skills/flowpilot/assets/flowpilot_router.py`
- `python skills/flowpilot/assets/flowpilot_router.py ...`

The facade may keep public CLI parsing, public helper wrappers, shared path
helpers, and orchestration glue. Behavior-bearing clusters should move behind
domain modules only when their state owner, side effects, and tests are clear.

## Target Module Map

First target shape:

| Module | Owns |
| --- | --- |
| `flowpilot_prompt_store.py` | Prompt manifest loading, template rendering, prompt hash validation, missing-prompt errors. |
| `runtime_kit/prompts/` | Versioned prompt/control text assets. |
| `flowpilot_router_prompt_delivery.py` | Prompt/card delivery action construction and prompt-check actions. |
| `flowpilot_router_card_returns.py` | Card ACK return settlement and finalizers. |
| `flowpilot_router_controller_ledger.py` | Controller action ledger rows, receipts, reconciliation, standby snapshots. |
| `flowpilot_router_daemon_runtime.py` | Daemon loop, lock/status records, bounded background fanout. |
| `flowpilot_router_bootloader.py` | Bootloader action application and startup shell setup. |
| `flowpilot_router_startup.py` | Startup intake, startup activation, heartbeat binding. |
| `flowpilot_router_event_identity.py` | Event idempotency keys, entrypoint normalization, identity projections. |
| `flowpilot_router_event_dispatcher.py` | External event dispatch families and wait-action settlement. |
| `flowpilot_router_control_blockers.py` | Control blocker records and blocker policy transitions. |
| `flowpilot_router_repair_transactions.py` | Repair transaction writes, route-mutation recheck guards, stale-evidence ledgers. |
| `flowpilot_router_pm_role_work.py` | PM role-work requests, packet relay, result relay, absorption decisions. |
| `flowpilot_router_packet_dispatch.py` | Current-node packet/result dispatch, active-holder packet mechanics. |
| `flowpilot_router_route_frontier.py` | Route activation, execution frontier, current-node progression. |
| `flowpilot_router_terminal_ledger.py` | Final route-wide ledgers, terminal closure, backward replay. |
| `flowpilot_router_validation.py` | Artifact validation, manifest checks, local runtime audits. |
| `flowpilot_router_legacy_repair.py` | Compatibility-only legacy repair helpers that cannot yet be deleted. |

This map is a final target, not a requirement to move all code in one commit.
The first implementation wave must establish the split pattern and validation
gates without destabilizing runtime behavior.

## Split Order

1. PromptStore and prompt-delivery boundary, because prompt text is low-level
   data and already belongs in the runtime kit.
2. Card-return settlement and card-delivery finalizers, because they form a
   compact ACK protocol boundary.
3. Controller ledger and daemon runtime, because they are the main foreground
   disturbance and background-test boundary.
4. Startup/bootloader, external events, control blockers, repair transactions,
   PM role-work, route frontier, and terminal ledgers in focused waves.

## Coarse Facade Convergence Target

The remaining waves SHALL prioritize coarse phase ownership over small helper
extraction. The router facade is not considered converged while the main
phase controllers still live in `flowpilot_router.py`.

The next implementation target is:

| Coarse owner | Owns |
| --- | --- |
| `flowpilot_router_runtime_state.py` | Run/bootstrap state shape, state IO, runtime packet/frontier/role-memory factories, and continuation/quarantine state records. |
| `flowpilot_router_startup_flow.py` | Bootloader action selection/application, startup intake, startup answer validation, startup display/audit/fact/activation/repair flows, and resume/role-recovery startup actions. |
| `flowpilot_router_controller_scheduler.py` | Controller action ledger orchestration, receipts, scheduler reconciliation, wait reminders, foreground standby, patrol timer, and controller action application. |
| `flowpilot_router_work_packets.py` | Material/research/current-node packet dispatch, PM role-work request/result/decision lifecycle, packet batch refresh, and packet-group reviewer validation. |
| `flowpilot_router_events_repair.py` | Control-blocker classification/materialization/resolution, repair transaction planning/finalization, gate-decision validation, and repair outcome settlement. |
| `flowpilot_router_event_dispatcher.py` | External event dispatch orchestration and event wait-action settlement while delegating domain-specific side effects to their owners. |
| `flowpilot_router_route_frontier.py` | Route/frontier helpers, legal route action checks, route state snapshots, and node completion. |
| `flowpilot_router_terminal_ledger.py` | Final route-wide ledger, terminal backward replay, terminal closure suite, and terminal reconciliation. |

The facade may keep compatibility wrappers for existing test-facing names, but
wrapper bodies should delegate to a coarse owner. Repeated small extractions
that leave the phase controller body in the facade do not satisfy this target.

## FlowGuard Evidence

The split model treats each function block as:

`Input x State -> Set(Output x State)`

For this maintenance pass, the executable model must reject:

- a facade that no longer exposes public imports or CLI;
- a facade that still owns the major startup, controller, work-packet,
  external-event/repair, or route/terminal phase controller bodies after the
  coarse split claims completion;
- two modules claiming the same state owner;
- a partition without an owner module;
- hundreds of one-function micro-modules;
- prompt delivery that references a missing asset;
- prompt rendering that falls back to stale inline text;
- prompt hashes that do not match the stored asset;
- a prompt asset that is not included in install checks;
- background validation that has progress output but no final exit/meta
  artifact.

## Validation

Focused validation:

```powershell
openspec validate split-flowpilot-router-facade-prompt-store --strict
python simulations/run_flowpilot_router_facade_split_checks.py --json-out simulations/flowpilot_router_facade_split_results.json
python -m pytest tests/test_flowpilot_prompt_store.py -q
python -m pytest tests/test_flowpilot_test_tiers.py -q
python simulations/run_flowpilot_structure_maintenance_checks.py --json-out simulations/flowpilot_structure_maintenance_results.json
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
```

Long validation should use hidden/background process artifacts under
`tmp/flowguard_background/`, then inspect `.exit.txt` and `.meta.json` before
claiming completion.
