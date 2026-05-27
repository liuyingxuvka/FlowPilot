## 1. Baseline And Safety

- [x] 1.1 Confirm the previous ACK/busy-state OpenSpec change is complete and keep its source changes as the baseline.
- [x] 1.2 Keep a non-runtime backup snapshot of the current router and router runtime test file.
- [x] 1.3 Verify real FlowGuard import and record a FlowGuard adoption note for this refactor.
- [x] 1.4 Launch long Meta and Capability regressions in the background using the repository artifact contract.

## 2. Low-Risk Facade Extraction

- [x] 2.1 Extract stable runtime constants/protocol tables into helper modules while preserving facade exports.
- [x] 2.2 Extract router path helpers into a helper module while preserving existing path outputs.
- [x] 2.3 Extract JSON/write-lock/runtime-file helpers into a helper module while preserving lock behavior.
- [x] 2.4 Run import, compile, focused router tests, and install self-check for the low-risk extraction.

## 3. Controller Ledger Boundary

- [x] 3.1 Extract Controller-facing constants and patrol command formatting helpers.
- [x] 3.2 Keep Controller receipt and scheduled-action reconciliation in the router because the behavior-preserving seam is not clean yet.
- [x] 3.3 Add focused boundary tests and reuse existing Controller ordinary-work versus passive-wait tests.
- [x] 3.4 Run focused Controller/dispatch/scheduler checks.

## 4. Card ACK And Return Settlement Boundary

- [x] 4.1 Extract single-card and bundle ACK identity/status helpers.
- [x] 4.2 Keep write-bearing wait-row reconciliation and return-settlement finalizers in the router after seam review.
- [x] 4.3 Add or move focused tests for ACK-only clearance and output-bearing work remaining busy.
- [x] 4.4 Run focused ACK, dispatch-recipient, and two-table scheduler FlowGuard checks.

## 5. Packet/Mail, Startup, Daemon, And Terminal Boundaries

- [x] 5.1 Extract the static mail sequence table where no packet schema or authority behavior changes.
- [x] 5.2 Keep startup/bootloader stateful helpers behind the existing router facade for this pass.
- [x] 5.3 Extract standby/patrol constants and command helpers behind the existing CLI commands.
- [x] 5.4 Extract terminal status tables while preserving facade and terminal completion semantics.
- [x] 5.5 Stop high-coupling startup/daemon/settlement seams and leave deeper behavior-bearing extraction for a separate OpenSpec change.

## 6. Test Suite Restructure

- [x] 6.1 Add a boundary-specific router helper test file.
- [x] 6.2 Keep the existing end-to-end router runtime test suite as the facade/CLI integration suite.
- [x] 6.3 Run the split/focused test suites and attempt the broad router runtime suite; broad runtime timed out after 15 minutes and is recorded as residual evidence gap.

## 7. Final Verification And Sync

- [x] 7.1 Run all relevant focused FlowGuard checks for touched boundaries.
- [x] 7.2 Inspect background Meta and Capability regression artifacts and rerun or fix failures as needed.
- [x] 7.3 Run `python scripts/check_install.py` and `python scripts/smoke_autopilot.py --fast`.
- [x] 7.4 Synchronize the installed local FlowPilot skill and verify source freshness.
- [x] 7.5 Update install checks and adoption notes to reflect the new module boundaries.
- [x] 7.6 Validate the OpenSpec change and mark tasks complete only after evidence passes.

## 8. Git And Postflight

- [x] 8.1 Review the final diff for accidental behavior changes, backup leakage, cache files, or generated noise.
- [x] 8.2 Stage and commit the completed maintenance work locally.
- [x] 8.3 Record KB postflight observation if the refactor exposed reusable lessons or misses.
