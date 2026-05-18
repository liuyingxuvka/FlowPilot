# FlowPilot Full Model-Test-Code Diagnostics

Date: 2026-05-18

This report summarizes the full diagnostic layer emitted by:

```powershell
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
```

The original eight family alignment plans, the AST-supported source-contract
subset, and the full diagnostic machinery are green. The full diagnostic layer
is intentionally stricter than the family gates: it inventories wider repository
surfaces and reports remaining model, code, test, background-evidence, and
structure-split repair work.

- `full_diagnostic_ok`: true. The diagnostic machinery and known-bad sanity
  checks are working.
- `full_coverage_ok`: false. Some ordinary external-contract tests, structure
  splits, and background evidence repairs remain.

## Current Counts

| Metric | Count |
| --- | ---: |
| Total diagnostic surfaces | 532 |
| Covered surfaces | 433 |
| Surfaces with one or more gaps | 99 |
| Compatibility facades | 60 |
| Owner modules | 118 |
| Script entrypoints | 17 |
| Model-check runners | 82 |
| Test tiers | 15 |
| Test tier commands | 240 |

## Gap Counts

| Gap code | Count | Meaning |
| --- | ---: | --- |
| `missing_test` | 55 | No ordinary external-contract test evidence was found for the surface. |
| `needs_structure_split` | 52 | Module or script is above the diagnostic split threshold. |
| `stale_evidence` | 3 | Background evidence is failed, stale, incomplete, progress-only, or local-only release proof. |

`internal_only_test` is now zero. The latest burn-down converted the prior
internal-only owner evidence into source-level external-contract bindings and
kept the remaining runtime gaps visible as direct `missing_test` or
`needs_structure_split` work.

Aggregate counts in the JSON include:

- `gap_counts_by_severity`: `critical=1`, `medium=109`.
- `gap_counts_by_repair_type`: `add_external_contract_test=55`,
  `split_structure=42`, `defer_structure_split=10`,
  `fix_failing_background_evidence=2`,
  `rerun_public_release_evidence=1`.
- `gap_counts_by_release_relevance`: `runtime_contract=99`,
  `validation_gate=7`, `release_gate=2`, `legacy_validation=2`.

## Top Repair Items

The current highest-priority actionable summary is:

1. `test-tier:release`: `public_release_check` is classified as
   `release_local_only` because URL checks were skipped; this is local proof,
   not public release proof.
2. `script:run_test_tier`: the tier runner is still above the structure split
   threshold and should be the next StructureMesh-backed split candidate.
3. Remaining router owner modules such as CLI, control transactions,
   controller repair scheduling, controller scheduler receipt shards, event
   intake/identity, event repair, expected waits, and facade export helpers
   still need ordinary direct external-contract tests.
4. `test-tier:legacy-full`: two legacy full-model background artifacts remain
   visible as failed legacy-validation history, but old legacy full-model
   checks are not ranked as current release gates.

## Newly Strengthened Contract Coverage

This pass added or strengthened external-contract evidence for:

- Runtime owner contract tests for barrier bundles, break-glass incident
  lifecycle, run-path resolution, prompt store hashing, packet runtime
  contract/path/schema/audit boundaries, packet control-plane runner exit
  behavior, lifecycle-provider side effects, card-return ids, and router error
  records.
- Router owner-boundary helpers already exercised by
  `tests/test_flowpilot_router_boundaries.py`, now bound into the source
  contract plan.
- Router owner external contracts for action envelopes, dispatch recipient
  gates, action handler outcome/error paths, artifact validation, card delivery
  ledgers, child-skill capability sync/approval, and controller scheduler
  ledger projection, exercised by `tests/test_flowpilot_router_owner_contracts.py`.
- `flowpilot_router_protocol_boot_cards.py` as a compatibility aggregation
  layer. It dropped from 684 lines before this change to 64 lines after the
  latest split.
- New declarative protocol modules:
  `flowpilot_router_protocol_startup_catalog.py` at 196 lines,
  `flowpilot_router_protocol_planning_cards.py` at 253 lines,
  `flowpilot_router_protocol_runtime_cards.py` at 157 lines, and
  `flowpilot_router_protocol_card_metadata.py` at 151 lines.

The boot-card split now has direct contract evidence for
`startup_boot_catalog`, `planning_system_card_catalog`,
`runtime_system_card_catalog`, `system_card_metadata_catalog`, and
`system_card_catalog`. All five split surfaces are below the StructureMesh line
threshold and have no diagnostic gap codes.

## Background Evidence Policy

Background evidence is classified from final artifacts rather than progress
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

The diagnostic records concrete deferred split metadata for broad surfaces that
remain above threshold. Stateful surfaces stay deferred until they have a
claimed StructureMesh target:

- `flowpilot_router_work_packets_current_node.py`
- `flowpilot_router_card_returns.py`
- `role_output_runtime_schema.py`
- route artifact/frontier state shards

Declarative surfaces remain safer follow-up candidates after an explicit claim:

- `flowpilot_router_facade_export_manifest_controller.py`
- `flowpilot_router_protocol_decision_tables.py`

`flowpilot_router_protocol_boot_cards.py` is no longer a pending split
candidate. It is recorded as `completed_split` with the startup, planning,
runtime, and metadata catalogs extracted into focused modules.
