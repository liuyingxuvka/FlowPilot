## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Validate the new OpenSpec change and keep its non-goals narrow.
- [x] 1.2 Run FlowGuard package/project audit and identify the existing owning models.

## 2. Runtime Repair Loop

- [x] 2.1 Update repair-loop counting so break-glass requires same-node, same-problem, consecutive attempts over five.
- [x] 2.2 Preserve ordinary PM repair for under-threshold and cross-node similar failures.
- [x] 2.3 Keep stale repair rows out of current active-blocker/final-preflight projections while preserving history.

## 3. Ledger Persistence

- [x] 3.1 Change current run ledger writes to same-directory temp write plus atomic replace.
- [x] 3.2 Add bounded retry for transient empty/incomplete current run ledger reads.
- [x] 3.3 Ensure persistent invalid ledgers still fail clearly without fallback synthesis.

## 4. Cards And Guidance

- [x] 4.1 Update Reviewer guidance to reuse `blocker_class` for the same-node same defect.
- [x] 4.2 Update FlowGuard Operator guidance to preserve same-node problem identity.
- [x] 4.3 Update Controller/break-glass guidance to say cross-node similar failures do not trigger this threshold.

## 5. Models And Tests

- [x] 5.1 Update focused FlowGuard model/check coverage for same-node repeat, cross-node non-trigger, stale-history status, and ledger read/write stability.
- [x] 5.2 Add runtime tests for same-node over-threshold break-glass and under-threshold ordinary repair.
- [x] 5.3 Add runtime tests for cross-node similar failures not triggering break-glass and consecutive-chain reset.
- [x] 5.4 Add status/final-preflight tests for stale repair history staying noncurrent.
- [x] 5.5 Add ledger persistence tests for atomic write and transient invalid-read retry.
- [x] 5.6 Add card coverage tests for the narrow guidance.

## 6. Validation, Sync, And Git

- [x] 6.1 Run targeted FlowGuard checks and focused pytest/unittest suites.
- [x] 6.2 Rebuild and check FlowGuard topology after source/model/test/card changes.
- [x] 6.3 Sync repository-owned FlowPilot files to the installed local skill and run install audits/checks.
- [x] 6.4 Commit the completed local changes without reverting peer-agent work.
