## 1. Model And Contract

- [x] 1.1 Add a focused FlowGuard model/check for control-plane ledger consolidation hazards.
- [x] 1.2 Add OpenSpec-linked runtime tests for daemon-owned scheduler folding, transient ledger contention, stale passive waits, and batch wait role projection.

## 2. Runtime Ownership

- [x] 2.1 Normalize daemon-critical JSON write verification/read-back access denial into retryable write-in-progress behavior.
- [x] 2.2 Route scheduler row reconciliation through a Router-owned fold lane and avoid independent foreground scheduler writes while daemon mode owns the run.
- [x] 2.3 Preserve receipt durability and action-local metadata when scheduler folding is deferred.

## 3. Projection Cleanup

- [x] 3.1 Make Controller/daemon decisions prefer Controller action ledger authority over conflicting legacy `pending_action` fields.
- [x] 3.2 Derive worker batch missing roles from active packet/batch member state before event-name role inference.
- [x] 3.3 Supersede stale passive/current-scope wait rows whose prerequisite row or phase has already resolved.

## 4. Verification And Sync

- [x] 4.1 Run focused FlowGuard checks and router runtime tests for the touched control-plane paths.
- [x] 4.2 Run heavyweight Meta and Capability regressions in the background using `tmp/flowguard_background/` artifacts and inspect completion evidence.
- [x] 4.3 Run install checks, sync the repo-owned FlowPilot skill into the local installed version, and audit local install freshness.
- [x] 4.4 Review git status and prepare a scoped local git commit if the repository is clean enough to commit without overwriting peer work.
