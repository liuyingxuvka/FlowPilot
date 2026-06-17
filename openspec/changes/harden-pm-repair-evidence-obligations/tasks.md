## 1. Model And Contract Grounding

- [x] 1.1 Record the model miss class for reason-only or registry-only PM repair decisions after semantic blockers.
- [x] 1.2 Extend FieldLifecycleMesh field rows and chains for `repair_evidence_obligations` and `repair_obligation_disposition`.
- [x] 1.3 Extend packet-result contract metadata so PM repair packets/results expose the new required fields and branch examples.
- [x] 1.4 Extend ContractExhaustionMesh and Cartesian control-plane coverage for missing, empty, wrong-type, duplicate, unknown, stale, and old-alias repair obligation cases.
- [x] 1.5 Extend FieldLifecycleMesh, ContractExhaustionMesh, Cartesian coverage, and Model-Test Alignment for required sealed-body reads through `authorized_result_reads`, `current_handoff_contract`, open receipts, and submit-time rejection.

## 2. Runtime Contract Implementation

- [x] 2.1 Derive `repair_evidence_obligations` from active blocker fields when creating PM repair decision packets.
- [x] 2.2 Require `repair_obligation_disposition` when a PM repair packet declares obligations.
- [x] 2.3 Validate disposition coverage: every obligation exactly once, no unknown ids, no duplicates, no stale ids, and no reason/summary/registry-only closure.
- [x] 2.4 Preserve existing terminal supplemental, parent-scope, redesign-route, and authority-waiver branch requirements while adding obligation disposition.
- [x] 2.5 Project current repair obligation ids to downstream repair, FlowGuard semantic recheck, and Reviewer recheck context without adding a fallback path.
- [x] 2.6 Project blocker, target, and upstream result bodies to downstream packets as required authorized reads, deliver all bodies through packet open, and reject submit-result when any required open receipt is missing.

## 3. Prompt And Role Card Updates

- [x] 3.1 Update PM repair card guidance to require disposition of every repair evidence obligation.
- [x] 3.2 Update FlowGuard operator guidance to verify semantic rechecks consume repair obligation context.
- [x] 3.3 Update Reviewer guidance to block direct-evidence claims that do not consume the current obligation context.
- [x] 3.4 Update packet identity, output contract, PM, repair worker, Reviewer, FlowGuard operator, and role handoff guidance so every delivered authorized blocker/target/upstream body must be read before submit.

## 4. Tests And Synthetic Coverage

- [x] 4.1 Add focused runtime tests for PM repair packet obligation creation and reason-only rejection.
- [x] 4.2 Add focused runtime tests for unknown, duplicate, stale, waiver-without-authority, and registry-only obligation dispositions.
- [x] 4.3 Add fake AI or synthetic coverage rows for PM repair obligation failure shapes.
- [x] 4.4 Add field contract tests for the new lifecycle rows and chains.
- [x] 4.5 Add model-test alignment rows and tests binding the new obligations to runtime contracts and test evidence.
- [x] 4.6 Add multi-body runtime/handoff regressions and card coverage tests proving one-body-only or summary-only behavior is not acceptable.

## 5. Validation And Sync

- [x] 5.1 Run OpenSpec strict validation for this change.
- [x] 5.2 Run focused runtime, field contract, synthetic coverage, contract exhaustion, Cartesian, card coverage, model coverage, meta, capability, and model-test alignment checks.
- [x] 5.3 Rebuild and check FlowGuard project topology after model/test/code changes.
- [x] 5.4 Sync the repo-owned FlowPilot skill install and audit local install sync.
- [x] 5.5 Run final install self-checks and record FlowGuard adoption evidence.
- [x] 5.6 Review final git status and stage/commit only the intended current-contract FlowPilot changes.
