## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, clean git state, and peer-agent coordination boundaries.
- [x] 1.2 Inventory existing synthetic replay, hard-gate, router daemon, packet, terminal, and background proof evidence.
- [x] 1.3 Define finite full-flow chaos phases, injected error sequences, protected invariants, recovery routes, and final states.

## 2. Matrix

- [x] 2.1 Add an end-to-end synthetic chaos coverage matrix script and result JSON.
- [x] 2.2 Add matrix rows for happy path, startup/daemon gating, worker bad-then-repair, PM repair bad-then-corrected, background progress-only-then-final, parallel run isolation, and terminal overclaim-then-clean-closure.
- [x] 2.3 Add known-bad matrix cases for missing phase, evidence, protected invariant, recovery route, final state, and progress-only final proof overclaim.
- [x] 2.4 Add tests for matrix completeness, bounded confidence text, evidence role classification, and known-bad rejection.

## 3. Runtime Full-Flow Replay

- [x] 3.1 Add a golden full-flow replay test that reaches clean terminal closure through existing Router/runtime helpers.
- [x] 3.2 Add a worker bad-package then repaired-package replay.
- [x] 3.3 Add a PM repair bad-package then corrected-repair replay.
- [x] 3.4 Add a background progress-only proof then final-proof replay.
- [x] 3.5 Add a parallel-run isolation replay with cross-run stop or stale authority attempt.
- [x] 3.6 Add a terminal overclaim then clean-closure replay.
- [x] 3.7 Fix any discovered runtime acceptance, recovery, isolation, or closure bug without weakening hard invariants.

## 4. TestMesh and Alignment

- [x] 4.1 Register the new matrix and replay tests in the fast parent tier.
- [x] 4.2 Update tier assertions so future changes cannot silently drop the full-flow chaos evidence.
- [x] 4.3 Refresh model-test alignment evidence so the new rows are visible to FlowGuard confidence checks.
- [x] 4.4 Record FlowGuard adoption evidence with commands, results, skipped steps, and scoped confidence.

## 5. Validation

- [x] 5.1 Run focused matrix generation and matrix tests.
- [x] 5.2 Run focused full-flow replay tests.
- [x] 5.3 Run hard-gate and synthetic replay tests that the new parent evidence consumes.
- [x] 5.4 Run fast tier and affected router child tiers, using background artifacts only when final exit artifacts exist.
- [x] 5.5 Run Meta and Capability model regressions in background and inspect final artifacts.
- [x] 5.6 Validate the OpenSpec change strictly.

## 6. Sync and Finalization

- [x] 6.1 Synchronize repository-owned local FlowPilot skill.
- [x] 6.2 Run install sync audit, install check, and check_install serially.
- [x] 6.3 Perform predictive-KB postflight and record a structured observation if this work exposes a reusable lesson or route gap.
- [x] 6.4 Commit local git state without pushing, publishing, tagging, deploying, or archiving.
