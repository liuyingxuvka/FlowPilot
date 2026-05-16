## 1. Baseline And Coordination

- [x] 1.1 Run predictive KB preflight and record relevant prior lessons for this maintenance pass.
- [x] 1.2 Read repository coordination and FlowGuard-required handoff/model context.
- [x] 1.3 Verify the real `flowguard` package is importable for this environment.
- [x] 1.4 Confirm the worktree is clean, create this pass on a local maintenance branch, and keep non-runtime backup snapshots under `tmp/`.

## 2. OpenSpec And Risk Gate

- [x] 2.1 Create the OpenSpec change artifacts for the second conservative router maintenance pass.
- [x] 2.2 Validate the OpenSpec change in strict mode before marking implementation complete.
- [x] 2.3 Record a FlowGuard adoption note for this pass, including risk intent, touched boundaries, and planned checks.

## 3. Runtime Test Boundary Split

- [x] 3.1 Add focused runtime test entrypoints for ACK/return settlement, Controller reconciliation, startup/daemon, dispatch/packet gate, and terminal closure boundaries.
- [x] 3.2 Ensure focused test entrypoints reuse the existing runtime test class without duplicating test bodies.
- [x] 3.3 Add the focused test files to install self-check coverage.

## 4. Controller Reconciliation Boundary

- [x] 4.1 Inspect Controller receipt and scheduler reconciliation helpers for pure extraction seams.
- [x] 4.2 Extract only side-effect-free Controller reconciliation helpers into a boundary module.
- [x] 4.3 Preserve `flowpilot_router.py` facade compatibility for moved Controller helpers.
- [x] 4.4 Run focused Controller/runtime checks after the extraction.

## 5. ACK And Return Settlement Boundary

- [x] 5.1 Inspect ACK/return settlement helpers for pure classification or identity seams.
- [x] 5.2 Extract ACK/return side-effect-free helpers while preserving ACK-only versus output-bearing semantics.
- [x] 5.3 Preserve router facade compatibility for moved ACK/return helpers.
- [x] 5.4 Run focused ACK/runtime checks after the extraction.

## 6. Startup, Daemon, Dispatch, And Terminal Boundaries

- [x] 6.1 Extract startup/daemon table-driven or pure command/status helpers that do not own lifecycle progression.
- [x] 6.2 Extract dispatch/packet gate table-driven or pure classification helpers that do not write packet ledgers.
- [x] 6.3 Extract terminal table-driven or pure status helpers that do not close runtime state.
- [x] 6.4 Preserve router facade compatibility for all moved helpers and stop any seam that requires behavior changes.

## 7. Verification, Install Sync, And Git

- [x] 7.1 Run focused unit tests for the new helper modules and boundary runtime entrypoints.
- [x] 7.2 Run compile/import checks and `scripts/check_install.py`.
- [x] 7.3 Run applicable focused FlowGuard checks and broad Meta/Capability checks through the background artifact contract.
- [x] 7.4 Run `scripts/smoke_autopilot.py --fast`.
- [x] 7.5 Synchronize the installed local FlowPilot skill and verify install freshness.
- [x] 7.6 Review the final diff for accidental behavior changes, backup leakage, cache files, or generated noise.
- [x] 7.7 Run KB postflight, stage, and commit the completed local maintenance work.
