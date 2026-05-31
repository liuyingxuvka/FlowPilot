## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Create the OpenSpec change for removing fixed FlowGuard runner recommendations.
- [x] 1.2 Keep proposal, design, specs, and tasks internally consistent.
- [x] 1.3 Ground validation in the existing FlowGuard source repo model and project-audit checks.

## 2. Runtime And Skill Contract

- [x] 2.1 Remove `recommended_runner_commands` from runtime-issued FlowGuard operator packets.
- [x] 2.2 Keep run-local evidence root and tracked-baseline protection in packet policy.
- [x] 2.3 Update skill guidance so FlowGuard operator selects or creates suitable evidence without fixed runner hints.
- [x] 2.4 Recognize `verdict` and `flowguard_report.ok=false` as blocking structured outcomes.

## 3. Regression Tests

- [x] 3.1 Update new-entrypoint tests for the no-fixed-runner packet contract.
- [x] 3.2 Add core-runtime tests for `verdict: blocked` and nested failing FlowGuard reports.
- [x] 3.3 Update semantic outcome alignment checks if they track parser obligations.

## 4. Validation And Sync

- [x] 4.1 Run focused unit/model checks for the changed behavior.
- [x] 4.2 Run relevant FlowGuard/project checks and inspect failures.
- [x] 4.3 Sync installed FlowPilot skill from source and audit freshness.
- [x] 4.4 Recheck git status and record the final local state without reverting peer work.
