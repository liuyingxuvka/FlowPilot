## 1. Authority, Scope, And Baseline

- [x] 1.1 Upgrade the project FlowGuard record from 0.58.5 to the installed 0.61.0 and pass project audit.
- [x] 1.2 Build and bootstrap the first observed ModelSystemSnapshot from all 165 checked-in topology model/runner entries and the current behavior ledger with zero coverage gaps.
- [x] 1.3 Run full existing-model preflight and bind the change to existing control-plane friction, idempotency, daemon, progress, workstream, validation, TestMesh, and ModelMesh owners.
- [x] 1.4 Capture a reproducible baseline for no-change router writes, duplicate history/action effects, daemon result size, validation artifact bytes, combined-stream duplication, and representative wall time.
- [x] 1.5 Inventory task-owned paths and recheck peer/untracked changes before each implementation group; do not modify or stage unrelated AI work.

## 2. FlowGuard Resource-Bounded Design

- [x] 2.1 Add the focused resource-boundedness child model with Observe, Reconcile, Persist, RecordProgress, StoreEvidence, and Retain FunctionBlocks.
- [x] 2.2 Add known-good and known-bad scenarios for no-change writes, duplicate receipts, repeated progress, copied streams, missing proof refs, and unsafe retention.
- [x] 2.3 Extend the existing control-plane friction, event-idempotency, daemon-liveness, progress-lifecycle, complete-workstream, validation-artifact, and TestMesh owners without duplicating their responsibilities.
- [x] 2.4 Add FieldLifecycleMesh coverage for removed action observation fields, compact reminder state, bounded daemon result fields, V5 proof references, and retention plan/index fields.
- [x] 2.5 Add Model-Test Alignment and TestMesh rows mapping every new resource-bound obligation to one primary code owner and current ordinary test evidence.
- [x] 2.6 Register the child model/runner/result in Meta, Capability, ModelMesh, project topology, install checks, and source inventories.

## 3. Router No-Change Persistence

- [x] 3.1 Make `save_run_state` compare canonical public state before atomic write and return a written/no-write result without weakening lock, fsync, replace, or read-back checks.
- [x] 3.2 Classify daemon tick semantic/projection/frontier deltas in memory and skip full run-state persistence on no-change ticks.
- [x] 3.3 Replace daemon `ticks[]` accumulation and terminal output with bounded counts, last/terminal tick data, and bounded anomalies.
- [x] 3.4 Make daemon status/projection writes content-aware while preserving the existing one-second relevant-file observation and current liveness authority.
- [x] 3.5 Add focused tests proving 10,000 no-change ticks preserve router-state/action/scheduler/history hash, size, count, and modification time while liveness stays current.
- [x] 3.6 Add focused tests proving one real semantic input produces exactly one state commit and the next unchanged tick produces none.

## 4. Receipt, Action, Wait, And Ledger Idempotency

- [x] 4.1 Stop `append_history` callers from recording identical deferred-fold, reminder, passive-wait, and reconciliation facts.
- [x] 4.2 Remove action `seen_count` and `last_seen_at` as current authority and use receipt/action state plus liveness status for observation.
- [x] 4.3 Reconcile receipt SHA, action state, and scheduler effect before mutation; return already-current without refreshing `updated_at`.
- [x] 4.4 Persist wait reminder state once through current receipt/wait/return owners and remove copied `wait_reminder_history` bodies.
- [x] 4.5 Rebuild controller action/passive-wait ledgers only when their semantic inventory changes and keep completed detail in existing action owner files.
- [x] 4.6 Add negative tests for conflicting same-action receipt content, unsupported observation fields, duplicate reminder/defer history, and foreign or stale owner effects.
- [x] 4.7 Prove 10,000 repeated reconciliations retain one action, one scheduler effect, and one semantic history fact.

## 5. Core Runtime, Progress, And Prompt Contraction

- [x] 5.1 Make core text/JSON projection writers content-aware and compute affected projection categories only in memory.
- [x] 5.2 Append only newly identified events to `events.jsonl` without scanning and rematerializing complete event history.
- [x] 5.3 Enforce the finite progress status vocabulary and coalesce repeated identical status inside the ten-minute result-liveness window.
- [x] 5.4 Preserve status-change and due-reminder persistence plus all existing 5/10/30-minute ACK/result reminder and replacement thresholds.
- [x] 5.5 Update PM, Worker, Reviewer, FlowGuard, packet identity, post-ACK, and output-contract prompts to request progress only for semantic status changes, due reminders, and material long-command transitions.
- [x] 5.6 Keep `contract_self_check.workstream_plan_and_completion` as one obligation/phase-level table and prevent command-level rows, duplicate final plans, and reviewer plan copies.
- [x] 5.7 Add runtime and prompt tests proving coalesced progress causes zero event/count/save, status changes and due reminders persist, and complete workstream quality gates remain unchanged.

## 6. V5 Validation Evidence Normalization

- [x] 6.1 Replace line-by-line raw stream copying so stdout and stderr are the sole raw bodies and `combined.txt` is a terminal index capped at 32 KiB.
- [x] 6.2 Add stream path/hash/bytes/line counts, combined-kind, cleanup, and V2 result-fingerprint fields to terminal child metadata.
- [x] 6.3 Split supervisor state into one immutable impact plan, one bounded mutable progress file, and one terminal owner index plus existing terminal meta/exit markers.
- [x] 6.4 Replace temporary `.owner.json` bodies with exact impact-plan path/SHA/owner-id lookup and remove the temporary owner file after all readers are updated.
- [x] 6.5 Make executed owner rows reference child proof and make reused owner rows reference prior proof/ticket identity without copying raw logs, full snapshots, prior owner rows, or ticket dictionaries.
- [x] 6.6 Implement `acceptance_testmesh_evidence_manifest.v5` as the sole normal runtime contract and reject V4, missing explicit prior V5 identity, newest-manifest discovery, repo-root discovery, conversion, dual read, and dual emission.
- [x] 6.7 Bound parent/release/verification failure excerpts at 200 lines or 64 KiB while retaining immutable complete-stream references.
- [x] 6.8 Update acceptance TestMesh, impact resolution, evidence validation, report readers, fixtures, schemas, tests, and model obligations for V5.
- [x] 6.9 Add tests for altered/missing stdout or stderr, missing/duplicate/hash-mismatched owner refs, stale reuse tickets, owner inventory mismatch, cleanup-unconfirmed, and V4 normal-runtime rejection.
- [x] 6.10 Freeze source/toolchain/owner inventory and execute one explicit complete V5 seed baseline; retain its terminal owner evidence for the final gate.
- [x] 6.11 Preserve edge-by-edge process start lineage so a reused Windows parent PID cannot bridge one background owner into a younger sibling owner; cover the observed failure and same-class counterexample.

## 7. Safe Retention And Archive Lifecycle

- [x] 7.1 Extend the existing retention report across `.flowpilot/runs` and `tmp/test_background` with current/index, terminal, live owner, lease, packet/action, write-lock, reference, pin, byte, and protection fields.
- [x] 7.2 Ensure count/age limits only rank already eligible entries and that unknown, inconsistent, current, live, open, locked, referenced, pinned, or nonterminal entries fail closed.
- [x] 7.3 Implement a deterministic frozen retention plan with plan id and SHA-256; keep the default command read-only.
- [x] 7.4 Implement explicit `apply --plan ... --plan-sha256 ...` revalidation, ZIP creation, archive read-back/hash verification, index update, and post-commit heavy-subdirectory removal.
- [x] 7.5 Add recovery/rollback handling for archive creation or index-update failure without creating a second current authority.
- [x] 7.6 Add tests proving zero false archive of current/live/referenced/pinned runs, stale-plan rejection, archive read-back, index consistency, and no automatic cleanup during install/validation/release.
- [x] 7.7 Leave real historical workspace data untouched; report the tested capability rather than applying a destructive retention plan during this release.
- [x] 7.8 Split the retention implementation behind its existing facade into one read-only scan owner and one pure common kernel; pass release-scope StructureMesh parity and known-bad checks for missing ownership, duplicate state, facade/entrypoint loss, dependency cycles, stale parity, and insufficient evidence.

## 8. Focused Verification And Model Revision

- [x] 8.1 Run strict OpenSpec validation and repair every proposal/design/spec/task inconsistency.
- [x] 8.2 Run focused router, core-runtime, prompt/card, test-tier, acceptance-TestMesh, retention, install, and version tests after each affected implementation group.
- [x] 8.3 Run focused resource-boundedness, control-plane friction, idempotency, daemon, progress, workstream, validation, TestMesh, ModelMesh, Meta, and Capability model checks.
- [x] 8.4 Rebuild and check `docs/flowguard_project_topology.json` and `.md` after all model, runner, result, test, prompt, and code-owner changes.
- [x] 8.5 Build the complete candidate ModelSystemSnapshot, create one exact affected ModelRevisionSet against the then-current generation 3 authority, and activate generation 4 only after current V5 owner, final-confidence, and SkillGuard evidence passes.
- [x] 8.6 Rerun project audit and model-system audit and require current 0.61.0 parity, zero authority gaps, and the activated candidate fingerprint.

## 9. Frozen Full Validation, Installation, And SkillGuard

- [x] 9.1 Freeze the final source, version, toolchain, V5 manifest, complete owner plan, and exactly one heavy execution owner per model/test gate.
- [x] 9.2 Run the complete FlowGuard model regression owner and complete test/acceptance owner in the existing background evidence contract; continue useful verification while they run and accept only terminal meta, exit, result, fingerprint, and descendant-zero proof.
- [x] 9.3 Repair every model/test failure and rerun only affected owners until the frozen full gates pass; restart the final full gate only if frozen inputs change.
- [x] 9.4 Bump all FlowPilot source/install/release version surfaces to 0.13.0 and run version parity plus package/source boundary checks.
- [x] 9.5 Build, activate, and audit the clean local FlowPilot consumer installation; verify no `.skillguard`, author receipts, tests, models, plans, or private paths enter the installed projection.
- [x] 9.6 Re-resolve the latest current SkillGuard source/version after its concurrent maintenance settles and audit the FlowPilot author repository/unit/member boundary.
- [x] 9.7 Compile the FlowPilot SkillGuard contract, freeze its same-unit check plan with private run/evidence roots, execute missing owners once, aggregate exact terminal proof, and require enforced closure.
- [x] 9.8 Transactionally reinstall/audit the SkillGuard-graduated FlowPilot projection and require source/install/current-release identity parity.

## 10. GitHub Release And Final Closure

- [x] 10.1 Perform a phase-change predictive-KB preflight for public release and recheck GitHub authentication, remote/default-branch state, and remote tag/version availability.
- [x] 10.2 Inspect the final worktree, preserve every unrelated peer file, and stage only task-owned OpenSpec, FlowGuard, runtime, prompt, test, install, version, and documentation paths.
- [x] 10.3 Commit the frozen release source, push the current branch and fast-forward the remote default branch without rewriting peer history.
- [x] 10.4 Create annotated tag `v0.13.0` and a source-only GitHub Release with the verified change summary and validation evidence.
- [x] 10.5 Verify local HEAD, remote branch, remote default branch, tag, GitHub Release, source version, installed FlowPilot release identity, FlowGuard model head, and SkillGuard closure all agree.
- [x] 10.6 Run the explicit post-change FlowGuard maintenance scan, strict OpenSpec validation/status check, install audit, clean-release boundary audit, and predictive-KB postflight.
- [x] 10.7 Mark every task complete only from current evidence and deliver the final Chinese report with resource before/after measurements, exact checks, release URL, residual risks, and confirmation that peer work was not rolled back.
