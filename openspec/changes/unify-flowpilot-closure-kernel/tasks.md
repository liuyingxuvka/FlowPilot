## 1. Inventory And Model

- [x] 1.1 Inventory high-risk local closure checks across Controller, Router waits, role delivery, ACK returns, packet lifecycle, PM/reviewer packages, and terminal scans.
- [x] 1.2 Update FlowGuard closure-related models with same-class non-Controller closure drift hazards.
- [x] 1.3 Run focused FlowGuard closure checks and record current result artifacts.

## 2. Runtime Closure Kernel

- [x] 2.1 Add a small internal closure-kernel helper under `skills/flowpilot/assets/`.
- [x] 2.2 Route current-scope pre-review blocker classification through the closure kernel.
- [x] 2.3 Route the highest-risk wait/ACK/controller reconciliation call sites through the closure kernel without changing sealed-body or semantic gate boundaries.

## 3. Regression Coverage

- [x] 3.1 Add focused tests for resolved/reconciled Controller rows, non-Controller closed rows, identity mismatch, and unknown/incomplete evidence.
- [x] 3.2 Run focused runtime tests and Python import/compile checks for touched modules.

## 4. Validation And Sync

- [x] 4.1 Start heavyweight FlowGuard meta/capability regressions in the repository background-log format and inspect completion artifacts.
- [x] 4.2 Sync the local installed FlowPilot skill from the repository and run install freshness/audit checks.
- [x] 4.3 Update FlowGuard adoption evidence and this OpenSpec task list with completed work.
- [x] 4.4 Review git status, preserve peer-agent changes, and create the requested local git version if validation passes.
