## 1. Preflight And Ownership

- [x] 1.1 Confirm current FlowGuard package, project audit, OpenSpec status, and repository coordination state.
- [x] 1.2 Inventory existing FlowPilot contract, evidence, reviewer, blocker, break-glass, model-mesh, synthetic coverage, and model-test alignment owners.
- [x] 1.3 Record the model-miss classification and same-class generalized contract-exhaustion case family.

## 2. Contract Exhaustion Matrix

- [x] 2.1 Add or extend a FlowGuard-backed contract-exhaustion model for current FlowPilot packet/result/evidence/reviewer/repair/loop contract families.
- [x] 2.2 Add fixture/baseline builders for required contract families and fail when a current family lacks a builder.
- [x] 2.3 Generate missing-body, missing-field, wrong-type, wrong-target, missing-authorized-read, missing-evidence, evidence-path-mismatch, empty-required-manifest, reissue-inheritance, and repeated-no-delta matrix cells.
- [x] 2.4 Emit machine-readable matrix results with cell id, family id, mutation kind, expected oracle outcome, owner surface, and evidence status.

## 3. Runtime Control-Plane Repair

- [x] 3.1 Ensure formal FlowGuard reissues preserve or regenerate current packet-owned evidence output policy.
- [x] 3.2 Ensure missing current packet-owned FlowGuard evidence blocks before result acceptance can support downstream review.
- [x] 3.3 Ensure accepted FlowGuard result, packet outcome, work-order decision, evidence artifact, reviewer authorized reads, reviewer manifest, and system validation cannot diverge silently.
- [x] 3.4 Ensure reviewer packets are not issued when matching FlowGuard evidence is required but the manifest or authorized read is missing.
- [x] 3.5 Ensure PM/control repair packets include concrete missing-field, missing-evidence, owner, and target guidance instead of no-delta repeat instructions.
- [x] 3.6 Extend break-glass loop identity to count same-root-cause no-delta loops across changing surface blocker classes without triggering on ordinary repair progress.

## 4. Tests And FlowGuard Evidence

- [x] 4.1 Add the observed regression test for FlowGuard reissue evidence-policy loss, accepted-result/work-order split, empty reviewer manifest, and system-validation failure.
- [x] 4.2 Add same-class contract-exhaustion tests covering generated finite field/body/path/evidence/reviewer/reissue/no-delta variants.
- [x] 4.3 Add parent closure tests for FlowGuard evidence consistency and current child evidence id consumption.
- [x] 4.4 Add break-glass root-cause loop tests for renamed surface blockers and non-triggering ordinary repair progress.
- [x] 4.5 Update ModelMesh, TestMesh, synthetic coverage, and Model-Test Alignment artifacts/results to consume the new matrix evidence.

## 5. Validation, Sync, And Cleanup

- [x] 5.1 Run targeted unit tests for the changed runtime/control-plane paths.
- [x] 5.2 Run affected FlowGuard model checks and model-test alignment checks.
- [x] 5.3 Rebuild and check FlowGuard project topology.
- [x] 5.4 Run install/smoke/local-sync checks and sync the installed FlowPilot skill.
- [x] 5.5 Inspect unfinished or untracked OpenSpec changes and complete or report their final disposition.
- [x] 5.6 Perform predictive KB postflight and record any reusable model-miss or process lesson.

## 6. Historical Failure And Handoff Consumption Tightening

- [x] 6.1 Add history-derived missing-body, mail/body-loss, wrong-address, stale-context, vanished-evidence, install split-brain, invalid repair-target, and repeated-blocker families to the matrix.
- [x] 6.2 Treat GlassBreak as an alarm only: prove five same-root repeats are detected, but fail any accepted rehearsal that reaches GlassBreak instead of normal repair.
- [x] 6.3 Require each history-derived family to name a normal repair route and keep `glass_break_allowed_in_acceptance` false.
- [x] 6.4 Derive TestMesh child-suite requirements from every generated `required_evidence_owner`, including `contract_exhaustion_historical_failure_matrix`.
- [x] 6.5 Bind the owner-consumption handoff to Model-Test Alignment, synthetic coverage, and layered boundary proof.
- [x] 6.6 Rerun targeted contract-exhaustion, synthetic coverage, model-test alignment, and layered-boundary tests after the handoff-consumption repair.

## 7. Live-Run Replay And Zero-Blocker Acceptance

- [x] 7.1 Add OpenSpec requirements that current live-runtime findings and `control_plane_stuck` block final coverage claims.
- [x] 7.2 Treat current `lifecycle_guard.decision=control_plane_stuck` as blocking in process-liveness and ModelMesh projections.
- [x] 7.3 Add hard regression tests proving current stuck guard cannot be reported as continuable or expected green.
- [x] 7.4 Repair or explicitly dispose the stale repo-local current run through the official FlowPilot runtime path, without manual ledger edits.
- [x] 7.5 Regenerate model evidence so coverage inventory has zero `live_runtime_or_state_findings` and the full-leaf gate is current.
- [x] 7.6 Rerun targeted tests, affected FlowGuard checks, OpenSpec validation, topology checks, and install/local-sync checks.
