## 1. Spec And Model

- [x] 1.1 Record proposal, design, specs, and FlowGuard snapshot for terminal replay repair-loop hardening.
- [x] 1.2 Validate the OpenSpec change in strict mode.

## 2. Runtime

- [x] 2.1 Preserve terminal replay context on current-scope repair packets.
- [x] 2.2 Ensure current open terminal repair/reissue packets preempt `close_project`.
- [x] 2.3 Keep stopped/user-decision and route-redesign behavior current-contract only.

## 3. Tests And Evidence

- [x] 3.1 Add focused runtime regression for terminal block -> PM repair -> rerun -> blocker cleared -> closure.
- [x] 3.2 Add focused router regression for open terminal reissue dispatch before closure.
- [x] 3.3 Add fake E2E/current-contract regression for terminal blocker repair to completion.
- [x] 3.4 Add model-test alignment evidence rows for the full repair-return loop.

## 4. Validation And Sync

- [x] 4.1 Run focused unit tests for the new terminal repair-loop behavior.
- [x] 4.2 Run fake E2E/new entrypoint tests.
- [x] 4.3 Run FlowGuard model-test alignment and field/contract checks.
- [x] 4.4 Run relevant core/runtime/high-standard regressions.
- [x] 4.5 Rebuild/check topology and sync installed FlowPilot.
- [x] 4.6 Update adoption logs and KB postflight.
