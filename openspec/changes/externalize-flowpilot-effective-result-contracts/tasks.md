## 1. Contract Design

- [x] 1.1 Add explicit result contract profiles to the stage matrix.
- [x] 1.2 Add effective contract helpers in packet result contracts.
- [x] 1.3 Preserve base-family helpers while routing runtime checks through effective helpers.

## 2. Runtime Integration

- [x] 2.1 Add `result_contract_profile_ids` to packet envelope and output contract.
- [x] 2.2 Attach `flowguard.semantic_recheck_required` when issuing blocker-bound FlowGuard recheck packets.
- [x] 2.3 Attach `flowguard.subject_artifacts_consumed_required` when subject artifacts must be consumed.
- [x] 2.4 Use effective contracts in handoff, open-packet submission checklist, submit-result validation, and reissue.
- [x] 2.5 Reissue packets must include effective minimal shape, allowed values, type requirements, and actual invalid submitted fields when present, without publishing unsupported-field example catalogs.

## 3. Prompt Cleanup

- [x] 3.1 Update FlowGuard operator wording to treat external contract surfaces as mechanical authority.
- [x] 3.2 Update packet output contract prompts/templates so body text cannot add hidden mechanical fields.
- [x] 3.3 Add card coverage tests for the new wording.
- [x] 3.4 Filter role-visible stage evidence so lifecycle-history fields stay internal and do not appear in role prompts or packet bodies.

## 4. Tests And Models

- [x] 4.1 Add first-packet tests for effective semantic recheck minimal shape and allowed values.
- [x] 4.2 Add reissue tests for complete second-round repair guidance.
- [x] 4.3 Add wrong-type and near-alias negative tests.
- [x] 4.4 Add subject-artifact profile tests.
- [x] 4.5 Update FieldLifecycleMesh, ContractExhaustionMesh, Model-Test Alignment, and synthetic-agent coverage.

## 5. Validation And Sync

- [x] 5.1 Run focused runtime, prompt, and contract tests; broad fake-agent coverage remains owned by the parallel fake-agent workstream.
- [x] 5.2 Run affected FlowGuard model checks, split smoke groups, and topology check.
- [x] 5.3 Sync local installed FlowPilot artifacts and run install audits.
- [x] 5.4 Commit the completed change after peer-agent-safe final status inspection.
