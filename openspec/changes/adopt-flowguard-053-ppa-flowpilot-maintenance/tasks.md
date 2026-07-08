## 1. Project Upgrade And OpenSpec Grounding

- [x] 1.1 Run the FlowGuard 0.53 project upgrade and inspect all modified adoption artifacts.
- [x] 1.2 Rerun FlowGuard project audit and confirm the installed engine, schema, and project record agree.
- [x] 1.3 Validate the OpenSpec change with the new verification contract and task list.

## 2. PPA/BCL Maintenance Model

- [x] 2.1 Add a FlowPilot maintenance model that uses real FlowGuard Primary Path Authority and Behavior Commitment Ledger APIs.
- [x] 2.2 Cover package/result/blocker repair paths as current-contract primary paths with no fallback, alias, or old-field acceptance.
- [x] 2.3 Bind the PPA/BCL model to risk gates, coverage shards, and test receipts.
- [x] 2.4 Add a runner that fails on blocked/scoped PPA or BCL findings and writes inspectable JSON evidence.

## 3. Field Lifecycle And Packet Review Evidence

- [x] 3.1 Review PM-visible role summary and authorized-result-read surfaces against field lifecycle ownership.
- [x] 3.2 Add tests proving unsupported field expansion is rejected and runtime does not generate semantic summaries.
- [x] 3.3 Add tests proving required read surfaces are mechanical requirements, not runtime semantic review.
- [x] 3.4 Update or finish the existing PM-visible role summary OpenSpec evidence without adding fallback fields.

## 4. Model-Test Alignment And Synthetic Coverage

- [x] 4.1 Add the new PPA/BCL and field lifecycle evidence to FlowPilot model-test alignment.
- [x] 4.2 Rerun synthetic fake-agent coverage and confirm all global D-card families remain covered.
- [x] 4.3 Refresh topology when model, test, or evidence surfaces change.

## 5. Regression, Install Sync, And Release Evidence

- [x] 5.1 Run routine and release-relevant FlowPilot/FlowGuard regression checks required by the verification contract.
- [x] 5.2 Run long meta/capability checks with final background log artifacts when needed.
- [x] 5.3 Sync the repo-owned FlowPilot skill installation and verify installed/local digest parity.
- [x] 5.4 Inspect final git status and keep peer-agent untracked paths unstaged and untouched.

## 6. Closure

- [x] 6.1 Update FlowGuard adoption notes with the current upgrade, checks, skipped items, and evidence boundaries.
- [x] 6.2 Run OpenSpec strict validation for this change and all changes.
- [x] 6.3 Record KB postflight if this work exposes reusable maintenance lessons.
- [x] 6.4 Commit only the scoped FlowPilot maintenance changes.
