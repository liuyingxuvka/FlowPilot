## Context

FlowPilot is a current-contract runtime. The packet/result control plane
already records packets, leases, results, accepted result pointers, review
windows, validation evidence, and materialized projections. The incident class
behind this change is not missing data. It is that stale or duplicate backend
submissions can be absorbed far enough to allocate result ids and append
packet history before the runtime marks them mechanically blocked.

That ordering lets history pollution affect later code that reads the newest
historical result instead of the accepted result. It also makes background
agents believe a duplicate submission was at least processed as a normal
result, which can drive repeated old-packet retries.

Constraints:

- Use real FlowGuard and existing model/test surfaces.
- Keep one current runtime path; do not add compatibility or fallback routes.
- Do not add UI.
- Avoid new ledger fields or state families. Existing packet, lease, result,
  blocker, review, validation, and projection records must carry the fix.
- Runtime may enforce mechanical structure and currentness only. It must not
  semantically judge Reviewer prose.
- Reviewer prompts should make the Reviewer actively responsible for quality:
  open the current work and evidence, run tests or FlowGuard checks where
  useful, compare against model/spec obligations, and add review-scope tests or
  fixtures when that is the clearest way to prove a defect or prevent a shallow
  pass.
- Preserve unrelated peer-agent changes and untracked work.

## Goals / Non-Goals

**Goals:**

- Reject stale, noncurrent, inactive-lease, and already-accepted result
  submissions before creating any result record.
- Make repeated current-role dispatch idempotent while a valid current lease is
  already assigned.
- Make accepted packet readers use `accepted_result_id` as authority.
- Keep projection/materialization failures separate from business result
  submission.
- Update every current Reviewer packet/card surface so passive checklist-only
  review is disallowed by instruction, and active verification behaviors are
  named directly.
- Extend FlowGuard and regression coverage across model, runtime tests,
  fake-AI replay, D-card/contract-exhaustion rows, and model-test alignment.
- Sync repository-owned install artifacts and the local installed FlowPilot
  skill after validation.

**Non-Goals:**

- No legacy migration, old-field adapter, stale-result quarantine fallback, or
  dual authority path.
- No new Reviewer semantic scoring in runtime.
- No UI or user-facing workflow addition.
- No release, publish, deploy, or frozen acceptance-contract change.

## Decisions

1. **Move result-submission preconditions before result allocation.**

   The runtime must check packet currentness, accepted state, lease identity,
   lease status, role binding, route/run scope, and ACK/read prerequisites
   before calling the result id allocator or mutating the ledger. A failed
   precheck raises the existing runtime error class or returns the existing
   CLI error shape without creating a result row.

   Alternative considered: keep creating blocked result rows for audit. This
   is rejected because it preserves `result_ids` pollution and keeps old
   submissions looking like ordinary results.

2. **Use `accepted_result_id` for accepted-packet authority.**

   Accepted packets already have a single pointer. Review creation, validation
   recording, status projection, repair decisions, final closure, and router
   next-action code must prefer that pointer. `result_ids` remains historical
   evidence only.

   Alternative considered: keep reading `result_ids[-1]` and filter blockers.
   This is rejected because one stale append is enough to move authority.

3. **Make repeated dispatch-current-role idempotent.**

   If the current packet already has an active assigned lease for the same
   current responsibility, dispatch returns the existing lease/handoff rather
   than consuming a new assignment or superseding the active lease. Lease
   replacement stays in the modeled repair/reissue lane.

   Alternative considered: allow dispatch to supersede the previous lease. This
   is rejected for ordinary dispatch because it creates two backend contexts
   that can both attempt submission.

4. **Separate projection failures from business submission.**

   Ledger save, event log, projection, and current pointer refresh are separate
   side effects. Projection writes should be atomic, and projection failures
   should surface as projection/runtime errors. They must not invite or perform
   another business result submission.

5. **Reviewer hardening stays mechanical at runtime.**

   Runtime may reject a Reviewer result for missing required fields, empty
   required arrays, forbidden fields, noncurrent subject, missing current
   accepted result binding, missing authorized read/open receipt, missing
   evidence path, or invalid pass/block shape. Runtime must not keyword-match
   or semantically grade whether the Reviewer wrote a good challenge.

   Reviewer quality is strengthened through cards/prompts, FlowGuard model
   obligations, fake-AI bad profiles, synthetic coverage rows, and runtime
   replay of mechanically invalid cases.

6. **Reviewer packet prompts require active verification work.**

   Reviewer packets should tell the Reviewer to do the actual review work, not
   merely comment on the submitted summary. That includes opening current
   result bodies and cited evidence, checking model/spec obligations, running
   focused tests or FlowGuard checks when they are relevant and practical,
   creating or repairing review-scope tests/fixtures when existing tests do not
   cover the risk, and reporting the exact evidence used for pass/block.

   This does not make Reviewer the owner of production repair. Reviewer may add
   tests or review evidence when authorized by the packet scope, but production
   implementation fixes, PM route decisions, and FlowGuard acceptance remain in
   their existing lanes.

7. **Validation and install sync happen after focused green evidence.**

   Focused model/runtime checks run first. Broader model-test alignment,
   topology, install sync, local install audit, and install self-check run only
   after the changed surfaces are stable.

## Risks / Trade-offs

- **Risk: old tests still assert result history pollution** -> Update those
  tests first so the previous behavior fails before runtime changes are trusted.
- **Risk: raising instead of returning a blocked result affects CLI callers** ->
  Keep the existing current-contract runtime error/report surface and assert
  no ledger mutation in tests.
- **Risk: dispatch idempotency hides real stale leases** -> Reuse only an
  active lease that is already assigned to the same current packet and role;
  all mismatched, closed, superseded, or noncurrent leases still reject.
- **Risk: Reviewer hardening drifts into semantic matching** -> Keep semantic
  quality out of runtime assertions and cover generic pass behavior through
  fake-AI/model tests with mechanical currentness/evidence failures where
  applicable.
- **Risk: long regressions consume the foreground** -> Run heavyweight model
  or tier checks with the repository background artifact contract when needed,
  then inspect exit and metadata artifacts before claiming completion.

## Migration Plan

1. Add OpenSpec, FlowGuard, test, and model-test-alignment obligations.
2. Change focused tests to require hard ingress rejection without result
   allocation.
3. Update runtime submit, dispatch idempotency, authority readers, and
   projection writers.
4. Refresh fake-AI/D-card/coverage and model-test-alignment evidence.
5. Run focused checks, then broader checks, topology, install sync, local
   install audit, install self-check, and git status audit.

Rollback is ordinary source rollback before release. No migration of persisted
ledger history is introduced by this change.
