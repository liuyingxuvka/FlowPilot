# FlowPilot Full Model-Test-Code Diagnostics

Date: 2026-05-21

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
- `full_coverage_ok`: false. Structure debt remains visible.
- `release_convergence_ok`: true. The remaining findings are explicit
  StructureMesh deferrals, not missing model/code/test bindings or stale
  release evidence.

## Current Counts

| Metric | Count |
| --- | ---: |
| Total diagnostic surfaces | 717 |
| Covered surfaces | 708 |
| Surfaces with one or more gaps | 9 |
| Compatibility facades | 107 |
| Owner modules | 226 |
| Script entrypoints | 19 |
| Model-check runners | 92 |
| Model-check runner helpers | 18 |
| Test tiers | 15 |
| Test tier commands | 240 |

## Gap Counts

| Gap code | Count | Meaning |
| --- | ---: | --- |
| `needs_structure_split` | 9 | Module or script is above the diagnostic split threshold and is explicitly deferred under StructureMesh. |

`missing_model`, `missing_code`, `missing_test`, `extra_code`,
`internal_only_test`, and `stale_evidence` are all zero in the current
diagnostic result. The latest burn-down converted the remaining owner-module
rows into source-level external-contract bindings and kept only explicit
StructureMesh deferrals visible.

Aggregate counts in the JSON include:

- `gap_counts_by_severity`: `medium=9`.
- `gap_counts_by_repair_type`: `defer_structure_split=9`.
- `gap_counts_by_release_relevance`: `runtime_contract=9`.
- `unresolved_non_deferred_gap_count`: `0`.
- `deferred_structure_split_count`: `9`.

## Top Repair Items

The current actionable summary is intentionally a structure backlog, not a
missing-test backlog:

1. Nine runtime-contract surfaces remain over the owner/facade threshold. They
   keep explicit `peer_safety_status`,
   `deferred_split_reason`, `safe_split_class`, and
   `recommended_next_action` metadata.
2. `run_flowpilot_model_test_alignment_checks.py` is now a small compatibility
   runner facade. Its common declarations, family plans, source-contract plan,
   known-bad cases, and full diagnostic surface inventory live in focused
   `flowpilot_model_test_alignment_*` modules.
3. `run_test_tier.py` has already been split into a small CLI wrapper plus
   focused tier-definition and background-artifact modules.
4. `public_release_check` now has current URL-probing evidence from
   `python scripts\check_public_release.py --json --skip-validation`; it is no
   longer counted as local-only release proof.
5. `meta_legacy_full` and `capability_legacy_full` are reclassified as
   historical compatibility oracles. Current release confidence comes from
   reused valid layered full parent proofs. The failed/running legacy artifacts
   stay visible in `background_evidence` but do not block
   `release_convergence_ok`.

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

This pass also added `tests/test_flowpilot_full_diagnostic_contracts.py`, which
binds direct external contracts for the remaining controller/control/scheduler,
event/wait/repair, facade-export, lifecycle/startup/system-card,
role/prompt/proof/terminal/work-packet, user-flow, and packet control-plane
surfaces. The source-contract plan now has matching obligations, code
contracts, and exact test ids for those rows.

The next structure-maintenance pass also split two declarative runtime table
parents while preserving their public contracts:

- `flowpilot_router_facade_export_manifest_controller.py` dropped to 31 lines
  and now aggregates controller repair, scheduler, events, and lifecycle export
  shards. The facade-export contract test checks the child-union parity.
- `flowpilot_router_protocol_external_events.py` dropped to 40 lines and now
  aggregates startup, material/product, route, and terminal event shards. The
  event/wait/repair contract test checks the child-union parity.

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
`--skip-url-check` is explicitly local-only proof. The current public release
proof uses `--skip-validation` only, so URL probing still runs while avoiding a
duplicate nested full validation pass.

Legacy monolithic Meta/Capability full graphs are no longer the release proof
source. They remain inspectable compatibility oracles; when the current
layered full parent proof is valid, the diagnostic records
`legacy_full_reclassified` instead of counting old monolithic failure as stale
release evidence.

## Structure-Split Repair Planning

The diagnostic records concrete deferred split metadata for broad surfaces that
remain above threshold. These surfaces stay deferred until they have a claimed
StructureMesh target and parity evidence:

- `flowpilot_router_controller_scheduler_receipts_effects.py`
- `flowpilot_router_controller_scheduler_receipts_packet_folds.py`
- `flowpilot_router_controller_scheduler_receipts_scheduled.py`
- `flowpilot_router_controller_scheduler_standby.py`
- `flowpilot_router_io.py`
- `flowpilot_router_lifecycle_requests.py`
- `flowpilot_router_protocol_external_event_data.py`
- `flowpilot_router_runtime_state.py`
- `flowpilot_router_startup_intake_materialization.py`

`flowpilot_router_protocol_boot_cards.py` is no longer a pending split
candidate. It is recorded as `completed_split` with the startup, planning,
runtime, and metadata catalogs extracted into focused modules.
`flowpilot_router_facade_export_manifest_controller.py`,
`flowpilot_router_protocol_external_events.py`, and
`simulations/run_flowpilot_model_test_alignment_checks.py` are also no longer
pending split candidates at their public facade level.
