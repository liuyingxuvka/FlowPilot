## Context

`flowpilot_router_controller_scheduler_receipts_packet_folds.py` reconciles
Controller `done` receipts from Router-visible evidence. The core behavior is
already covered by the Controller receipt evidence-fold FlowGuard model: if the
Router can verify packet/result relay evidence, the fold may satisfy the
Router-owned postcondition flag and update lifecycle projections; if evidence
is missing, the fold must remain unsatisfied.

The remaining maintainability issue is not a missing feature. Both
`_apply_parallel_batch_receipt_lifecycle` and
`_apply_pm_role_work_receipt_lifecycle` re-derive the same lifecycle target:
packet dispatch means `packet_relayed`; result relay means either
`result_relayed_to_pm` or `result_relayed_to_reviewer`.

## Goals / Non-Goals

**Goals:**

- Shorten duplicate lifecycle decision paths without changing observable
  receipt-fold behavior.
- Keep the decision as a small policy value that is easy to inspect and test.
- Preserve all distinct business branches: packet dispatch, result relay,
  control blocker delivery, PM role-work, and non-PM role-work remain distinct.

**Non-Goals:**

- Do not split files just to reduce line count.
- Do not change the receipt evidence registry.
- Do not widen Controller visibility into sealed packet or result bodies.
- Do not merge packet dispatch with result relay evidence validation.
- Do not change public imports or action types.

## Decisions

### Decision 1: Create a lifecycle policy helper, not another module

The selected contraction is local to one owner file. A helper such as
`_receipt_lifecycle_policy(spec)` can return the record status, timestamp
field, batch status, and officer lifecycle status for supported lifecycle
folds. Keeping it local avoids a facade or ownership split for a small internal
policy.

Alternative considered: move lifecycle folding to a new module. Rejected
because the user goal is branch pruning, not file splitting, and the current
public owner remains appropriate.

### Decision 2: Keep evidence validation branches separate

The policy applies only after evidence is already satisfied. Packet dispatch
still validates packet envelopes, relay/open/lease/batch evidence, and result
relay still validates result envelopes and next-recipient relay. Those are
different business branches and should not be merged.

Alternative considered: create one generic evidence validator. Rejected
because it would blur packet and result proof obligations.

### Decision 3: Test the policy directly and through existing runtime checks

The helper gets a focused source-level test for packet dispatch and reviewer
result relay status selection. Runtime receipt-fold tests remain the behavior
evidence for observable state.

## Risks / Trade-offs

- Incorrect policy mapping could silently write the wrong lifecycle status.
  Mitigation: direct policy test plus existing receipt-fold runtime tests.
- Overclaiming branch equivalence could hide distinct business behavior.
  Mitigation: limit the policy to post-evidence lifecycle writeback and keep
  validation branches separate.
- Background checks could be mistaken for completion evidence. Mitigation:
  inspect exit-bearing artifacts before claiming completion.
