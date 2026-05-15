## 1. Contract And Model

- [x] 1.1 Record the OpenSpec proposal/design/spec for async startup obligation join.
- [x] 1.2 Update the startup FlowGuard model so the pre-review ACK join uses the common ledger path.
- [x] 1.3 Run the focused startup optimization model checks.

## 2. Runtime

- [ ] 2.1 Teach Router to defer only startup-scope pending-card-return waits when an independent startup action can proceed.
- [ ] 2.2 Enforce the Reviewer pre-review join through the existing pending-card-return dependency blocker.
- [ ] 2.3 Preserve the same Controller action ledger and card ACK ledgers; do not add a startup-only table.

## 3. Tests And Validation

- [ ] 3.1 Add focused router tests for startup prep delivery and ACK cleanup before Reviewer review.
- [ ] 3.2 Add focused router tests for PM startup activation using the existing same-role ACK blocker.
- [ ] 3.3 Run focused router/runtime checks and OpenSpec validation.
- [ ] 3.4 Sync and audit the installed local FlowPilot skill version.

## 4. Finalization

- [ ] 4.1 Update FlowGuard adoption notes for skipped heavyweight checks and focused validation.
- [ ] 4.2 Review local peer-agent changes and include compatible work in staging.
- [ ] 4.3 Commit the synchronized local git version.
