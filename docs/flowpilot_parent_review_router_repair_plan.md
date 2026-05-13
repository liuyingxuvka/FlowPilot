# FlowPilot Parent Review Router Repair Plan

## Goal

FlowPilot must not enter a sibling module while the previous parent/module has
completed child work but has not completed local parent backward replay and PM
segment disposition.

## Optimization Checklist

| Step | Area | Concrete change | Required evidence |
| --- | --- | --- | --- |
| 1 | FlowGuard model | Add a negative scenario where the last child leaf of module A completes, module A parent review remains incomplete, and the router enters module B leaf work. | `run_flowpilot_parent_child_lifecycle_checks.py` rejects the hazard. |
| 2 | FlowGuard model | Add an intended scenario where the last child leaf of module A completes and the next legal active node is module A for parent backward replay. | Parent-child lifecycle intended checks pass. |
| 3 | Router next-node selection | Change child completion next-node selection to check the completed leaf's parent chain before scanning sibling modules. | A focused router test proves A2 completion activates parent A, not B1. |
| 4 | Router route action authority | Preserve existing parent action policy: once parent A is active and all child ledgers are current, legal next actions must be parent backward targets, replay, PM segment decision, then parent completion. | Existing parent backward runtime tests still pass. |
| 5 | Route display | Stop rendering a parent/module as `done` solely because terminal children are complete. Render it as parent-review-ready until the parent itself is completed. | Route sign tests assert child-complete parent is not `done`. |
| 6 | Local install sync | Copy the repaired skill files into the local installed FlowPilot skill. | Install sync and local install audit pass. |
| 7 | Local git | Commit the local repository changes only. Do not push to GitHub. | Local git log contains the repair commit; remote remains untouched. |

## Bug Risk Checklist

| Risk | What could go wrong | FlowGuard/model coverage required | Runtime/test coverage required |
| --- | --- | --- | --- |
| R1 | Router still jumps from module A final leaf directly into module B leaf. | Negative scenario rejects sibling-module leaf entry before parent replay. | Focused router test checks next active node after A2 completion. |
| R2 | Router gets stuck on a parent even after replay and PM segment decision pass. | Intended parent lifecycle remains accepted through parent completion. | Existing parent completion tests still pass. |
| R3 | Router starts parent review before all children or descendant leaves are complete. | Existing child-chain and descendant-completion hazards remain rejected. | Existing parent backward target tests still pass. |
| R4 | Stale child completion ledgers count as valid parent readiness. | Existing stale route/status and old route-version hazards remain rejected. | Existing ledger-current runtime tests still pass. |
| R5 | Root or unrelated ancestor is activated as a normal parent node. | New intended scenario constrains the next node to the nearest completed parent scope, not arbitrary ancestors. | Focused router test uses sibling modules under a root. |
| R6 | Route sign says `done` when it only means child work is complete. | Model names parent-review-ready as nonterminal, not accepted parent closure. | Route display test checks not-done status before parent completion. |
| R7 | The repair breaks local installed FlowPilot while repo tests pass. | Adoption log records model and sync evidence. | Install sync check and local install audit pass after repo changes. |

## Execution Order

1. Upgrade the FlowGuard parent-child lifecycle model and check runner.
2. Run the model until known-bad hazards are rejected and intended paths pass.
3. Patch router next-node selection.
4. Add focused router regression tests and run them.
5. Patch route display status.
6. Add focused route display regression tests and run them.
7. Run the strongest practical FlowPilot regression checks.
8. Sync repo-owned skill files into the local installed skill.
9. Run install/audit checks.
10. Create a local git commit only.
