## Why

The router route-mutation test slice was still slow because each parent-level
assertion replayed the same child workflow: controller boot, pre-route gates,
current-node packet dispatch, worker result return, reviewer block, and
model-miss triage. Representative tests took 80-95 seconds each, and the
24-test slice had evidence of 20+ minute runtime.

This change splits that slow family by semantic ownership instead of only
moving commands into tiers. Child contract setup owns the detailed input state;
parent tests consume the bound input/output contract and exercise only the
route-mutation event and parent-owned outputs.

## What Changes

- Add a FlowGuard TestMesh contract model for slow-test parent/child splits.
- Add route-mutation child contract fixtures that bind active route, frontier,
  review-block, model-miss-triage, route-action-policy, and packet-ledger input
  state without replaying the full child workflow.
- Convert the canonical route-mutation pytest slice to fast parent contract
  tests that call the real router route-mutation event and assert parent-owned
  outputs.
- Keep the old aggregate runtime methods available as full child/oracle
  coverage for explicit or release/background runs.

## Impact

- Affected validation: route-mutation runtime pytest slice and fast
  FlowGuard/TestMesh checks.
- Affected production behavior: none.
- Affected install sync: new model, result, helper tests, and canonical slice
  are registered with install checks.
