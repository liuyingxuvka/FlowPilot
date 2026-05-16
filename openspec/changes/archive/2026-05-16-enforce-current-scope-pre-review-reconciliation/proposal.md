## Why

FlowPilot review gates lose meaning when a reviewer is asked to judge a startup gate or current node while hidden local obligations can still change the review package. The Router needs a durable current-scope reconciliation rule before review work begins, and before leaving scopes that do not have a final review.

## What Changes

- Add current-scope obligation reconciliation before reviewer work starts for startup and current-node review gates.
- Keep reconciliation strictly local to the active startup gate or active node; it must not clear future, sibling, or route-wide obligations.
- Require review-created obligations, such as reviewer card ACKs, reviewer reports, pass/block receipts, and PM follow-up disposition, to close before the scope can be completed or crossed.
- For scopes without a final review, require the same current-scope reconciliation before boundary transition.
- Preserve explicit carry-forward only when an item is intentionally transferred to a later scope with reason, target scope, owner, and join condition.

## Capabilities

### New Capabilities

- `current-scope-pre-review-reconciliation`: Defines local obligation reconciliation before reviewer work and before no-review scope transitions.

### Modified Capabilities

- None.

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected tests: focused Router runtime tests for startup/current-node pre-review waits, review-created obligation closure, and local-scope-only behavior.
- Affected models: new focused FlowGuard model/runner for current-scope pre-review reconciliation.
- Existing heavyweight regressions `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` are intentionally skipped by user request.
- Local install must be synchronized and audited after implementation.
