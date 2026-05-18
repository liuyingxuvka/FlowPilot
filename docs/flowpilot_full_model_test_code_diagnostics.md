# FlowPilot Full Model-Test-Code Diagnostics

Date: 2026-05-18

This report summarizes the full diagnostic layer emitted by:

```powershell
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
```

The original eight family alignment plans and the AST-supported source-contract
subset are green. The full diagnostic layer is stricter: it inventories wider
repository surfaces and reports missing model, code, test, external-contract,
background-evidence, and structure-split repair work.

- `full_diagnostic_ok`: true. The diagnostic machinery and known-bad sanity
  checks are working.
- `full_coverage_ok`: false. The repository still has model-test-code coverage
  gaps, now ranked by repair priority.

## Current Counts

| Metric | Count |
| --- | ---: |
| Total diagnostic surfaces | 459 |
| Covered surfaces | 27 |
| Surfaces with one or more gaps | 432 |
| Compatibility facades | 60 |
| Owner modules | 113 |
| Script entrypoints | 17 |
| Model-check runners | 82 |
| Test tiers | 12 |
| Test tier commands | 175 |

## Gap Counts

| Gap code | Count | Meaning |
| --- | ---: | --- |
| `internal_only_test` | 226 | There is test/model mention evidence, but no source-level external contract binding. |
| `missing_test` | 198 | No ordinary test evidence was found for the surface. |
| `missing_model` | 72 | Code exists without a current model obligation binding. |
| `extra_code` | 72 | Code exists outside the current accepted model/test map. |
| `needs_structure_split` | 54 | Module or script is above the diagnostic split threshold. |
| `stale_evidence` | 3 | Background evidence is failed, stale, incomplete, progress-only, or local-only release proof. |

## Triage Fields

Every finding now includes:

- `severity`: `critical`, `high`, `medium`, or `low`.
- `surface_owner`: the owner module, script, model runner, or test tier.
- `release_relevance`: `release_gate`, `validation_gate`, `runtime_contract`,
  `public_cli`, `legacy_validation`, or maintenance-only categories.
- `repair_type`: the concrete repair class, such as
  `add_external_contract_test`, `defer_structure_split`, or
  `rerun_public_release_evidence`.
- `dedupe_key`: a stable grouping key for repeated findings with the same
  owner and repair type.
- `priority_score`: lower values are repaired first.

Aggregate counts in the JSON include:

- `gap_counts_by_severity`: `critical=1`, `high=185`, `medium=367`, `low=72`.
- `gap_counts_by_repair_type`: `add_external_contract_test=198`,
  `upgrade_to_external_contract_test=226`, `add_model_binding=72`,
  `classify_or_remove_code=72`, `split_structure=43`,
  `defer_structure_split=11`, `fix_failing_background_evidence=2`,
  `rerun_public_release_evidence=1`.
- `gap_counts_by_release_relevance`: `runtime_contract=326`,
  `release_gate=180`, `validation_gate=88`, `public_cli=27`,
  `legacy_validation=4`.

## Top Repair Items

The current highest-priority actionable summary is:

1. `test-tier:release`: `public_release_check` is classified as
   `release_local_only` because URL checks were skipped; this is local proof,
   not public release proof.
2. `test-tier:integration` and `smoke_autopilot_fast`: add external-contract
   test coverage for the integration tier and smoke command surfaces.
3. Model-check runners such as `run_barrier_equivalence_checks.py`,
   `run_card_instruction_coverage_checks.py`, and
   `run_command_refinement_checks.py`: add fast public runner contract tests
   if they are to count as ordinary external evidence.
4. Release scripts `check_public_release.py` and `install_flowpilot.py`: they
   now have CLI smoke tests, but still need explicit model bindings before the
   full diagnostic can call them fully covered release gates.
5. `test-tier:legacy-full`: two legacy full-model background artifacts are
   still visible as failed legacy-validation history, but old legacy full-model
   checks are not ranked as current release gates.

## Newly Strengthened Contract Coverage

This pass added or recognized external-contract evidence for:

- `packet_runtime.py` facade export parity, including schema constants,
  identity markers, `load_envelope`, direct-relay validation, reviewer relay
  validation, and startup-release verification exports.
- `flowpilot_router_controller_scheduler_receipts.py` facade parity.
- `flowpilot_router_work_packets_pm_role.py` facade parity.
- `flowpilot_router_terminal_ledger.py` facade parity through the router
  compatibility facade.
- `flowpilot_runtime_closure.py` officer lifecycle, continuation quarantine,
  final user report, and route display refresh record contracts.
- `flowpilot_router_daemon_runtime.py` daemon run/stop, lock acquire/refresh/
  release, status write, and tick contracts.
- `flowpilot_router_startup_daemon.py` daemon lock liveness and heartbeat
  monitor helpers.
- CLI entrypoint behavior for install, sync audit, public release audit,
  test-tier list/dry-run, lifecycle scan, packet parser, and role-output
  parser surfaces.

## Background Evidence Policy

Background evidence is now classified from final artifacts rather than progress
text. The classifier reads `.meta.json` with `utf-8-sig` and distinguishes:

- `passed`
- `failed`
- `running`
- `incomplete`
- `stale`
- `progress_only`
- `release_local_only`

Progress-only evidence is never a pass. Release validation with
`--skip-url-check` is explicitly local-only proof.

## Structure-Split Repair Planning

The diagnostic records concrete deferred split metadata for 11 currently broad
surfaces. Broad stateful surfaces are deferred because they overlap recent
owner-module polish and need a claimed StructureMesh target before editing:

- `flowpilot_router_work_packets_current_node.py`
- `flowpilot_router_card_returns.py`
- `role_output_runtime_schema.py`
- route artifact/frontier state shards

Declarative surfaces are safer follow-up candidates after an explicit claim:

- `flowpilot_router_facade_export_manifest_controller.py`
- `flowpilot_router_protocol_boot_cards.py`
- `flowpilot_router_protocol_decision_tables.py`

Each deferred row includes `split_status`, `split_reason`,
`deferred_split_reason`, `peer_safety_status`, `recent_owner_context`,
`safe_split_class`, and `recommended_next_action`.
