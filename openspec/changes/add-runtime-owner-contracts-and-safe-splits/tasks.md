## 1. Planning and Inventory

- [x] 1.1 Run KB preflight and FlowGuard import preflight.
- [x] 1.2 Inspect current git status and identify peer-owned dirty files.
- [x] 1.3 Extract prioritized runtime owner contract gaps and structure split candidates from the current diagnostic JSON.

## 2. Runtime Owner Contract Tests

- [x] 2.1 Add direct owner-contract tests for high-priority non-router runtime modules.
- [x] 2.2 Bind those tests into the FlowGuard source-contract alignment plan.
- [x] 2.3 Add direct owner-contract bindings for already-tested router owner modules.
- [x] 2.4 Regenerate the model-code-test diagnostic and verify reduced `internal_only_test` / `missing_test` counts.

## 3. Safe Structure Split

- [x] 3.1 Select split candidates that do not overlap active peer edits.
- [x] 3.2 Apply compatibility-preserving declarative splits where validation scope is clear.
- [x] 3.3 Record remaining deferred split reasons without editing risky modules.

## 4. Validation and Sync

- [x] 4.1 Run focused unit/pytest checks.
- [x] 4.2 Run OpenSpec strict validation for this change.
- [x] 4.3 Run practical background tier validation and inspect final artifacts.
- [x] 4.4 Sync local installed FlowPilot skill and verify install/audit checks.
- [x] 4.5 Record FlowGuard adoption evidence and KB postflight observation.
- [x] 4.6 Commit scoped local changes without staging unrelated peer or timestamp-only files.
