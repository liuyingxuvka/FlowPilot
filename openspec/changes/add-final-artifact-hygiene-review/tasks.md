## 1. OpenSpec And FlowGuard Planning

- [x] 1.1 Record proposal, design, specs, and task plan for final artifact hygiene review.
- [x] 1.2 Validate the OpenSpec change in strict mode before production edits are claimed complete.
- [x] 1.3 Keep the implementation inside the existing evidence-quality, final-ledger, terminal-replay, and supplemental-repair flow.

## 2. Cards And Templates

- [x] 2.1 Update Reviewer core and terminal replay cards to require `final_artifact_hygiene_review`.
- [x] 2.2 Update PM evidence quality, final ledger, review repair, and closure cards to inventory, close, repair, or disposition hygiene findings.
- [x] 2.3 Update human review, final ledger, terminal replay map, node acceptance plan, and packet body templates with explicit hygiene fields.

## 3. Runtime Contract And State

- [x] 3.1 Add current-contract hygiene findings and closure rows to the runtime ledger.
- [x] 3.2 Require terminal replay reports to include `final_artifact_hygiene_review`.
- [x] 3.3 Block terminal replay pass and terminal closure while required hygiene findings are unresolved.
- [x] 3.4 Extend terminal supplemental repair gap validation with `final_artifact_hygiene_gap` and `hygiene_category`.

## 4. FlowGuard Models And Tests

- [x] 4.1 Extend terminal supplemental repair model coverage for final artifact hygiene gaps.
- [x] 4.2 Add focused runtime tests for missing hygiene review, required hygiene blocker, supplemental contract hygiene gap, final ledger closure, and closure blocking.
- [x] 4.3 Update acceptance testmesh/model evidence for the new payload cells.

## 5. Validation, Install Sync, And Closure

- [x] 5.1 Run focused unit tests and FlowGuard checks.
- [x] 5.2 Run affected contract/runtime/fake rehearsal/model-test checks.
- [x] 5.3 Validate OpenSpec strictly after implementation.
- [x] 5.4 Sync repo-owned local FlowPilot install and run install/audit checks.
- [x] 5.5 Update adoption evidence and final git/worktree summary without reverting peer-agent changes.
