## 1. OpenSpec And FlowGuard Scope

- [x] 1.1 Validate this OpenSpec change strictly before production edits.
- [x] 1.2 Record the FlowGuard model-miss classification as input-branch
  missing plus evidence overclaim: direct conflict rejection was covered, but
  repair-owned daemon replay was not.
- [x] 1.3 Identify the existing model boundaries to extend rather than adding
  a parallel ownership model.

## 2. Model And Evidence Expansion

- [x] 2.1 Extend event-idempotency and/or control-plane friction models with
  package-disposition conflict replay after active control-blocker ownership.
- [x] 2.2 Extend the same model family with package-disposition conflict replay
  after PM repair-decision ownership.
- [x] 2.3 Add or update a known-friction defect-family gate for package
  disposition conflict replay, with scoped-confidence rules.
- [x] 2.4 Update model-test alignment so the new obligations require observed
  regression and same-class generalized test evidence.

## 3. Runtime Repair

- [x] 3.1 Add or reuse a shared scoped-event conflict classifier that can
  distinguish new conflict, already-recorded replay, control-blocker-owned
  stale conflict, PM-repair-owned stale conflict, terminal quarantine, and
  unknown corruption.
- [x] 3.2 Route role-output ledger replay through that classifier before a
  repair-owned stale conflict can raise a fatal daemon error.
- [x] 3.3 Preserve the hard body-conflict rule: stale different-body evidence
  is never accepted as a successful package disposition.
- [x] 3.4 Preserve the current legal PM/control-blocker or follow-up producer
  wait when stale conflicting evidence is replayed.

## 4. Runtime Tests

- [x] 4.1 Add focused tests for material-scan same-package different-body
  replay after active control blocker.
- [x] 4.2 Add focused tests for material-scan same-package different-body
  replay after PM repair decision or repair transaction.
- [x] 4.3 Generalize the tests across research and current-node package
  dispositions.
- [x] 4.4 Add daemon replay or restart-level coverage proving the daemon stays
  live and the legal wait remains visible.

## 5. Verification And Sync

- [x] 5.1 Run focused runtime tests and FlowGuard event-idempotency,
  control-plane friction, repair-transaction, known-friction, and model-test
  alignment checks for touched obligations.
- [x] 5.2 Launch heavyweight Meta and Capability checks in the documented
  background artifact format and inspect stdout, stderr, combined, exit, meta,
  timestamp, and proof-reuse status before claiming completion.
- [x] 5.3 Sync repo-owned FlowPilot installed skill, then run install audit and
  install check.
- [x] 5.4 Run final OpenSpec validation, git scope review, and KB postflight.
