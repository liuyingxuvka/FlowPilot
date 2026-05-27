## 1. Requirements And Model Grounding

- [x] 1.1 Validate real FlowGuard import and preserve peer-agent workspace state.
- [x] 1.2 Inventory existing parallel-run isolation, current-pointer, active UI catalog, status summary, and live-audit coverage.
- [x] 1.3 Validate this OpenSpec change strictly before implementation.

## 2. FlowGuard Model And Audit

- [x] 2.1 Extend the control-plane friction model/audit so explicit active-set authority requires targetable active entries, current-pointer focus-only semantics, no global main requirement, and stale-residue classification.
- [x] 2.2 Add known-bad checks for missing target ids, missing active-set authority, hidden non-current active runs, stale active residue reported as live work, and implicit all-run operations.
- [x] 2.3 Refresh model-test alignment evidence for active-set authority coverage.

## 3. Runtime And Status Projection

- [x] 3.1 Update `active_ui_task_catalog` to expose active-set authority, scope kind, target ids, operation targets, and stale-residue boundaries.
- [x] 3.2 Update route-state snapshot authority/background entries to mirror active-set target semantics.
- [x] 3.3 Ensure user-facing status can distinguish focus/default target, background active blocks, all-active operations, and stale history without internal-only wording.

## 4. Tests

- [x] 4.1 Add focused runtime tests for legal A/B parallel runs without a global main line.
- [x] 4.2 Add tests for block-scoped agents under one Flow block and target ownership.
- [x] 4.3 Add negative tests for stale index residue, missing target ids, missing authority metadata, and accidental all-run operation semantics.
- [x] 4.4 Register the focused tests in the appropriate fast/router tier if not already covered.

## 5. Validation

- [x] 5.1 Run focused active-set runtime tests.
- [x] 5.2 Run FlowGuard control-plane friction checks and update generated JSON.
- [x] 5.3 Run model-test alignment checks and focused tier tests.
- [x] 5.4 Run Meta and Capability regressions in background under `tmp/flowguard_background/`, then inspect final exit/meta/stdout/stderr/combined artifacts.
- [x] 5.5 Run a read-only live audit against the current workspace and report whether active-set warnings remain.

## 6. Sync And Finalization

- [x] 6.1 Synchronize repository-owned installed FlowPilot skill after source validation.
- [x] 6.2 Run install check and local install sync audit after synchronization.
- [x] 6.3 Record FlowGuard adoption and predictive KB postflight notes.
- [x] 6.4 Review git diff, stage intended files only, and commit local git state without pushing, publishing, tagging, deploying, or archiving.
