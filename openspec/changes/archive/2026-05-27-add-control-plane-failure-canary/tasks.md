## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, clean git state, and peer-agent coordination boundaries.
- [x] 1.2 Inventory existing lock, daemon, launcher, heartbeat, resume, control-blocker, terminal-fence, and background-supervisor evidence.
- [x] 1.3 Define finite control-plane canary rows, known-bad row failures, and scoped confidence text.

## 2. Matrix

- [x] 2.1 Add a control-plane failure canary matrix script and result JSON.
- [x] 2.2 Add matrix rows for stale write lock, half-written artifact, dead daemon/launcher, duplicate heartbeat wakeup, peer-run stop isolation, and stale background proof.
- [x] 2.3 Add known-bad matrix cases for missing invariant, missing recovery route, missing standard final state, missing runnable evidence, and progress-only proof overclaim.
- [x] 2.4 Add tests for matrix completeness, confidence boundary, row classification, and known-bad rejection.

## 3. Runtime Canary Replay

- [x] 3.1 Add runtime canary tests for stale/fresh lock recovery using existing controller or background helper paths.
- [x] 3.2 Add runtime canary tests for missing, corrupt, or half-written artifact handling.
- [x] 3.3 Add runtime canary tests for dead daemon/launcher resume recovery.
- [x] 3.4 Add runtime canary tests for duplicate heartbeat or resume idempotency.
- [x] 3.5 Add runtime canary tests for peer-run stop or stale authority isolation.
- [x] 3.6 Add runtime canary tests for terminal fence or dirty state preventing normal continuation.
- [x] 3.7 Fix any exposed control-plane runtime defect without weakening hard invariants. No production runtime defect was exposed.

## 4. TestMesh and Alignment

- [x] 4.1 Register the canary matrix and runtime replay tests in the fast parent tier.
- [x] 4.2 Update tier assertions so future changes cannot silently drop control-plane canary evidence.
- [x] 4.3 Refresh model-test alignment evidence so the new canary obligation is visible to FlowGuard confidence checks.
- [x] 4.4 Record FlowGuard adoption evidence with commands, results, skipped steps, and scoped confidence.

## 5. Validation

- [x] 5.1 Run focused matrix generation and matrix tests.
- [x] 5.2 Run focused runtime canary replay tests.
- [x] 5.3 Run fast tier and affected Router child tiers, using background artifacts only when final exit/meta artifacts exist.
- [x] 5.4 Run Meta and Capability model regressions in background and inspect final artifacts.
- [x] 5.5 Validate the OpenSpec change strictly.

## 6. Sync and Finalization

- [x] 6.1 Synchronize repository-owned local FlowPilot skill.
- [x] 6.2 Run install sync audit, install check, and check_install after sync.
- [x] 6.3 Perform predictive-KB postflight and record a structured observation if this work exposes a reusable lesson or route gap.
- [x] 6.4 Commit local git state without pushing, publishing, tagging, deploying, or archiving.
