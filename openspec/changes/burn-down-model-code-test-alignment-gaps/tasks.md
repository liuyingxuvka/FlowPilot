## 1. Inventory and Delegation

- [x] 1.1 Refresh the current diagnostic inventory and extract prioritized gap clusters by repair type and release relevance.
- [x] 1.2 Delegate read-only analysis for missing model bindings, missing/internal-only tests, and extra-code/structure-split candidates.
- [x] 1.3 Select a bounded set of high-value repair targets that can be safely implemented without overlapping unrelated peer work.

## 2. External Contract Evidence

- [x] 2.1 Add aggregate external-contract tests for high-value model-check runner surfaces.
- [x] 2.2 Add or strengthen external-contract tests for selected test-tier command surfaces.
- [x] 2.3 Add or strengthen external-contract tests for selected public script entrypoints and compatibility facades.
- [x] 2.4 Teach the diagnostic to recognize the new evidence without treating internal-only tests as full coverage.

## 3. Model Binding and Code Classification

- [x] 3.1 Add model/source-contract bindings for selected intentional owner modules and public entrypoints currently reported as missing model.
- [x] 3.2 Reclassify selected intentional compatibility code so it is not reported as unowned extra code.
- [x] 3.3 Preserve true extra-code and broad split candidates as actionable residual findings with owner and next-action metadata.

## 4. Documentation and Result Artifacts

- [x] 4.1 Regenerate `simulations/flowpilot_model_test_alignment_results.json`.
- [x] 4.2 Update model-test-code diagnostic documentation with before/after counts and remaining residual gap categories.
- [x] 4.3 Update OpenSpec task status as each implementation group is validated.

## 5. Validation, Sync, and Local Git

- [x] 5.1 Run focused unit/pytest checks for changed diagnostics and tests.
- [x] 5.2 Run OpenSpec strict validation for this change.
- [x] 5.3 Run practical background tier validation and inspect final artifacts with the classifier.
- [x] 5.4 Sync the local installed FlowPilot skill and verify install/audit checks.
- [x] 5.5 Record FlowGuard adoption evidence and KB postflight observation.
- [x] 5.6 Commit the scoped local changes without staging unrelated peer or timestamp-only files.
