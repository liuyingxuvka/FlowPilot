## Context

The direct `record_external_event` path already writes PM package disposition
artifacts before finalizing event flags and wait closure. The role-output ledger
reconciliation path was weaker: after validating the role-output envelope and
checking replay conflicts, it called the generic reconciled-event recorder,
which only set flags, event history, scoped idempotency, and wait closure. That
created a second event-ingress path that could bypass formal gate package
checks such as source result `contract_self_check`.

The current uncommitted quarantine patch is useful for stale replay conflicts,
but it does not fix the deeper issue by itself. A non-conflicting first replay
still needs to prove the domain commit before the router can call it progress.

## Goals / Non-Goals

**Goals:**

- Make role-output ledger reconciliation use a domain-first transaction before
  event finalization.
- Cover all PM package disposition events, not only material scan.
- Keep replay quarantine for stale or repair-owned conflicts.
- Add a regression for the exact failed-self-check pattern and a positive
  commit-path check so the guard is not merely blocking everything.

**Non-Goals:**

- Replacing the router event dispatcher.
- Changing the PM package disposition output contract.
- Reworking unrelated controller action identity, daemon, or packet runtime
  behavior.

## Decisions

1. Add the transaction guard at the reconciled-event recorder boundary.

   This is the narrowest place where all role-output ledger events converge
   before state mutation. The alternative would be to duplicate package-specific
   logic inside the ledger scan loop, but that would keep event recording and
   domain writing separated.

2. Reuse the existing PM package disposition writer for reconciled package
   events.

   The writer already validates runtime envelope authority, result absorption
   transaction registry entries, material generation, packet outcomes, PM open
   evidence, and formal gate package self-checks. Reusing it avoids a weaker
   second implementation.

3. Keep stale replay quarantine before commit.

   Conflict quarantine remains valuable because stale direct events should not
   invoke the writer and risk changing the canonical disposition. The new guard
   applies only after replay/conflict checks have accepted a candidate as the
   current event body.

4. Close the defect family with authority and ingress matrices.

   The recurring failure is not closed by a single observed regression. The
   repair must prove that PM package disposition authority cannot split across
   event idempotency, run flags, event history, active batch state, material or
   package artifacts, role-output ledger replay, daemon startup/restart, and
   repair transaction ownership. The minimum closure matrix covers direct event
   intake, role-output ledger reconciliation, daemon startup/restart replay,
   and repair-owned conflict replay over valid, missing, corrupted, and
   mismatched canonical package states.

## Risks / Trade-offs

- A historical synthetic test with incomplete packet artifacts may now fail
  earlier because reconciliation correctly requires a commit-capable package.
  Mitigation: update tests to provide realistic packet/result envelopes for
  positive commit paths and keep artificial conflict tests on the quarantine
  path.
- Existing runs with already-recorded package events but missing canonical
  package artifacts will not be silently repaired by flag replay. Mitigation:
  surface those as blocked or skipped invalid evidence so PM repair can handle
  them explicitly.
- The defect-family gate is larger than the original point fix. Mitigation:
  keep implementation changes scoped to package disposition transaction
  authority, but require broader validation evidence before claiming the
  recurrence class is closed.
