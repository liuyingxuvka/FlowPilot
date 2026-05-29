## 1. Contract And Model

- [x] 1.1 Create the `generate-new-flowpilot-formal-entrypoint` OpenSpec change.
- [x] 1.2 Record that this is a new FlowPilot formal entrypoint, not an old-system migration.
- [x] 1.3 Add a FlowGuard model for startup UI -> sealed intake -> new ledger -> dynamic lease -> FlowGuard -> review -> closure.
- [x] 1.4 Include hazard states for old router authority, monitoring UI requirement, fixed six roles, body leakage, headless formal overclaim, ACK-only completion, and fake-live overclaim.

## 2. Implementation

- [x] 2.1 Add `skills/flowpilot/assets/flowpilot_new.py` as the fresh formal entrypoint.
- [x] 2.2 Reuse the old native startup intake UI script from the new entrypoint.
- [x] 2.3 Record startup UI output into the new current-run ledger with sealed body authority.
- [x] 2.4 Bootstrap the new route and first PM packet without reading old route state.
- [x] 2.5 Add command surfaces for dynamic lease recording, ACK, result submission, FlowGuard evidence, review, validation, closure, and status.
- [x] 2.6 Update `SKILL.md` so fresh formal `Use FlowPilot` points at the new entrypoint.

## 3. Validation

- [x] 3.1 Add focused tests for startup UI reuse, sealed ledger entry, PM packet creation, public projection isolation, and fake end-to-end closure.
- [x] 3.2 Test that headless startup output is rehearsal-only and cannot prove formal startup.
- [x] 3.3 Run the new FlowGuard entrypoint model and write its result artifact.
- [x] 3.4 Run OpenSpec validation, focused pytest, install checks, and existing complete-system regressions.
- [x] 3.5 Sync local installed FlowPilot skill and audit source freshness.

## 4. Completion

- [x] 4.1 Update version and changelog.
- [x] 4.2 Update install inventory for new entrypoint files and result artifacts.
- [x] 4.3 Record FlowGuard adoption and KB postflight observations.
- [x] 4.4 Commit the local git result without push, tag, release, or deploy.
