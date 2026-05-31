## 1. Contract And Model

- [x] 1.1 Create the `unify-new-flowpilot-work-packet-lifecycle` OpenSpec change.
- [x] 1.2 Add requirements for symmetric packet lifecycle across PM, explicit FlowGuard officer, Reviewer, and requested worker-class responsibilities.
- [x] 1.3 Add FlowGuard model coverage for role-packet order, forbidden side-command completion, and lease/status cleanliness.

## 2. Implementation

- [x] 2.1 Add packet kinds and subject/result references to the new runtime.
- [x] 2.2 Make `submit-result` advance task -> FlowGuard officer -> review -> system validation -> system closure.
- [x] 2.3 Ensure every backend role can be leased only through its issued packet.
- [x] 2.4 Close leases after accepted packet results so status has no stale active reviewer/operator rows.
- [x] 2.5 Remove direct command guidance from the formal FlowPilot skill path.

## 3. Validation

- [x] 3.1 Add tests that reproduce the live-run FlowGuard officer lease failure before repair.
- [x] 3.2 Add tests that reviewer status projection has packet id and ACK before review result and no active dirty lease after system closure.
- [x] 3.3 Update fake end-to-end rehearsal to use only lease/ACK/result packet operations.
- [x] 3.4 Add a real black-box fake-project rehearsal that starts through the startup UI script, drives the public CLI packet chain, and covers wrong-role, missing-ACK, ACK-only, and retired side-command error flows.
- [x] 3.5 Run OpenSpec, FlowGuard model checks, focused pytest, model-test alignment, install checks, and local install sync.

## 4. Completion

- [x] 4.1 Update version, changelog, install inventory, and FlowGuard adoption notes.
- [x] 4.2 Commit the local git result without push, tag, release, or deploy.
