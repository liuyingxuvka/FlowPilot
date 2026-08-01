# FlowPilot milestone-renewal budget

This budget keeps the mandatory top-level milestone audit visible without
turning every route node into a heavyweight global review.

## Gate shape

Every completed top-level milestone has one hard renewal gate:

1. PM audits the completed prefix, deviations, remaining gaps, and emits the
   complete remaining route to the final goal.
2. FlowGuard challenges the renewed route against the current model.
3. PM absorbs the FlowGuard findings into one current candidate.
4. Reviewer accepts or blocks the whole renewal claim.
5. The local runtime validates and binds machine-owned commit material.
6. The local runtime atomically activates the accepted route.

That is exactly four AI-role submissions and two local mechanical steps. A
clean pass has zero retries. A challenge creates one new candidate cycle; it
does not edit the already accepted route in place.

Nested child completion is deliberately outside this global gate. It closes
locally and returns control to its parent route. This is what prevents a deep
tree from multiplying whole-goal audits at every leaf.

## Evidence window

The PM may see the semantic completed-prefix projection, but it is authorized
to read only the current milestone evidence plus the immediately previous
accepted milestone audit. It does not reopen every historical result body.
The runtime, not PM, binds the current contract hash and the completed rows'
evidence references during commit.

The executable budget check uses three current evidence bodies and at most one
previous audit body, so the authorized read count remains at four for 10, 50,
and 100 top-level milestones. The previous audit and packet naturally grow
with the semantic completed prefix; the count of separately reopened evidence
bodies does not.

## Accepted budgets

- Route sizes: 10, 50, and 100 top-level milestones.
- Sampled hard gates: first, middle, and penultimate milestone.
- Contract/packet staging p95: at most 250 ms locally.
- Four-role payload plus two mechanical-step p95: at most 500 ms locally.
- Authorized evidence-result reads: at most four per hard gate.
- Largest 100-milestone transport payload: at most 15 times the largest
  10-milestone payload, which admits bounded linear semantic growth but rejects
  runaway super-linear expansion.

Run:

```text
python simulations/run_flowpilot_milestone_renewal_budget_checks.py
```

The result is a deterministic local transport and conformance measurement. It
does not include provider/network latency and is not evidence that a live AI
will produce a high-quality plan; model regressions, prompt contracts, and the
longitudinal public-CLI rehearsal own those separate claims.
