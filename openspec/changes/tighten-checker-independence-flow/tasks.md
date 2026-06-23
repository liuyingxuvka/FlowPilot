## 1. Runtime Flow Tightening

- [x] 1.1 Add a shared target-result producer check for Reviewer and FlowGuard checker packets.
- [x] 1.2 Reject or replace same-agent checker assignments during role resolution and leasing.
- [x] 1.3 Mechanically block same-agent checker submissions from already-open illegal leases.
- [x] 1.4 Close `parent_backward_replay` task results after FlowGuard pass without creating a second Reviewer packet.
- [x] 1.5 Confirm active blocker projections already use current-effective blockers, and adjust only if a current decision path still reads stale rows.

## 2. Focused Tests And Model Coverage

- [x] 2.1 Add core runtime tests for FlowGuard operator self-check assignment rejection and submission blocking.
- [x] 2.2 Add non-regression tests proving Reviewer and FlowGuard role reuse remains allowed for different producers.
- [x] 2.3 Add parent backward replay regression coverage proving FlowGuard pass closes replay and no second Reviewer packet is issued.
- [x] 2.4 Add or update scenario/model coverage for checker independence and current blocker projection.
- [x] 2.5 Run focused runtime, route, blocker, and complete-system tests.

## 3. Verification, Sync, And Local Git

- [x] 3.1 Validate the OpenSpec change with strict validation.
- [x] 3.2 Run required FlowGuard model/check regressions, using background artifacts for long checks.
- [x] 3.3 Rebuild and check the FlowGuard project topology if touched artifacts require it.
- [x] 3.4 Sync the repository-owned FlowPilot skill to the local installed skill and run install audits/checks.
- [x] 3.5 Record FlowGuard adoption evidence and commit the scoped local changes without touching peer-agent work.
