## 1. Preflight And Baseline

- [x] 1.1 Record FlowGuard package/version/project-audit evidence and current peer-agent dirty worktree boundaries.
- [x] 1.2 Add a human-readable contract reduction baseline document that compares `run-20260613-140526` and the later first-packet failure as process evidence.
- [x] 1.3 Validate this OpenSpec change before production edits and keep the active `harden-flowpilot-stage-evidence-matrix` change visible as a dependency, not a replacement.

## 2. Stage Matrix Contract Authority

- [x] 2.1 Extend `packet_stage_evidence_matrix.py` rows with `current_required_fields`, `moved_fields`, `deleted_fields`, `allowed_blocker_classes`, `blocker_class_to_next_action`, and `required_evidence_owner`.
- [x] 2.2 Replace soft future-evidence wording in matrix data with hard keep/move/delete and allowed-blocker declarations for all mainline packet families.
- [x] 2.3 Add strict helper functions for field disposition lookup, allowed blocker class lookup, and fixed blocker next-action lookup.
- [x] 2.4 Add repair packet contract metadata for every fixed blocker class: packet family, required source ids, required receipts/evidence refs, owner role, payload fields, and return gate.
- [x] 2.5 Add repeated-repair lineage metadata: original blocker id, prior repair packet/result ids, prior evidence refs, failed recheck id, prior failure reason, new repair delta, and return gate.
- [x] 2.6 Add tests proving every mainline family has the new matrix fields and unknown families fail without fallback.

## 3. Packet Result Contract Reduction

- [x] 3.1 Reduce `task.high_standard_contract` to `requirements` and `acceptance_item_registry`, using `closure_rule` and `future_evidence_rule`.
- [x] 3.2 Reduce `task.discovery` and `task.skill_standard` to preplanning definition fields only.
- [x] 3.3 Keep `task.planning` parent/child structure and `acceptance_item_ids` ownership while rejecting worker/final evidence fields.
- [x] 3.4 Reduce `task.node_acceptance_plan` to five node context groups.
- [x] 3.5 Add `current_evidence_refs` to `task.node` and reject progress-only/currentless node results.
- [x] 3.6 Reduce `flowguard_check.post_result` to the seven PM-facing result fields and move model details to the run-local evidence file contract.
- [x] 3.7 Reduce `review.any_current_subject` to the seven Reviewer-facing result fields while preserving blocker authority.
- [x] 3.8 Reduce PM repair to common fields plus branch-specific payloads only.
- [x] 3.9 Replace PM disposition acceptance item arrays with `acceptance_item_disposition[]`.
- [x] 3.10 Keep parent replay and terminal replay separate, with terminal replay strict on final closure.

## 4. Runtime Mechanical Validation

- [x] 4.1 Add blocker object validation that checks enum membership, fixed next-action mapping, current target ids, and field shape only.
- [x] 4.2 Add repair packet validation that checks each blocker class opens its fixed repair packet with required source ids, receipts/evidence refs, owner role, payload fields, and return gate.
- [x] 4.3 Add repeated-repair validation that requires prior repair materials to carry forward on second and later attempts.
- [x] 4.4 Reject moved/deleted fields according to the matrix without translating old fields into current fields.
- [x] 4.5 Ensure FlowGuard model-detail fields in result bodies are rejected and packet-owned `flowguard_evidence.json` is the single model-detail evidence surface.
- [x] 4.6 Ensure target projects use installed self-check receipts and run-local evidence instead of FlowPilot development repository simulation scripts.
- [x] 4.7 Remove or reject legacy aliases, wrappers, shape guessing, newest-run fallback, repo-root fallback, historical result promotion, old packet evidence, and manual fallback blocker evaluation surfaces.

## 5. Prompt And Card Cleanup

- [x] 5.1 Update FlowGuard role and child cards so FlowGuard models and self-repairs small model/test gaps in its evidence file, never by requiring PM to pre-fill model fields.
- [x] 5.2 Update Reviewer role and child cards so Reviewer can block only by current-stage fixed blocker classes.
- [x] 5.3 Update PM role and phase cards so PM writes current-stage packages, absorbs fixed blockers, and chooses one finite structured repair branch from the PM repair-decision packet.
- [x] 5.4 Update route and node acceptance cards to keep parent/child and acceptance item ownership at planning/node-plan stages only.
- [x] 5.5 Remove prompt/card wording that treats early packets as terminal evidence packages or target projects as FlowPilot development repositories.

## 6. FlowGuard Model Updates

- [x] 6.1 Update FieldLifecycleMesh rows for every kept, moved, and deleted field.
- [x] 6.2 Update ArchitectureReduction evidence for removed broad report fields, duplicate gate language, and fallback surfaces.
- [x] 6.3 Update Model-Test Alignment obligations to bind the reduced matrix, contracts, runtime validators, prompts, and tests.
- [x] 6.4 Update ContractExhaustionMesh cases for missing, wrong-type, moved-field, deleted-field, unknown blocker class, wrong next action, and fallback cases.
- [x] 6.5 Update TestMesh coverage so every mainline packet family has current child test evidence.

## 7. Unit And Replay Tests

- [x] 7.1 Add or update stage matrix tests for all mainline families and blocker mappings.
- [x] 7.2 Add or update packet result contract tests for all reduced families.
- [x] 7.3 Add Reviewer stage-boundary tests: current-stage blocks pass, future-stage blocks fail.
- [x] 7.4 Add FlowGuard self-repair evidence tests for model/test gaps and compact result bodies.
- [x] 7.5 Add PM repair and disposition contract tests for finite PM repair branches and `acceptance_item_disposition[]`.
- [x] 7.6 Add blocker repair package tests for every fixed blocker class handling route and repair packet contract.
- [x] 7.7 Add repeated-repair lineage tests proving prior repair materials carry forward and missing lineage is rejected.
- [x] 7.8 Add parent replay and terminal replay contract tests.
- [x] 7.9 Add no-fallback negative tests for all removed compatibility surfaces.
- [x] 7.10 Extend historical live-run replay tests to cover the 2026-06-13 success mainline and the later failure as one regression among all families.

## 8. Validation, Install, And Sync

- [x] 8.1 Run focused unit tests for changed runtime, contracts, prompts, and replay surfaces.
- [x] 8.2 Run FlowGuard model checks for field, contract exhaustion, model-test alignment, information-flow, Meta, and Capability surfaces.
- [x] 8.3 Rebuild and check the FlowGuard project topology after model/test/runtime changes.
- [x] 8.4 Sync repository FlowPilot artifacts to the local installed skill and run install audits.
- [x] 8.5 Run smoke checks in a target-project style workspace without development repository script assumptions.
- [x] 8.6 Inspect final git status/diff without reverting peer-agent changes.
- [x] 8.7 Perform predictive KB postflight and record any reusable route gap or correction.
