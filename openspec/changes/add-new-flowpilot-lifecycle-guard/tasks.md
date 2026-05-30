## 1. OpenSpec And FlowGuard Model

- [x] 1.1 Create OpenSpec proposal, design, specs, and implementation tasks for the lifecycle guard upgrade.
- [x] 1.2 Add a FlowGuard lifecycle-guard model for nonterminal stop prevention, resume rehydration, wait patrol, recovery classification, stale result quarantine, and terminal stop authorization.
- [x] 1.3 Extend existing new-entrypoint or fake-rehearsal model hazards so guard bypasses are detected.

## 2. Runtime Guard Implementation

- [x] 2.1 Extend the new runtime ledger with lifecycle guard, patrol history, repeated-action history, and terminal stop authority fields.
- [x] 2.2 Implement metadata-only guard snapshot derivation from current ledger, packet, lease, route, event, and next-action state.
- [x] 2.3 Make nonterminal status and patrol persist `controller_stop_allowed: false` and terminal completion persist `controller_stop_allowed: true`.
- [x] 2.4 Implement manual resume/patrol command paths on the new entrypoint without restoring old monitor UI or old router authority.
- [x] 2.5 Reject or quarantine stale/late results from inactive leases, superseded packets, or stale route/source generations.

## 3. Persistence, Projection, And CLI

- [x] 3.1 Persist guard snapshots under the current run and project them into public status without sealed bodies.
- [x] 3.2 Add public CLI commands and Python facades for `patrol` and `resume`.
- [x] 3.3 Include guard state in the startup/status/lease/ACK/result public responses.

## 4. Fake AI Rehearsal And Tests

- [x] 4.1 Add focused unit tests for nonterminal stop blocking, terminal stop authorization, manual resume, and repeated-action stuck detection.
- [x] 4.2 Add focused unit tests for missing ACK, ACK-only result waits, inactive lease recovery, and stale/late result rejection.
- [x] 4.3 Extend fake-host rehearsal so the normal path reaches terminal with stop authority and error paths remain nonterminal.
- [x] 4.4 Update model-test alignment surfaces for the new lifecycle guard files and tests.

## 5. Validation, Sync, And Close

- [x] 5.1 Run OpenSpec validation for this change and all specs.
- [x] 5.2 Run focused FlowGuard lifecycle/new-entrypoint/fake-rehearsal/model-test checks.
- [x] 5.3 Run focused unit tests and fake end-to-end smoke.
- [x] 5.4 Start heavyweight meta/capability regressions in background artifacts and inspect completion evidence.
- [x] 5.5 Bump FlowPilot version, sync the local installed skill, and run install sync/audit/check-install.
- [x] 5.6 Record FlowGuard adoption evidence, perform KB postflight, review git status, and commit the completed upgrade.
