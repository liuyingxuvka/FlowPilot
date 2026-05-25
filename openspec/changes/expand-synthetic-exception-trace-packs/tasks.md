## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, clean git state, OpenSpec validity, and peer-agent coordination boundaries.
- [x] 1.2 Inventory existing ordinary runtime tests for control blockers, PM repair, resume, route mutation, PM package disposition, material repair, and terminal dirty ledgers.
- [x] 1.3 Identify which P0/P1 branches can use real runtime APIs for synthetic replay and which require ordinary runtime evidence only.

## 2. P0 Synthetic Exception Packages

- [x] 2.1 Add synthetic replay for ACK-only semantic-work-open plus reissue/escalation boundary.
- [x] 2.2 Add synthetic replay for control blocker retry budget escalating to PM.
- [x] 2.3 Add synthetic replay for PM repair accepting a registered/receivable target.
- [x] 2.4 Add synthetic replay for PM repair rejecting invalid, stale, or non-receivable targets.
- [x] 2.5 Add synthetic replay for fatal blocker rejecting ordinary PM waiver.
- [x] 2.6 Add synthetic replay for resume active-blocker/ambiguous-state preemption.

## 3. P1 Synthetic Exception Packages

- [x] 3.1 Add synthetic replay for route mutation stale sibling proof or old packet disposal.
- [x] 3.2 Add synthetic replay for PM package disposition envelope authority and raw/manual event rejection.
- [x] 3.3 Add synthetic replay for controller boundary repair budget escalation.
- [x] 3.4 Add synthetic replay for material repair generation and stale progress flag rejection.
- [x] 3.5 Add synthetic replay for dirty terminal ledgers blocking completion.

## 4. Matrix and Gates

- [x] 4.1 Extend coverage matrix rows with risk tier, replay requirement, replay status, non-replayable reason, and covered failure mode.
- [x] 4.2 Add known-bad matrix tests for missing P0/P1 replay rows and synthetic overclaiming.
- [x] 4.3 Keep synthetic matrix in the fast tier and refresh generated JSON.

## 5. Validation

- [x] 5.1 Run focused synthetic trace and matrix tests.
- [x] 5.2 Run relevant router child suites for control blockers, resume, route mutation, PM role-work, quality gates, material modeling, and terminal closure.
- [x] 5.3 Run FlowGuard model-test alignment and fast tier.
- [x] 5.4 Run Meta and Capability full regressions in background with stable artifact inspection.
- [x] 5.5 Confirm no full diagnostic actionable findings remain.

## 6. Sync and Finalization

- [x] 6.1 Recheck git state for peer-agent writes before install sync.
- [x] 6.2 Synchronize repository-owned local FlowPilot skill.
- [x] 6.3 Run install sync audit and install check serially after sync.
- [x] 6.4 Validate OpenSpec change, mark tasks complete, and commit local git state.
- [x] 6.5 Run predictive-KB postflight and record any reusable lesson or route gap.
