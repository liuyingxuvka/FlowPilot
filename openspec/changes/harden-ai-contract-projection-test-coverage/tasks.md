## 1. Coverage Model Setup

- [x] 1.1 Add AI-facing conditional contract projection cases to the executable coverage matrix.
- [x] 1.2 Add ContractExhaustionMesh case rows for conditional projection and retry convergence.
- [x] 1.3 Add TestMesh ownership rows for the new projection and retry convergence evidence.
- [x] 1.4 Add Model-Test Alignment rows that distinguish validator, projection, and corrected-retry evidence.
- [x] 1.5 Expand ContractExhaustionMesh from representative `semantic_recheck` rows to data-driven rows for every result-contract finite option and every conditional profile finite/exact field.

## 2. Projection Tests

- [x] 2.1 Add packet-local projection tests for `semantic_recheck` required fields, allowed options, and minimal valid shape.
- [x] 2.2 Add projection tests for forbidden near-synonym fields and conditional field visibility.
- [x] 2.3 Add regression checks that validator-only evidence cannot count as projection coverage.
- [x] 2.4 Add matrix-generation tests proving every `allowed_value_options` field has both missing-projection and wrong-value coverage cells.
- [x] 2.5 Add matrix-generation tests proving every result-contract profile exposes profile-owned required fields, field types, allowed values, and forbidden aliases as profile-specific cells.

## 3. Reissue And Fake-AI Convergence Tests

- [x] 3.1 Add deterministic bad fake-AI payload variants for near-synonym fields, wrong boolean/object values, missing consumed read ids, and missing repair obligation ids.
- [x] 3.2 Add runtime reissue feedback tests proving each bad payload yields precise correction fields.
- [x] 3.3 Add wrong-then-corrected fake-AI rehearsal tests proving legal continuation before GlassBreak.
- [x] 3.4 Preserve dedicated GlassBreak threshold coverage for the fifth same-class repeat.
- [x] 3.5 Add a contract-driven fake-AI responder that reads packet-local finite options, refuses missing options, generates wrong-value rows for every visible option field, and repairs from runtime reissue feedback.
- [x] 3.6 Add a responder-to-model parity check: every ContractExhaustionMesh cell assigned to fake-AI responder ownership and expressible through packet/result contracts must be generated from the AI-facing contract surface, not from hand-written package assumptions.
- [x] 3.7 Add responder option-value parity: every declared finite option value must be materializable into a branch-valid fake-AI payload, and unreachable option values must fail the contract-exhaustion gate.

## 4. Validation And Sync

- [x] 4.1 Run targeted unit tests for projection, reissue feedback, fake rehearsal, and contract exhaustion.
- [x] 4.2 Run affected FlowGuard model checks and update result artifacts.
- [x] 4.3 Rebuild and check FlowGuard project topology if model/test registries changed.
- [x] 4.4 Sync the repo-owned local FlowPilot install and run install/audit checks.
- [x] 4.5 Record FlowGuard adoption and KB postflight evidence for the completed test upgrade.
- [x] 4.6 Run the upgraded ContractExhaustion, executable matrix, Cartesian, Model-Test Alignment, card instruction, and Acceptance TestMesh unit checks.
- [x] 4.7 Wait for router background TestMesh evidence if a broad routine/release acceptance claim is required after parallel AI work settles.
- [x] 4.8 Close the current responder parity gaps for `pm_repair_decision.pm_repair_decision` after the peer implementation externalizes the missing conditional branch shapes/options and the four unreachable `hygiene_category` option values, then rerun `tests.test_flowpilot_contract_exhaustion_mesh` to green.
