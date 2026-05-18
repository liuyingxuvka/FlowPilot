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
| Total diagnostic surfaces | 527 |
| Covered surfaces | 384 |
| Surfaces with one or more gaps | 143 |
| Compatibility facades | 60 |
| Owner modules | 113 |
| Script entrypoints | 17 |
| Model-check runners | 82 |
| Test tiers | 15 |
| Test tier commands | 240 |

## Gap Counts

| Gap code | Count | Meaning |
| --- | ---: | --- |
| `missing_test` | 78 | No ordinary external-contract test evidence was found for the surface. |
| `needs_structure_split` | 54 | Module or script is above the diagnostic split threshold. |
| `internal_only_test` | 25 | There is test/model mention evidence, but no source-level external contract binding. |
| `stale_evidence` | 3 | Background evidence is failed, stale, incomplete, progress-only, or local-only release proof. |

This burn-down pass intentionally reduced `missing_model` and `extra_code` to
zero by binding intentional owner modules, facades, scripts, and model-check
runners to diagnostic model categories. It also reduced release/validation gate
`missing_test` and `internal_only_test` findings to zero through aggregate
external-contract tests for model-check runners and test-tier commands.

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

- `gap_counts_by_severity`: `critical=1`, `high=25`, `medium=134`.
- `gap_counts_by_repair_type`: `add_external_contract_test=78`,
  `upgrade_to_external_contract_test=25`, `split_structure=43`,
  `defer_structure_split=11`, `fix_failing_background_evidence=2`,
  `rerun_public_release_evidence=1`.
- `gap_counts_by_release_relevance`: `runtime_contract=149`,
  `validation_gate=7`, `release_gate=2`, `legacy_validation=2`.

## Top Repair Items

The current highest-priority actionable summary is:

1. `test-tier:release`: `public_release_check` is classified as
   `release_local_only` because URL checks were skipped; this is local proof,
   not public release proof.
2. Runtime owner modules such as `barrier_bundle.py`,
   `flowpilot_controller_break_glass.py`, `flowpilot_paths.py`, and
   `flowpilot_prompt_store.py`: upgrade internal-only tests into direct
   source-level external contract bindings.
3. Runtime owner/facade modules with no ordinary test evidence: add focused
   public contract tests or preserve them as structure-split candidates if a
   safe test boundary is not yet clear.
4. `test-tier:legacy-full`: two legacy full-model background artifacts are
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
- Aggregate model-check runner public contracts for every
  `simulations/run_*checks.py` entrypoint.
- Aggregate test-tier command contracts for command names, referenced targets,
  integration tier contents, background recommendations, and release-only
  placement.
- Aggregate compatibility-facade surface contracts for parseable asset modules,
  stable export lists, and owner-module delegation.
- Aggregate script surface contracts for repository CLIs and wrappers.

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
