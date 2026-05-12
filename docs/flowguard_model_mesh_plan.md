# FlowGuard Model Mesh Plan

## Purpose

FlowPilot already has many deep FlowGuard models. The current failure mode is
not lack of local model depth. It is that abstract model results, live run
facts, conformance replay status, and cross-model obligations can drift without
a single model-backed release gate saying whether the current run may proceed.

This plan records the optimization order and the risk list before code changes.
The implementation must first upgrade FlowGuard coverage so the expected
failure classes are executable hazards, then validate the optimization plan
against that model, and only then change runtime or install checks.

## Optimization Checklist

| Order | Optimization item | Concrete change | Done evidence |
| --- | --- | --- | --- |
| 1 | Model mesh risk contract | Add a FlowGuard model that treats each specialized model as a contract-bearing evidence source, not as an implementation detail. | Safe graph passes; required labels include evidence ingestion, live projection, conformance tiering, contradiction blocking, and continue/block decision. |
| 2 | Evidence tiers | Classify model evidence as `abstract_green`, `hazard_green`, `live_current_green`, and `conformance_green`. | Hazards catch abstract-only evidence being used as current-run permission. |
| 3 | Live projection adapter | Read current `.flowpilot/current.json` and the selected run metadata-only artifacts into a mesh fact set. | Current run projection reports a decision without reading sealed body files. |
| 4 | Cross-model contradiction gate | Compare frontier, packet ledger, status summary, active blocker, repair transaction, and saved model result status. | Hazards catch inconsistent active phase, hidden active blocker, stale run id, skipped live audit, and collapsed repair outcome events. |
| 5 | Repair outcome mesh obligation | Require success, blocker, and protocol-blocker outcomes to be distinct and context-compatible when a repair transaction is active. | Hazards catch shared success/blocker/protocol events and parent repair targeting leaf-only current-node events. |
| 6 | Packet authority mesh obligation | Require packet/result role-origin evidence before reviewer/PM evidence can unlock continuation. | Hazards catch `completed_agent_id_belongs_to_role=false` and unchecked role-origin audit being treated as pass evidence. |
| 7 | Decision surface | Emit a stable decision vocabulary: `mesh_green_can_continue`, `blocked_by_live_evidence`, `blocked_by_stale_model_result`, `blocked_by_missing_conformance`, `blocked_by_cross_model_contradiction`, `model_coverage_insufficient`. | Runner output includes decision, blocking reasons, confidence tier, and skipped checks. |
| 8 | Coverage sweep integration | Make the read-only coverage sweep consume the mesh result and expose it as a top-level runner record. | Sweep classifies mesh findings and distinguishes current-run blockers from runner failures. |
| 9 | Install/smoke integration | Add the mesh check to local install validation in a non-destructive mode that does not require the active run to be safe, only correctly classified. | `scripts/check_install.py` passes while reporting mesh decision artifacts. |
| 10 | Local install sync | Refresh the installed FlowPilot skill from the repository after validation. | `scripts/install_flowpilot.py --sync-repo-owned --json` and `scripts/audit_local_install_sync.py --json` pass. |

## Risk List and Required Model Coverage

| Risk id | Possible bug introduced by this optimization | Required FlowGuard catch |
| --- | --- | --- |
| R1 | Abstract model pass is treated as permission to continue a live run. | Hazard fails when `abstract_green` is used without `live_current_green` or accepted blocked-state classification. |
| R2 | A skipped live audit or skipped replay disappears inside a green result file. | Hazard fails when a required live/conformance runner has `skipped_checks` for the active decision tier. |
| R3 | Current run artifacts are from one run id while result files or projections are from another. | Hazard fails on stale or mismatched `run_id` evidence. |
| R4 | Active blocker exists but status summary or mesh decision reports safe-to-continue. | Hazard fails on active blocker hidden by safe decision. |
| R5 | `execution_frontier`, `packet_ledger`, and `status_summary` describe incompatible current work. | Hazard fails on active node/phase/packet mismatch without a blocker decision. |
| R6 | Repair transaction outcome table routes success, blocker, and protocol-blocker to the same business event. | Hazard fails on collapsed outcome events. |
| R7 | Parent/backward repair reruns a leaf-only current-node event. | Hazard fails on node-kind incompatible repair event. |
| R8 | Packet/result role-origin fields are unchecked but reviewer or PM evidence is accepted as sufficient. | Hazard fails on unchecked role origin or `completed_agent_id_belongs_to_role=false` being treated as pass. |
| R9 | The mesh runner reads sealed packet/result body files while auditing. | Hazard fails if metadata-only audit opens sealed body names. |
| R10 | Coverage sweep reports zero findings because it cannot parse or run some runners. | Hazard fails if runner parse errors are ignored for a mesh-level decision. |
| R11 | Check-install becomes impossible whenever an active run is legitimately blocked. | Hazard fails if install validation requires `safe_to_continue` instead of `classified_current_state`. |
| R12 | A local installed skill stays stale after repository changes. | Install/audit validation must compare repository-owned skill content after sync. |

## Implementation Order

1. Add the model mesh plan document.
2. Add `simulations/flowpilot_model_mesh_model.py`.
3. Add `simulations/run_flowpilot_model_mesh_checks.py`.
4. Run the new model and verify every risk in the table is represented by a
   detected hazard.
5. Use the model runner to validate the intended optimization plan.
6. Add the mesh runner to the coverage sweep and check-install surfaces.
7. Run focused tests after each implementation step.
8. Run slower project checks in background where possible:
   `simulations/run_meta_checks.py`, `simulations/run_capability_checks.py`,
   and final smoke/install checks.
9. Sync local installed FlowPilot skill only after repository checks pass.
10. Stage and commit local git changes, without pushing to GitHub.

## Non-Goals

- Do not merge every specialized model into one giant state graph.
- Do not read sealed packet, result, report, or decision bodies during mesh
  audit.
- Do not make ordinary install checks fail merely because the current active
  FlowPilot run is intentionally blocked.
- Do not delete or rewrite historical `.flowpilot` evidence.
- Do not push to remote GitHub as part of this task.
