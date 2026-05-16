## 1. Contract And Model

- [x] 1.1 Record the OpenSpec proposal/design/spec for the startup reconciliation self-block fix.
- [x] 1.2 Extend the focused current-scope FlowGuard model with passive wait self-block coverage.
- [x] 1.3 Run the focused FlowGuard check and preserve the result JSON.

## 2. Runtime Fix

- [x] 2.1 Patch startup pre-review reconciliation to ignore passive wait status rows.
- [x] 2.2 Add a focused Router runtime regression proving the wait clears when it is the only remaining row.
- [x] 2.3 Preserve blocking for ordinary unreconciled startup Controller work.

## 3. Validation And Sync

- [x] 3.1 Validate the OpenSpec change with strict validation.
- [x] 3.2 Run focused pytest coverage and non-heavy background regressions, skipping Meta and Capability by user request.
- [x] 3.3 Sync and audit the local installed FlowPilot skill.
- [x] 3.4 Review the combined peer-agent worktree and create the local git commit if the combined state is commit-ready.
