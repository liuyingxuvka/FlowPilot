## 1. Baseline and Ownership

- [x] 1.1 Create a dedicated OpenSpec change for FlowGuard-kernel adoption closure and validate the change artifact.
- [x] 1.2 Verify the real `flowguard` package is importable and record that no fake local substitute is being used.
- [x] 1.3 Capture current OpenSpec and git workspace state, including the peer-owned `finish-flowpilot-maintenance-convergence-v2` change and pre-existing dirty files.
- [x] 1.4 Run the current model-test alignment/full diagnostic baseline and identify the unresolved runtime-owner evidence gaps.

## 2. FlowGuard Evidence Repair

- [x] 2.1 Add external `CodeContract` rows for the controller wait audit and runtime gateway public surfaces reported as internally tested only.
- [x] 2.2 Add or adjust ordinary external-contract test evidence rows, and focused assertions if existing tests do not directly exercise the claimed symbols.
- [x] 2.3 Re-run the model-test-code diagnostic and confirm the two `internal_only_test` findings are absent from current evidence.

## 3. Legacy Data and Old Logic Disposition

- [x] 3.1 Audit old-data, legacy-marker, and retired-path handling through existing compatibility specs and validation scripts.
- [x] 3.2 Remove or isolate only old logic that is proven retired in this scope; otherwise document it as compatibility, peer-owned, or deferred structure debt.

## 4. Validation

- [x] 4.1 Run focused runtime-owner tests for controller wait audit and runtime gateway behavior.
- [x] 4.2 Run strict OpenSpec validation for this change and the full repository.
- [x] 4.3 Run FlowGuard model-test alignment with a current artifact.
- [x] 4.4 Run or refresh background meta and capability FlowGuard regressions, then inspect final stdout/stderr/combined/exit/meta artifacts before using them as evidence.

## 5. Install and Local Acceptance

- [x] 5.1 Synchronize the repository-owned FlowPilot skill into the local installed skill.
- [x] 5.2 Run install check and installed-skill freshness audit after synchronization.
- [x] 5.3 Update FlowGuard adoption evidence with commands, findings, skipped steps, and remaining scoped risks.
- [x] 5.4 Report final local git state, distinguishing this change from pre-existing or peer-owned dirty files.
