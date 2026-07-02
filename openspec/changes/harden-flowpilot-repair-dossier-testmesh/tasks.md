## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Validate the OpenSpec change artifacts and keep the new repair dossier scope separate from the narrower active-child-lineage break-glass change.
- [x] 1.2 Record the FlowGuard development-process route decisions for plan_detailing, execution_freshness, TestMesh, Model-Test Alignment, and install sync.
- [x] 1.3 Reconcile current dirty runtime/test changes before editing so peer or prior work is preserved.

## 2. Runtime Repair Dossier

- [x] 2.1 Add the smallest current-contract repair dossier state surface or projection with one owner and one update path.
- [x] 2.2 Create/update the dossier when blockers, PM decisions, repair packets, FlowGuard checks, reviewer rechecks, route mutations, and normal recovery occur.
- [x] 2.3 Preserve superseded-by-route-mutation blockers in the dossier until normal recovery or explicit closure.
- [x] 2.4 Classify dossier result ids as context-only or current-evidence.
- [x] 2.5 Add current-run material authorization gap fields only where runtime can act on them.

## 3. Role-Scoped Authorization

- [x] 3.1 Add one repair-context authorization helper that derives role-scoped reads from the active dossier.
- [x] 3.2 Wire PM repair decision and PM node-acceptance-plan packets to dossier reads and repair depth.
- [x] 3.3 Wire worker repair packets to blocker reason, PM repair decision, failed repair context, and required material refs.
- [x] 3.4 Wire FlowGuard repair packets to the current subject and repair obligation context.
- [x] 3.5 Wire reviewer packets to the current subject, matching FlowGuard, current evidence, and prior blocker/review reports.
- [x] 3.6 Prove normal non-repair packets remain minimally authorized.

## 4. Blocker Routing And Subject Alignment

- [x] 4.1 Enforce `missing_required_information` as same-packet material reissue or stop/control-block, not ordinary route repair.
- [x] 4.2 Enforce `missing_matching_flowguard_report` as matching FlowGuard issuance or block.
- [x] 4.3 Enforce `evidence_gap` as current evidence production, not PM plan text.
- [x] 4.4 Reject PM plan bodies and historical blocked results as current repair evidence.
- [x] 4.5 Reject wrong-subject FlowGuard evidence during reviewer repair checks.

## 5. Glass-Break Simplification

- [x] 5.1 Replace same-text/same-status blocker threshold logic with same-dossier same-parent repair-node depth.
- [x] 5.2 Trigger Controller break-glass at five consecutive repair nodes without normal business-node recovery.
- [x] 5.3 Ensure PM plan pass and reviewer plan review do not reset recovery.
- [x] 5.4 Prevent sixth ordinary repair packet/node after threshold.

## 6. Prompt And Contract Surfaces

- [x] 6.1 Update PM repair and PM node-plan cards with repair depth, blocker-chain, hard next-action, and material-authorization rules.
- [x] 6.2 Update worker cards so repair workers read blocker/PM/reviewer context but must produce fresh current evidence.
- [x] 6.3 Update reviewer cards so repair reviewers check current subject, matching FlowGuard, and prior blocker closure.
- [x] 6.4 Update FlowGuard cards so FlowGuard checks current evidence subjects rather than PM plan text.
- [x] 6.5 Update Controller break-glass guidance to use same-dossier repair depth.

## 7. Cartesian TestMesh And Unit Coverage

- [x] 7.1 Add repair dossier context unit tests.
- [x] 7.2 Add role-scoped authorization Cartesian tests for role, packet family, repair depth, and authorization state.
- [x] 7.3 Add normal-path privacy tests proving non-repair packets are not parent-wide open.
- [x] 7.4 Add fixed blocker next-action routing tests for every supported blocker class.
- [x] 7.5 Add context-only evidence rejection tests.
- [x] 7.6 Add reviewer subject-alignment and matching-FlowGuard tests.
- [x] 7.7 Add same-dossier glass-break depth tests for depths 0, 1, 2, 4, 5, and 6.
- [x] 7.8 Add observed repair-loop replay test for the June 28 failure pattern.
- [x] 7.9 Add repair TestMesh model/check script and result artifact.

## 8. Model-Test Alignment And Regression

- [x] 8.1 Update blocker repair information-flow model obligations for repair dossier context.
- [x] 8.2 Update project-control information-flow model obligations for repair-chain role authorization.
- [x] 8.3 Update model-test alignment rows for repair dossier, blocker routing, reviewer subject alignment, and glass-break.
- [x] 8.4 Run focused unit tests required by the verification contract and fix failures.
- [x] 8.5 Run focused FlowGuard checks required by the verification contract and fix failures.
- [x] 8.6 Rebuild and check FlowGuard project topology if model, test, card, or result surfaces changed.

## 9. Install Sync And Final Evidence

- [x] 9.1 Run source-side install self-check before sync if required by changed surfaces.
- [x] 9.2 Sync repository-owned FlowPilot files to the installed local skill.
- [x] 9.3 Run local install sync audit after sync, serialized after the sync command.
- [x] 9.4 Run install check after sync.
- [x] 9.5 Re-run OpenSpec verification or the equivalent verification-contract command set.
- [x] 9.6 Inspect git status and report changed files without reverting unrelated work.

## 10. Stage-Precedence Reduction

- [x] 10.1 Narrow the plan-as-evidence specification so PM node-acceptance plans are not blocked merely because the repair dossier contains future worker-evidence obligations.
- [x] 10.2 Trim runtime and Reviewer wording so `review_window` owns current-stage requirements and `repair_dossier_context` remains historical context only.
- [x] 10.3 Add Cartesian TestMesh and unit cells covering PM plan-stage subjects, worker/result-stage subjects, plan-only evidence, current worker evidence, and claimed-completion cases.
- [x] 10.4 Re-run focused OpenSpec, FlowGuard, and unit validation for the repair dossier stage boundary.
