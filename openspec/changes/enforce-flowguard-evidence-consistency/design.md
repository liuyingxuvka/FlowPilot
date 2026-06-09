## Context

FlowPilot is a current-contract runtime with no compatibility or fallback
acceptance path. Recent live runs showed a current-shaped FlowGuard result that
set top-level `passed: true` while its machine-readable self-check or child
FlowGuard reports said the work was blocked. The runtime accepted the result
because the packet/result contract checked field presence, forbidden old fields,
and top-level outcome, but did not bind child hard evidence status to the final
FlowGuard outcome.

The ownership split remains unchanged:

- Runtime/router owns mechanical validity: schema shape, field presence,
  hashes, current packet/result ids, current run scope, supported packet
  families, and machine-readable consistency.
- FlowGuard owns process/model/state review: whether the modeled boundary,
  checks, evidence, and residual risks support progress.
- Reviewer owns human quality review after runtime has accepted mechanics and
  FlowGuard hard evidence is internally consistent.

## Goals / Non-Goals

**Goals:**

- Reject current-shaped FlowGuard result packets when top-level `passed` or
  work-order pass conflicts with self-check or child hard evidence.
- Model the evidence-status chain from child reports to FlowGuard result to
  Reviewer handoff.
- Add same-class fake AI and synthetic trace failures so tests no longer only
  reject old shapes.
- Preserve the new-only single path: blocked hard evidence returns to current
  FlowGuard repair/reissue/block handling, not Reviewer and not a legacy parser.

**Non-Goals:**

- Do not restore old FlowPilot decision/summary formats.
- Do not make Reviewer validate required fields, hashes, child report status, or
  other mechanical facts.
- Do not add a broad compatibility layer that translates contradictory output
  into a valid result.
- Do not add per-scenario candidate ledgers when the existing packet/result gate
  can own the repair.

## Decisions

1. **Use one current-contract hard consistency gate in the FlowGuard result
   path.** The gate runs after normal JSON/field checks and before result
   acceptance, FlowGuard work-order pass recording, or Reviewer packet issuance.
   This keeps one path: submit current FlowGuard result -> mechanical shape check
   -> evidence consistency check -> accept/block.

2. **Treat evidence consistency as mechanical validity, not human review.**
   A machine-readable child report saying `ok=false`, `BLOCKED`,
   `missing_code_contract`, or `revalidation_required` is not a subjective
   quality judgement. Runtime can reject the result without asking Reviewer to
   rediscover the contradiction.

3. **Prefer existing fields first, add only one compact derived status if
   needed.** The minimum implementation should first enforce already-present
   `contract_self_check` booleans and structured report status fields. If child
   artifacts are not reliably machine-readable from the submitted result body,
   add one behavior-bearing `evidence_consistency` object to the FlowGuard
   result contract rather than scattering many specialized fields.

4. **Bind models and tests to the same owner contract.** FieldLifecycleMesh
   records the child status fields and projection; information-flow alignment
   verifies the status reaches the FlowGuard outcome before Reviewer; model-test
   alignment binds the obligation to runtime tests and fake AI replay.

5. **Use observed plus same-class negative tests.** One fixture should replay
   the observed family where child reports block but top-level `passed=true`.
   Additional synthetic cases should cover failed self-check, missing/unreadable
   child report, and old generic decision output.

## Risks / Trade-offs

- **Risk: over-adding fields.** Mitigation: require one compact derived status
  only if existing structured fields cannot make the gate deterministic.
- **Risk: live in-progress runs may have already submitted contradictory
  accepted results.** Mitigation: after code/tests pass, inspect active runs and
  use the current packet/control path to reissue or block the affected FlowGuard
  responsibility rather than accepting old evidence.
- **Risk: scoped tests pass while live evidence still fails.** Mitigation:
  include fake current-shaped contradiction replay and inspect the two active
  FlowPilot runs after installation/sync.
- **Risk: FlowGuard project evidence becomes stale after model changes.**
  Mitigation: rerun the affected model checks, topology check, install checks,
  and targeted pytest before claiming completion.
