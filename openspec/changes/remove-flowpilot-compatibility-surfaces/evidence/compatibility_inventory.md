# Compatibility Inventory

Generated during implementation of `remove-flowpilot-compatibility-surfaces`.

## Counts

- Search across active FlowPilot source, scripts, tests, simulations, docs, and
  OpenSpec specs found 447 files with compatibility-related markers.
- Current model-test alignment evidence reports 112 `compatibility_facade`
  surfaces and 5 deferred structure split findings.
- The new focused FlowGuard model
  `simulations/flowpilot_new_only_runtime_model.py` passes:
  `python simulations/run_new_only_runtime_checks.py`.

## Active Runtime Buckets

- Startup aliases:
  - `skills/flowpilot/SKILL.md`
  - `skills/flowpilot/assets/flowpilot_router_cli.py`
  - `scripts/install_checks/runtime.py`
- Legacy startup and old layout helpers:
  - `skills/flowpilot/assets/flowpilot_paths.py`
  - `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled_policy.py`
  - `skills/flowpilot/assets/packet_runtime_creation_startup.py`
- Event aliases and compatibility artifacts:
  - `skills/flowpilot/assets/flowpilot_router_protocol_external_event_data_route.py`
  - `skills/flowpilot/assets/flowpilot_router_protocol_external_event_data_material.py`
  - `skills/flowpilot/assets/runtime_kit/router_facade_owner_exports.json`
- Runtime schema and transaction aliases:
  - `skills/flowpilot/assets/runtime_kit/contracts/contract_index.json`
  - `skills/flowpilot/assets/runtime_kit/control_transaction_registry.json`
  - `skills/flowpilot/assets/role_output_runtime_schema_specs.py`
- Migration/recovery helpers:
  - `skills/flowpilot/assets/flowpilot_router_terminal_ledger_recovery.py`
  - `skills/flowpilot/assets/flowpilot_runtime_closure.py`
  - `skills/flowpilot/assets/flowpilot_router_startup_role_transactions_records.py`
- Prompt/card surfaces:
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/dispatch_request.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/current_node_dispatch.md`
  - `skills/flowpilot/assets/runtime_kit/cards/officers/route_process_check.md`
  - `skills/flowpilot/assets/runtime_kit/cards/officers/route_product_check.md`
  - `skills/flowpilot/assets/runtime_kit/cards/officers/product_architecture_modelability.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md`
- Install and validation gates:
  - `scripts/install_checks/common.py`
  - `scripts/install_checks/docs.py`
  - `scripts/install_checks/runtime.py`
  - `scripts/test_tier/integration_commands.py`
  - `scripts/test_tier/router_startup_foreground_commands.py`
  - `scripts/test_tier/router_terminal_commands.py`

## Classification

- Delete or reject: fresh-invocation aliases, legacy startup payloads, legacy
  officer/reviewer event aliases, output-type aliases, deprecated repair
  aliases, legacy migration helpers, and compatibility prompt instructions.
- Remove from current gates: legacy equivalence docs, barrier equivalence
  checks, legacy prompt matrix checks, and legacy-full monolithic runners.
- Preserve as current safety: prior/superseded authority quarantine, stale
  evidence rejection, and active-writer isolation. These can be renamed or
  reworded but must not be deleted as compatibility.
- StructureMesh staged contraction: public facade exports that exist only for
  old import paths. These require import-site checks before deletion.
