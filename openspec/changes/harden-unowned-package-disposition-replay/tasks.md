## 1. Scope And Specifications

- [x] 1.1 Add OpenSpec requirements for stale unowned PM package-disposition
  replay, canonical package authority, daemon liveness, and known-friction
  evidence.
- [x] 1.2 Validate the OpenSpec change strictly before runtime edits.

## 2. FlowGuard Model And Evidence

- [x] 2.1 Extend event-idempotency modeling with the foreground/daemon stale
  unowned package-disposition replay branch.
- [x] 2.2 Extend control-plane friction or known-friction modeling so this
  branch is a hard recurring regression gate.
- [x] 2.3 Update model-test alignment to require concrete test evidence for
  stale unowned replay, not only repair-owned replay.

## 3. Runtime Repair

- [x] 3.1 Detect stale unowned role-output package-disposition replay against
  the current canonical package artifact before fatal conflict handling.
- [x] 3.2 Quarantine or audit stale replay evidence without accepting the stale
  body as a successful package disposition.
- [x] 3.3 Preserve canonical package artifact and idempotency authority during
  daemon replay and stale run-state saves.
- [x] 3.4 Keep direct same-package different-body intake as a hard conflict
  unless an explicit repair/reissue path owns it.

## 4. Tests And Checks

- [x] 4.1 Add a focused historical regression test for newer foreground
  package commit followed by older daemon role-output replay.
- [x] 4.2 Add or update model-level tests and known-friction checks for the
  same branch.
- [x] 4.3 Run focused runtime tests and FlowGuard checks for all touched
  obligations.
- [x] 4.4 Launch heavyweight Meta and Capability regressions in the documented
  background artifact format and inspect final artifacts before claiming pass.

## 5. Sync And Finalization

- [x] 5.1 Sync the repo-owned local FlowPilot install.
- [x] 5.2 Run install audit/check commands sequentially.
- [x] 5.3 Review git scope, stage only intended files, commit locally, and
  perform KB postflight.
