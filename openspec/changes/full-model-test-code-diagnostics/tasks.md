## 1. Inventory And Scope

- [x] 1.1 Inventory FlowPilot owner modules and compatibility facades under `skills/flowpilot/assets`.
- [x] 1.2 Inventory script entrypoints under `scripts/` and FlowPilot CLI/runtime entrypoints.
- [x] 1.3 Inventory `scripts/run_test_tier.py` test tiers and their child commands.
- [x] 1.4 Map existing model-test-code coverage from the current alignment runner and related FlowGuard models.

## 2. Diagnostic Model

- [x] 2.1 Add full diagnostic surface rows for owner modules, facades, scripts, and test tiers.
- [x] 2.2 Add gap classifications for missing model, missing code, missing test, extra code, internal-only test, stale evidence, and needs-structure-split.
- [x] 2.3 Add known-bad diagnostics for orphan code, wrapper-only evidence, progress-only background evidence, and broad unsplit modules.
- [x] 2.4 Generate machine-readable diagnostic output with counts and per-surface findings.

## 3. Tests And Reports

- [x] 3.1 Add unit tests for diagnostic schema, coverage counts, and known-bad gap detection.
- [x] 3.2 Add or update a human-readable diagnostic report documenting current gaps and split candidates.
- [x] 3.3 Update documentation explaining how to interpret full diagnostic output versus subset alignment.

## 4. Validation

- [x] 4.1 Run focused model-test-code diagnostic checks and unit tests.
- [x] 4.2 Run OpenSpec strict validation for this change.
- [x] 4.3 Run relevant FlowGuard model regressions in background with complete artifact inspection.
- [x] 4.4 Sync local FlowPilot install if repo-owned skill files changed, then audit install freshness.

## 5. Completion

- [x] 5.1 Record FlowGuard adoption evidence with commands, findings, skipped checks, and residual risk.
- [x] 5.2 Record predictive KB postflight observation if this work exposes reusable diagnostic or background-check lessons.
- [x] 5.3 Stage and commit only files clearly owned by this change; do not stage peer-agent owner-module polish files.
