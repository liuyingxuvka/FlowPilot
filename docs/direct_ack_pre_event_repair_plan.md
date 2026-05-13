# Direct ACK Pre-Event Repair Plan

## Risk Intent Brief

Use FlowGuard for this change because it modifies Router event ingress,
durable return-ledger state, ACK validation, and control-blocker creation.
The protected harm is accepting work out of order, accepting an invalid card
ACK, or blocking a valid role event after a valid direct ACK is already present
on disk.

## Optimization Sequence

| Step | Optimization Point | Concrete Change | Proof Before Production Change |
| --- | --- | --- | --- |
| 1 | Model the pre-event ACK race | Represent the state where a direct card ACK file exists before a later role event but the return ledger is not yet resolved. | FlowGuard known-bad hazard fails for single-card and card-bundle ACKs. |
| 2 | Model implementation hazards | Add explicit hazards for invalid ACK acceptance, incomplete bundle acceptance, role-wait authority loss, duplicate completed-return writes, and wrong pending-return selection. | Each hazard must fail with a named invariant. |
| 3 | Prove target Router order | Add a safe path where Router validates and consumes a pending ACK before creating an unresolved-card-return blocker for a later role event. | FlowGuard safe graph has no invariant failures or stuck states. |
| 4 | Implement one ingress reconciliation helper | Reuse existing card and bundle ACK validation helpers from the direct ACK path; do not create a parallel validator. | Targeted router runtime tests prove valid ACKs are consumed before event blocking. |
| 5 | Preserve hard blockers | Missing, invalid, wrong-role, wrong-hash, and incomplete bundle ACKs must still block the incoming role event. | Runtime tests cover invalid/incomplete ACKs and legacy record-event ACK rejection. |
| 6 | Preserve role-event authority | Pre-event ACK consumption must not clear the unrelated `await_role_decision` authority that makes the incoming event legal. | Runtime test records a role event envelope immediately after pre-consuming a valid ACK. |
| 7 | Preserve idempotency | Pre-event ACK consumption must not write duplicate `completed_returns` entries or re-open resolved returns on retry. | Runtime test repeats the event path and checks the return ledger. |
| 8 | Sync local surfaces | After tests pass, synchronize the local installed FlowPilot skill and verify the local install. | `install_flowpilot.py --sync-repo-owned`, audit, and check pass. |

## Bug Risks To Catch First

| Risk | What Could Go Wrong | FlowGuard Coverage |
| --- | --- | --- |
| R1 | Router still blocks a valid role event even though a valid ACK file is already present. | `valid_card_ack_file_precedes_unresolved_role_event_block` |
| R2 | Router accepts a role event after seeing an invalid, wrong-role, or wrong-hash ACK. | `pre_event_ack_rejects_invalid_or_incomplete_ack` |
| R3 | Router accepts a role event after an incomplete card-bundle ACK. | `pre_event_ack_rejects_invalid_or_incomplete_ack` |
| R4 | Router consumes the ACK but clears the unrelated role-event wait, causing the incoming event envelope to fail authority checks. | `pre_event_ack_preserves_role_wait_authority` |
| R5 | Router writes duplicate completed-return entries when the same ACK path is encountered more than once. | `pre_event_ack_consumption_is_single_matched_resolution` |
| R6 | Router consumes the wrong pending return when more than one pending return exists. | `pre_event_ack_consumption_is_single_matched_resolution` |
| R7 | Router accepts the role event before marking the return ledger resolved. | `valid_card_ack_file_precedes_unresolved_role_event_block` |

## Minimal Production Repair Shape

Add one Router event-ingress reconciliation step after lifecycle-preempting
events and before unresolved-card-return blocker creation:

1. Inspect the current first pending card return.
2. If no direct ACK file exists, keep the current blocker behavior.
3. If an ACK file exists, validate it through the existing card-runtime
   validation path.
4. If validation resolves the return ledger, continue processing the incoming
   role event without clearing unrelated role-event authority.
5. If validation fails or the bundle ACK is incomplete, preserve the blocker
   behavior.

This keeps the return ledger as the source of truth while closing the timing
gap between file-system ACK arrival and Router ledger resolution.
