## 1. Current Authority and Model Boundary

- [x] 1.1 Record the exact current runtime, route-plan, PM-disposition, review-window, and frontier owners for this change.
- [x] 1.2 Repair the repository's FlowGuard current-format model authority without adding a compatibility reader or fallback. The repository now has the current `.flowguard/model-regression-manifest.json`, explicit `.flowguard/**/model.py` owners, and one accepted current `ModelRevisionSet` activation.
- [x] 1.3 Update the existing route-replanning owner model with the top-level milestone hard gate and complete remaining-plan renewal.
- [x] 1.4 Add executable good and bad profiles for missing renewal, unchanged renewal, changed suffix, Reviewer block, recovery, and terminal empty plan.
- [x] 1.5 Run the focused FlowGuard model checks and inspect every counterexample before runtime implementation.

## 2. Current PM Disposition Contract

- [x] 2.1 Add the topology-derived `milestone_plan_renewal_required` projection to current PM-disposition packets.
- [x] 2.2 Add the structured `milestone_audit` semantic contract with completed outcomes, deviations, remaining gaps, prior-plan assessment, and replan rationale; keep exact evidence binding runtime-owned.
- [x] 2.3 Add the strict `remaining_route_plan` contract and terminal-only empty-plan validation.
- [x] 2.4 Validate that every currently unclosed acceptance item retains an owner in a non-empty remaining plan.
- [x] 2.5 Update minimal shapes, branch shapes, field types, allowed values, repair feedback, and fake-AI contract projection from the same owner.
- [x] 2.6 Add negative tests for missing audit fields, missing evidence, uncovered obligations, premature empty plans, and unsupported old continuation fields.
- [x] 2.7 Bind the cumulative completed top-level prefix by `completed[].node_id` and complete runtime-issued evidence refs.
- [x] 2.8 Bind every renewal audit to the runtime-owned frozen final-goal `contract_hash` at commit and every remaining gap to `owner_node_ids` in the newly emitted suffix.

## 3. Staged Milestone Hard Gate

- [x] 3.1 Stage every top-level PM `accept` as one `commit_milestone_plan_renewal` effect instead of applying it immediately.
- [x] 3.2 Bind the staged effect to current node, route version, source generation, source packet/result, and canonical remaining-plan fingerprint.
- [x] 3.3 Route the staged result through the existing FlowGuard, PM-absorption, Reviewer, and system-validation chain.
- [x] 3.4 Extend the PM FlowGuard-absorption and Reviewer window instructions to challenge the milestone audit and final-goal route continuity.
- [x] 3.5 Commit accepted milestone state and reviewed plan renewal atomically only after all gate evidence passes.
- [x] 3.6 Keep nested child PM acceptance on the existing parent-composition path without a global plan-renewal gate.
- [x] 3.7 Reject checker reuse when any required authorized input was produced by the submitting checker identity, while preserving the existing role/lease owner model.

## 4. Equality-Aware Remaining Route Activation

- [x] 4.1 Canonicalize the submitted remaining plan and the current unfinished route suffix through one current representation.
- [x] 4.2 Record fresh audit and review evidence without increasing route version when the canonical remaining plan is unchanged.
- [x] 4.3 Create one new route version when the canonical remaining plan changes.
- [x] 4.4 Preserve accepted nodes, results, reviews, validation evidence, and completed-frontier history across changed suffix activation.
- [x] 4.5 Carry forward exact unchanged unfinished nodes and supersede or quarantine removed or changed unfinished nodes and packets.
- [x] 4.6 Reject changed specifications that reuse stale executed, superseded, or non-current node identity.
- [x] 4.7 Release the next node or final-closure chain only after the reviewed renewal commit.

## 5. Recovery and Projection

- [x] 5.1 Make routing recovery re-expose the exact missing FlowGuard, PM-absorption, Reviewer, validation, or commit obligation for a staged milestone result.
- [x] 5.2 Prevent submitted, interrupted, or Reviewer-blocked milestone results from falling through to old-route frontier advance.
- [x] 5.3 Project the latest accepted milestone audit and remaining-plan fingerprint from existing route, disposition, and status owners without creating a second plan authority.
- [x] 5.4 Add recovery tests for interruption at every gate stage and rejection of historical review reuse.
- [x] 5.5 Reconcile apply-failure currentness drift by reopening one fresh renewal packet; keep internal invariant failures explicit and non-recoverable.

## 6. Skill and Architecture Projection

- [x] 6.1 Update FlowPilot skill guidance and current PM/Reviewer runtime-card projections to describe the single mandatory milestone loop.
- [x] 6.2 Remove or consolidate instructions that tell PM to continue the old route automatically after a major milestone.
- [x] 6.3 Confirm the existing node-acceptance-plan gate still owns distinct context and acceptance-projection duties; record any proven contraction as a separate affected reduction candidate.
- [x] 6.4 Update the Behavior Commitment Ledger owner entry for mandatory milestone-plan renewal and its primary-path failure boundary.
- [x] 6.5 Rebuild and check the FlowGuard project topology after model, runtime, test, and prompt ownership changes.
- [x] 6.6 State the single direct loop in the launcher and PM/FlowGuard/Reviewer cards; explicitly forbid L0-L4 tiers and alternate route/ledger authorities.

## 7. Focused and Frozen Validation

- [x] 7.1 Add focused runtime tests for top-level leaf, top-level module, nested child, unchanged plan, changed plan, empty plan, and preserved history.
- [x] 7.2 Add review-window, staged-effect, fake-AI, recovery, and final-closure conformance tests.
- [x] 7.3 Run the minimum affected unit, model, review-window, and contract checks while source is changing and fix all failures.
- [x] 7.4 Refresh FlowPilot's SkillGuard contract source, compiled contract, and exact check manifest after source and check identities are frozen.
- [ ] 7.5 Run one final SkillGuard-supervised full validation for maintenance unit `unit:flowpilot` and inspect its immutable terminal receipts.
- [ ] 7.6 Sync the validated clean consumer projection and run installed currentness plus target-owned installed smoke checks separately.
- [ ] 7.7 Run OpenSpec strict validation and record final source, model, SkillGuard, installation, Git, tag, and publication identities separately.
- [x] 7.8 Perform the predictive-KB postflight check and record one structured observation only if this work exposed a reusable lesson or route gap (event `7275fb7d-a98f-41e1-bda7-40dc2710e23a`, terminal receipt verified).
- [ ] 7.9 Collect the background model regressions under one frozen source snapshot and preserve their immutable logs without overwriting parallel results.

## 8. Post-implementation Correctness Closure

- [x] 8.1 Update the milestone contract minimal shape from the same runtime owner projection so concrete multi-node owner bindings cannot produce a self-rejecting example.
- [x] 8.2 Make changed-suffix activation reuse the existing route-mutation blocker retirement, quarantine, and evidence-invalidation lifecycle; add an active-blocker replacement regression.
- [x] 8.3 Bind renewal coverage to every exact current obligation projection, including non-route hygiene, open resources, residual risks, and legacy evidence; permit nested helper nodes without fabricated gaps.
- [x] 8.4 Bind `milestone_audit.remaining` rows to current obligation ids or an equivalent existing projection and keep owner ids within the submitted route.
- [x] 8.5 Give PM bounded authorized reads for required milestone evidence and reject submission without the corresponding current read receipts.
- [x] 8.6 Replace currentness recovery text matching with a typed currentness-drift disposition and keep invariant failures explicit.
- [x] 8.7 Add Reviewer-owned top-level milestone granularity checks for both initial and renewed routes without introducing levels, scores, flags, or a second route authority.
- [x] 8.8 Enforce milestone-renewal currentness in the lowest top-level acceptance/commit owner and frontier-advance boundary; add a direct internal-call bypass regression.
- [x] 8.9 Prove terminal empty-plan closure traverses FlowGuard, PM absorption, Reviewer, system validation, and atomic commit before final closure; remove any test shortcut that permits a missing gate packet.

## 9. Current Model and Evidence Closure

- [x] 9.1 Add the audit-discovered renewal hazards to the runner state identity and expected-failure map; regenerate the result for all current negative scenarios.
- [x] 9.2 Bind the changed-suffix implementation and gate-to-commit path to runtime production conformance and affected tests instead of source-string presence checks or the historical repair slice only.
- [ ] 9.3 Update the current FlowGuard model-regression manifest and activate one accepted current ModelRevisionSet without a compatibility reader or fallback.
- [ ] 9.4 Regenerate current TestMesh/MTA, formal AI, PPA, BCL, Risk, release-scope parent, and final-confidence evidence from one frozen source/toolchain snapshot; closure-only consumers must run after their current producers.
- [ ] 9.5 Expand the FlowPilot SkillGuard declared checks to own the new renewal model, production conformance, affected tests, and current evidence closure; run the final supervised validation under the current contract identity.
- [x] 9.6 Make the bounded background supervisor fail closed when a child disappears or exceeds its deadline without an immutable terminal receipt; preserve cleanup-unconfirmed as a release blocker and add model plus unit regressions.

## 10. Lightweight Execution and Enablement

- [x] 10.1 Keep runtime-owned machine bindings out of PM semantic prose and reduce repeated audit transport through the existing accepted-prefix projection and current milestone delta without creating a second ledger.
- [x] 10.2 Consolidate route mutation lifecycle primitives and repeated milestone prompt/card instructions without removing the hard gate, PM absorption, Reviewer, or distinct node-acceptance-plan duties.
- [x] 10.3 Run one current-version public-launcher longitudinal rehearsal covering unchanged renewal, changed suffix, nested child, Reviewer block, interruption/resume, and terminal empty plan; this is not an A/B experiment.
- [x] 10.4 Measure four AI submissions, two local system steps, retries, full packet/context and evidence-read growth, and stage/total gate latency at 10/50/100 top-level milestones; record the accepted lightweight budget in `docs/flowpilot_milestone_renewal_budget.md`.
- [ ] 10.5 Refresh the validated consumer installation, confirm the milestone renewal path is enabled as the sole current behavior, and verify source/install parity.
- [ ] 10.6 Preserve peer work, commit only owned integrated files locally, rerun OpenSpec/FlowGuard/SkillGuard closure, and report source/install/model/test/Git identities separately.
- [ ] 10.7 Update `VERSION`, `CHANGELOG.md`, and public release notes; create an immutable new commit/tag/GitHub Release, push the current branch and `main`, and verify remote branch, tag, and Release identities.
