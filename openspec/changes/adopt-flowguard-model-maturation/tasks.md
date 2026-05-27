## 1. Model Grounding

- [x] 1.1 Verify real FlowGuard import/version in the FlowPilot repository.
- [x] 1.2 Inventory existing FlowPilot models, result artifacts, and stale or missing maturation evidence.
- [x] 1.3 Record the existing-model reuse decision and the scoped confidence boundary for this change.

## 2. OpenSpec And Maturation Model

- [x] 2.1 Add OpenSpec specs for model maturation, ACK/output separation, route replacement disposition, prompt assets, background proof, hierarchy, and diagnostics.
- [x] 2.2 Add a focused FlowGuard model for FlowPilot model maturation closure signals.
- [x] 2.3 Add a checker that calls `review_model_maturation_loop()` and writes a result artifact.
- [x] 2.4 Include known-bad hazards for ACK-only closure, undisposed replacement packets, prompt-contract gaps, stale evidence, oversized parent masking, and progress-only evidence.

## 3. Validation Integration

- [x] 3.1 Add the maturation checker/result to install readiness or local validation surfaces.
- [x] 3.2 Update maintenance documentation and validation command lists.
- [x] 3.3 Ensure model-test-code diagnostics can expose maturation actions and scoped confidence.

## 4. Sync And Verification

- [x] 4.1 Run OpenSpec strict validation for the change.
- [x] 4.2 Run the focused maturation checker and targeted related FlowGuard checks.
- [x] 4.3 Run install/smoke/local sync checks and refresh installed FlowPilot skill.
- [x] 4.4 Run heavyweight regressions in the background artifact contract where practical and report final artifacts, exit status, and any scoped gaps.
- [x] 4.5 Mark tasks complete only after verified, preserving peer-agent changes.
