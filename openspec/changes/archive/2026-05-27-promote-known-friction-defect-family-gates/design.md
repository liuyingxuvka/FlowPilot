## Context

The previous `harden-known-friction-regression-gates` change made six
historical FlowPilot control-plane failure classes hard regression rows. That
was necessary but not quite the new FlowGuard bar: repeated or high-risk
same-class model misses should also become explicit defect-family gates.

## Decisions

1. **Reuse the known-friction parent matrix.**
   The accepted rows already identify the historical bad case, source class,
   model obligation, runtime surface, runtime test, replay fixture, child
   evidence, forbidden shortcuts, and confidence boundary. A parallel registry
   would duplicate ownership.

2. **Derive one defect-family gate per accepted friction row.**
   Each row is already a recurring or high-risk dirty family. The gate id is
   derived from the friction id, and the gate consumes the row's model
   obligation and runtime authority boundary.

3. **Use FlowGuard's recurring model-miss helper directly.**
   `review_defect_family_gates(...)` checks promotion, observed failure,
   same-class generalized case, historical holdout, proof freshness, external
   scope, and scoped confidence. FlowPilot does not reimplement those rules.

4. **Use Risk Evidence Ledger for final confidence.**
   The known-friction matrix can still explain scoped boundaries, but the final
   full/scoped/blocked decision comes from `review_risk_evidence_ledger(...)`.

5. **Do not broaden live semantic claims.**
   Existing rows intentionally say the evidence does not prove arbitrary live
   AI semantic quality or unbounded production stress. The defect-family gate
   gives full confidence only for the named bounded dirty family.

## Risks

- If future rows omit family metadata, validation should fail before a broad
  confidence claim is made.
- If proof is progress-only, stale, or internal-only, both the defect-family
  gate and the risk ledger should block.
- If a future historical issue is adjacent but not the same class, it should
  be added as a new family or an explicit same-class case, not hidden under an
  unrelated row.
