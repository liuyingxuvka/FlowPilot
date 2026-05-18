# FlowPilot Full Model-Test-Code Diagnostics

Date: 2026-05-18

This report summarizes the current full diagnostic layer emitted by:

```powershell
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
```

The original eight family alignment plans are green, and the source-contract
subset is green. The full diagnostic layer is deliberately stricter: it
inventories the wider repository and reports every surface that lacks an
explicit model-code-test binding. Therefore:

- `full_diagnostic_ok`: true. The diagnostic machinery and known-bad sanity
  checks are working.
- `full_coverage_ok`: false. The repository does not yet have full
  model-test-code coverage.

## Current Counts

| Metric | Count |
| --- | ---: |
| Total diagnostic surfaces | 454 |
| Covered surfaces | 15 |
| Surfaces with one or more gaps | 439 |
| Compatibility facades | 59 |
| Owner modules | 111 |
| Script entrypoints | 17 |
| Model-check runners | 82 |
| Test tiers | 12 |
| Test tier commands | 173 |

## Gap Counts

| Gap code | Count | Meaning |
| --- | ---: | --- |
| `missing_test` | 211 | No ordinary test evidence was found for the surface. |
| `internal_only_test` | 224 | There is test/model mention evidence, but no source-level external contract binding. |
| `missing_model` | 72 | Code exists without a current model obligation binding. |
| `extra_code` | 72 | Code exists outside the current accepted model/test map. |
| `needs_structure_split` | 55 | Module or script is above the diagnostic split threshold. |
| `stale_evidence` | 9 | Long/background evidence is not final pass evidence in this diagnostic view. |

## High-Value Findings

The diagnostic does not show broken imports in the checked facade export
registry. The dominant problem is coverage accounting: many surfaces exist and
may be tested indirectly, but they are not yet bound to explicit model
obligations and source-level external-contract tests.

Priority gaps:

- `packet_runtime.py` is a public compatibility facade; child owners are
  represented in structure evidence, but the facade import/export contract is
  under-modeled in the full model-test-code map.
- `flowpilot_router_controller_scheduler_receipts.py` and
  `flowpilot_router_work_packets_pm_role.py` now have direct facade parity
  tests, but still need source-contract rows for the behavior they re-export.
- Terminal closure and runtime closure surfaces have tests and code, but not
  enough source-contract binding for closure-suite writes and dirty-ledger
  blocking.
- Daemon lock/status/queue ownership has model-test evidence, but lacks direct
  source-contract rows for daemon lock acquisition and status writes.
- Test-tier background machinery is partly modeled through `commands_for_tier`,
  but artifact path creation, supervisor behavior, child runner behavior, and
  background `main()` behavior remain weaker than the command registry binding.
- Many `simulations/run_*checks.py` runners are executable model evidence but
  are not represented by ordinary tests in the full diagnostic corpus.

## Representative Missing-Model / Extra-Code Surfaces

- `skills/flowpilot/assets/flowpilot_router_action_handlers.py`
- `skills/flowpilot/assets/flowpilot_router_action_handlers_packets.py`
- `skills/flowpilot/assets/flowpilot_router_controller_repair_deliverables.py`
- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_ledgers.py`
- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_standby.py`
- `skills/flowpilot/assets/flowpilot_router_events_repair_model_gate.py`
- `skills/flowpilot/assets/flowpilot_router_protocol_boot_cards.py`
- `skills/flowpilot/assets/flowpilot_router_protocol_decision_tables.py`
- `skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture.py`
- `skills/flowpilot/assets/flowpilot_router_route_artifacts_nodes.py`

## Representative Missing-Test Surfaces

- `scripts/audit_local_install_sync.py`
- `scripts/check_install.py`
- `scripts/check_runtime_card_capability_reminders.py`
- `scripts/flowpilot_lifecycle.py`
- `scripts/flowpilot_outputs.py`
- `scripts/flowpilot_packets.py`
- `skills/flowpilot/assets/flowpilot_router_facade_export_manifest.py`
- `skills/flowpilot/assets/flowpilot_router_action_factory.py`

## Representative Internal-Only Test Surfaces

- `skills/flowpilot/assets/card_runtime.py`
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/flowpilot_runtime.py`
- `skills/flowpilot/assets/packet_runtime.py`
- `skills/flowpilot/assets/role_output_runtime.py`
- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts.py`
- `skills/flowpilot/assets/flowpilot_router_work_packets_pm_role.py`
- `simulations/run_meta_checks.py`
- `simulations/run_capability_checks.py`
- `simulations/run_flowpilot_test_tiering_checks.py`
- `simulations/run_flowpilot_slow_test_contract_checks.py`

## Representative Structure-Split Candidates

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/flowpilot_router_protocol_boot_cards.py`
- `skills/flowpilot/assets/flowpilot_router_protocol_decision_tables.py`
- `skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture.py`
- `skills/flowpilot/assets/flowpilot_router_route_artifacts_nodes.py`
- `skills/flowpilot/assets/flowpilot_router_route_frontier_policy.py`
- `skills/flowpilot/assets/flowpilot_router_work_packets_current_node.py`
- `skills/flowpilot/assets/flowpilot_router_card_returns.py`
- `skills/flowpilot/assets/role_output_runtime_schema.py`

## Stale Or Incomplete Background Evidence Surfaces

These entries require complete background artifacts before they can support a
release-quality evidence claim:

- `tier-command:release:meta_full`
- `tier-command:release:capability_full`
- `tier-command:release:public_release_check`
- `tier-command:legacy-full:meta_legacy_full`
- `tier-command:legacy-full:capability_legacy_full`
- `tier-command:integration:flowguard_coverage_sweep`
- `tier-command:integration:smoke_autopilot_fast`

## Next Repair Order

1. Add source-contract rows and direct parity tests for the new receipts and PM
   role-work facades.
2. Add source-contract rows for `packet_runtime.py`, terminal closure, and
   daemon lock/status/queue ownership.
3. Bind `run_test_tier.py` background artifact/supervisor surfaces beyond
   `commands_for_tier`.
4. Convert high-value model-check runners from internal-only evidence to
   external-contract tests where the runner is public release evidence.
5. Let the ongoing owner-module polish finish before splitting broad modules
   that are already being actively edited by parallel agents.
