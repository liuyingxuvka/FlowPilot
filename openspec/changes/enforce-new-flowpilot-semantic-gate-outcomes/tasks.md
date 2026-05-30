## 1. Contracts And Modeling

- [x] 1.1 Add OpenSpec requirements for semantic packet outcomes, active blockers, PM repair decisions, and same-class recheck.
- [x] 1.2 Add a focused FlowGuard model and runner for semantic gate-outcome lifecycle and hazards.

## 2. Runtime Implementation

- [x] 2.1 Add ledger records for packet outcomes, active blockers, PM repair decisions, and repair transactions.
- [x] 2.2 Parse reviewer, validator, FlowGuard, worker, closure, and PM repair-decision result bodies before side effects.
- [x] 2.3 Route reviewer block, validator fail, FlowGuard fail, and worker blocked/needs-PM outcomes to active blockers.
- [x] 2.4 Automatically issue PM repair-decision packets and apply PM repair decisions through existing new-runtime primitives.
- [x] 2.5 Require same-gate/same-role recheck before clearing semantic blockers.

## 3. Tests And Rehearsals

- [x] 3.1 Add focused runtime tests proving reviewer block and validator fail do not silently pass.
- [x] 3.2 Add focused runtime tests proving PM repair decisions reissue or repair the correct scope and stale failed evidence is not accepted.
- [x] 3.3 Add model-test alignment checks so the FlowGuard model's required labels are covered by ordinary tests.

## 4. Validation And Sync

- [x] 4.1 Run OpenSpec validation and FlowGuard project audit.
- [x] 4.2 Run focused FlowGuard semantic outcome checks and targeted pytest.
- [x] 4.3 Run fake end-to-end rehearsal and required new runtime checks.
- [x] 4.4 Sync repo-owned installed FlowPilot skill and run install audit/check.
- [x] 4.5 Review git status, stage/commit only scoped files, and leave unrelated existing work untouched.
