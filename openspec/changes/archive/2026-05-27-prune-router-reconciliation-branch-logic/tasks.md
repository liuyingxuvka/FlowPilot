## 1. Model Grounding

- [x] 1.1 Re-run FlowGuard existing-model preflight for Router receipt, role-output, and runtime-state branch ownership.
- [x] 1.2 Add a branch-pruning model that represents reconciliation as `Input x State -> Set(Output x State)`.
- [x] 1.3 Encode the shared result cases: `noop`, `reconciled`, `superseded`, `replay_required`, `retry_pending`, `repair_pending`, and `blocked`.
- [x] 1.4 Add known-bad model cases for overclaiming branch equivalence, missing event authority, duplicate runtime-state ownership, and progress-only validation evidence.

## 2. Evidence Before Runtime Changes

- [x] 2.1 Add source-level model-test alignment contracts for the branch classifier and result-case effect application.
- [x] 2.2 Add focused replay fixtures for scheduled Controller receipt reconciliation branch families.
- [x] 2.3 Add role-output authority fixtures that distinguish invalid, not-ready, unauthorized, already-recorded, reconciled, and side-effect-only envelopes.
- [x] 2.4 Add runtime-state model fixtures for packet-ledger resume status mapping without changing runtime-state ownership.

## 3. Controller Receipt Branch Pruning

- [x] 3.1 Refactor scheduled Controller receipt reconciliation around a result-case classifier without changing public imports.
- [x] 3.2 Replace repeated branch-local write/update/clear/save sequences with shared effect application where replay proves equivalence.
- [x] 3.3 Preserve separate handlers for branches that remain behaviorally distinct after modeling.
- [x] 3.4 Keep `flowpilot_router_controller_scheduler_receipts_scheduled.py` compatible until StructureMesh approves any child-owner split.

## 4. Secondary Structure Planning

- [x] 4.1 Re-run Architecture Reduction and Code Structure Recommendation after the Controller receipt branch model is green.
- [x] 4.2 Split files only if the reduced logic needs clearer classifier/effect/facade/domain ownership.
- [x] 4.3 Keep role-output and runtime-state candidates model-only unless authority and stale-save replay evidence are green.
- [x] 4.4 Update StructureMesh catalogs and model-test alignment source contracts only for implementation boundaries that are actually adopted.

## 5. Validation And Sync

- [x] 5.1 Run focused branch-pruning model checks and known-bad sanity checks.
- [x] 5.2 Run focused runtime tests for scheduled receipts, role-output authority, and runtime-state resume mapping.
- [x] 5.3 Run FlowGuard router facade split, StructureMesh, and model-test alignment checks.
- [x] 5.4 Run router, Meta, and Capability regressions through the background artifact contract before claiming implementation done.
- [x] 5.5 Sync the repo-owned FlowPilot skill into the local installed skill location and audit freshness after runtime source changes.
- [x] 5.6 Record FlowGuard adoption evidence, KB postflight notes, and local git evidence for the final implementation.
