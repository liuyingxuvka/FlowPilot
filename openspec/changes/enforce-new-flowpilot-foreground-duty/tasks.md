## 1. Model And Spec Grounding

- [x] 1.1 Preserve the observed model miss: scoped closure completed while an open later packet remained and foreground stop was still possible.
- [x] 1.2 Add or update a FlowGuard foreground-duty model covering process-next-action, wait patrol, recovery/blocker, scoped closure continuation, and terminal return.
- [x] 1.3 Add model-miss bad cases for final return with an open packet, passive wait treated as completion, and scoped closure mistaken for project completion.

## 2. Runtime Implementation

- [x] 2.1 Implement foreground duty derivation for the new runtime from ledger, lifecycle guard, dynamic leases, and router next action.
- [x] 2.2 Add final-return preflight that blocks final answers unless current guard/duty state is terminal.
- [x] 2.3 Convert ACK/result quiet waits into explicit timed `wait_patrol` duty payloads.
- [x] 2.4 Ensure scoped closure immediately recomputes and persists the next foreground duty.
- [x] 2.5 Persist duty snapshots and patrol history without exposing sealed packet or result bodies.

## 3. Prompt And Terminology Cleanup

- [x] 3.1 Update `SKILL.md` so the new runtime path uses foreground duty and final-return preflight instead of old Router daemon standby wording.
- [x] 3.2 Clarify terminology for status projection, startup display, lifecycle guard, foreground duty, and legacy monitor.
- [x] 3.3 Keep old Router daemon guidance only as legacy/diagnostic guidance, not as required new-runtime authority.

## 4. Test And Rehearsal Coverage

- [x] 4.1 Add unit tests for open-packet final-return rejection and terminal final-return acceptance.
- [x] 4.2 Add unit tests for ACK/result wait patrol duty and repeated-action recovery/blocker duty.
- [x] 4.3 Extend fake AI rehearsal to assert scoped closure continues to later work or wait patrol.
- [x] 4.4 Add model-test alignment evidence that tests cover each foreground-duty obligation.

## 5. Validation And Sync

- [x] 5.1 Run OpenSpec validation/status checks for this change.
- [x] 5.2 Run real FlowGuard package audit and foreground-duty/model-miss checks.
- [x] 5.3 Run focused unit tests and fake AI rehearsal checks.
- [x] 5.4 Run required broader project regressions in background artifacts where practical.
- [x] 5.5 Sync the local installed FlowPilot skill from the repository and audit the installed version.
- [x] 5.6 Inspect git status and record the final verification boundary.
