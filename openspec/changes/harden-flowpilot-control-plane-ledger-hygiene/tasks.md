## 1. Regression Fixtures First

- [x] 1.1 Add core runtime regressions for dirty `accepted_result_id`, review-blocked accepted pointers, assignment-repair resurrection, and terminal hygiene blocking.
- [x] 1.2 Add PM FlowGuard acceptance regressions proving `decision=accept` waits for Reviewer/System acceptance before packet `accepted_result_id` is written.
- [x] 1.3 Add repair-chain identity regressions proving gate-derived `pm_flowguard_acceptance` and Reviewer packets inherit `repair_blocker_id`.
- [x] 1.4 Add break-glass closure regressions proving open incidents and pending permanent-fix patches block final closure and terminal return.
- [x] 1.5 Add final Reviewer authorization regressions proving final/backward replay Reviewer packets include non-empty required `authorized_result_reads`.
- [x] 1.6 Add historical/synthetic DataBank run replay fixtures for the observed `packet-0205/result-0209/event-5616`, missing repair identity, open break-glass, stale active blocker, and empty final Reviewer authorization chain.

## 2. Runtime Control-Plane Repairs

- [x] 2.1 Change `pm_flowguard_acceptance` handling so PM `decision=accept` records absorption and issues review without early `_accept_packet_result`.
- [x] 2.2 Add an internal accepted-result pointer invariant helper and apply it to assignment repair, accepted route evidence, backward chain, closure, and terminal preflight consumers.
- [x] 2.3 Harden `review_result` and `repair_accepted_packet_assignment` so they cannot leave or recreate accepted packet state around review-blocked/rejected results.
- [x] 2.4 Pass `repair_blocker_id` from PM decision gates into `pm_flowguard_acceptance` packets and verify downstream review/recheck inheritance remains strict.
- [x] 2.5 Add whole-ledger terminal hygiene checks for stale active blockers, dirty accepted pointers, failed review/validation contradictions, open break-glass incidents, and pending permanent-fix patches.
- [x] 2.6 Build final/backward Reviewer authorized evidence bundles through existing `authorized_result_reads` for final route-node and terminal replay packets.

## 3. Prompt And Card Alignment

- [x] 3.1 Update runtime-generated PM FlowGuard acceptance instructions to state that PM `decision=accept` is not final acceptance.
- [x] 3.2 Update Reviewer/final replay instructions to require active inspection, authorized body checks, FlowGuard/validation review, and blocker return when required material is missing.
- [x] 3.3 Update Controller break-glass guidance so temporary repair can restore normal flow but cannot support clean closure before disposition and validation are resolved.

## 4. FlowGuard And Fake-AI Coverage

- [x] 4.1 Update FlowGuard control-surface, blocker-repair, break-glass, runtime-closure, recursive-closure, and model-test-alignment models for the repaired obligations.
- [x] 4.2 Expand fake-AI/D-card Cartesian axes for result status, accepted pointer state, repair identity, packet family, blocker state, break-glass state, reviewer authorization state, and closure phase.
- [x] 4.3 Add coverage-matrix and synthetic trace rows tying every generated control-plane ledger hygiene cell to a runtime reaction and evidence owner.
- [x] 4.4 Ensure old/fallback/compatibility paths remain absent and add negative cases for any removed or rejected surface.

## 5. Verification And Sync

- [x] 5.1 Run each command in `verification-contract.yaml` that targets the new focused runtime and synthetic tests; fix failures before broad checks.
- [x] 5.2 Run the required FlowGuard model checks and update result artifacts only from current passing commands.
- [x] 5.3 Rebuild and check FlowGuard project topology after model/test/runtime/card changes.
- [x] 5.4 Sync the installed local FlowPilot skill/runtime from the repository and run install/audit checks.
- [x] 5.5 Run `openspec verify harden-flowpilot-control-plane-ledger-hygiene` and keep the change open if verification is not current.

## 6. Final Review

- [x] 6.1 Inspect the full git diff, preserve unrelated peer-agent changes, and separate this change's evidence from the concurrent high-standard context change.
- [ ] 6.2 Run KB postflight and record a structured observation if this repair exposes a reusable model-miss or FlowPilot control-plane lesson.
- [ ] 6.3 Report completed changes, checks, skipped checks, residual risk, and install/Git sync status in Chinese.
