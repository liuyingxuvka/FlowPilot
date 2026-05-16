## Context

FlowPilot already writes `await_role_decision` rows with `allowed_external_events`. When one of those events arrives, Router clears `pending_action`, but the durable Controller action row can remain `waiting`. That is why the live run showed two truths at once: PM had already returned a decision, while an old wait row still said Controller was waiting for that same decision.

Other active changes are adding a Router scheduler table and stateful receipt postconditions. This change plugs into that direction: Controller rows stay simple, Router scheduler rows stay authoritative, and external events become the evidence that closes wait rows.

## Goals / Non-Goals

**Goals:**
- Close any open `await_role_decision` Controller action whose `allowed_external_events` contains a newly recorded event.
- Mark the corresponding Router scheduler row reconciled from the external event.
- Apply the same reconciliation for normal event recording, already-recorded idempotent events, and Router-discovered durable evidence.
- Make the FlowGuard model catch stale wait rows and next-step advancement before stale waits are closed.

**Non-Goals:**
- Do not rewrite packet runtime, role-output runtime, or control-blocker policy.
- Do not make Controller responsible for dependency planning or event progression.
- Do not run the heavyweight meta/capability models unless explicitly requested.

## Decisions

1. Router closes waits from event evidence.

   A wait row is satisfied when it is open, its action type is `await_role_decision`, and the recorded event is in its `allowed_external_events`. Router marks that row complete with `completion_source=router_external_event_reconciliation`, records the event name, and updates the scheduler row to `reconciled`.

2. Wait rows do not require Controller receipts.

   Executable Controller actions still need Controller receipts. External-event wait rows are different: the role or PM event is the completion evidence. The action entry records that receipt is not required for this wait class.

3. Reconciliation is idempotent.

   If the same event is replayed or already recorded, Router may still close stale matching wait rows. Replaying the same reconciliation does not create duplicate actions or events.

4. FlowGuard models the ledger row, not only `pending_action`.

   The previous model represented the current wait but not the durable Controller wait row lifecycle. The upgraded model adds the missing row state and hazards for stale rows.

## Risks / Trade-offs

- [Risk] Marking wait rows done without a Controller receipt could be confused with executable Controller work. -> Mitigation: set explicit receipt-not-required metadata only for external-event wait rows.
- [Risk] Replayed events could close unrelated waits. -> Mitigation: require exact membership in `allowed_external_events`.
- [Risk] Existing live runs may already contain stale wait rows. -> Mitigation: the idempotent already-recorded path also runs the closure pass.
