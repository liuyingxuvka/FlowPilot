## Context

FlowPilot uses a two-table runtime: Router owns scheduler rows and workflow state, while Controller sees executable action rows and writes receipts. Some Controller actions are receipt-only, while stateful actions require Router-visible postconditions such as startup flags and durable display artifacts.

The audited failure showed a stateful row with complete evidence:

- Controller receipt for `write_display_surface_status` was `done`.
- Controller action and scheduler row were marked Router-reconciled.
- Display artifacts and user-dialog display ledger existed.
- `router_state.flags.startup_display_status_written` remained false.

Because next-action selection read the stale flag, Router repeatedly generated the same startup display action. Because the action was treated as nonblocking startup work, the daemon cleared/deferred it and looped instead of unblocking startup activation.

## Goals / Non-Goals

**Goals:**

- Reconcile Controller receipts and Router-owned postconditions before every next-action decision.
- Make stateful postcondition folding idempotent and safe to replay when flags drift.
- Suppress duplicate ordinary Controller commands while equivalent work is pending, running, done, or already reconciled.
- Turn unrecoverable drift into bounded repair/blocker evidence instead of a silent loop.
- Keep the fix generic for registered stateful Controller postconditions, with explicit coverage for startup display status.
- Preserve peer-agent edits already present in the focused FlowGuard model and README/version work.

**Non-Goals:**

- Do not redesign the Router daemon, packet runtime, role authority system, startup intake UI, or Cockpit behavior.
- Do not change sealed packet body boundaries.
- Do not publish a release or push to GitHub.
- Do not run repo-wide formatting or broad cleanup.

## Decisions

1. **Router decision entry starts with reconciliation.**

   The daemon/manual next-action path must first fold new receipts, scheduled receipt rows, pending action receipts, and settlement finalizers into the authoritative run state. Next-action providers must consume that settled state only.

2. **Already-reconciled does not mean postcondition can be skipped.**

   If an action entry or scheduler row says a stateful postcondition was applied but the corresponding Router-owned flag is false, reconciliation must re-apply or reclaim the postcondition before returning. If the durable evidence is invalid, it must record repair/blocker evidence.

3. **Duplicate suppression distinguishes in-flight, complete, and drifted work.**

   Equivalent Controller work that is pending/running/waiting stays in flight and is not reissued. Equivalent work that is done/reconciled with satisfied postconditions is complete and is not reissued. Equivalent work that is done/reconciled but has drifted postconditions enters reconciliation/repair and is not reissued as a normal command.

4. **Startup display uses the generic stateful-postcondition path.**

   `write_display_surface_status` remains a registered stateful Controller action with postcondition `startup_display_status_written`. The concrete display files and user-dialog ledger are proof inputs, but the durable safety property is generic: reconciled stateful postcondition implies Router-owned flag satisfaction or explicit repair/blocker.

5. **Focused model first, runtime second, heavy checks in background.**

   The existing modified focused model already captures the known-bad drift loop. Runtime changes must add a concrete regression that starts from the stale-flag/done-ledger shape and proves Router reconciles instead of requeueing. Heavy meta/capability checks may run through the repository background log contract after targeted checks pass.

## Risks / Trade-offs

- **Over-reconciliation could hide invalid evidence**: only registered postconditions may be replayed, and invalid/missing evidence must go to repair/blocker instead of blindly setting flags.
- **Too much scanning on every tick**: reconciliation stays scoped to the current run's known Controller receipts, scheduler rows, action rows, and registered artifact paths.
- **Parallel AI changes may overlap**: edits remain scoped to the reconciliation modules, startup display guard, tests, OpenSpec artifacts, and install sync evidence; unrelated README/version changes are preserved.
- **Legacy row shapes may lack complete metadata**: runtime should use existing action type/postcondition fields and degrade to the current repair/blocker lane when no safe reclaim path exists.

## Migration Plan

1. Complete OpenSpec deltas for the affected capabilities.
2. Confirm FlowGuard import and run the focused current-scope reconciliation model with the newly added drift hazards.
3. Implement idempotent stateful postcondition replay/reclaim in scheduled receipt reconciliation.
4. Add or update duplicate-dispatch guards so requeued startup display drift becomes reconciliation/repair, not a fresh ordinary command.
5. Add targeted router runtime tests for stale `startup_display_status_written` with done/reconciled startup display evidence.
6. Run focused FlowGuard and targeted runtime checks.
7. Start heavy meta/capability regressions in `tmp/flowguard_background/` and inspect exit artifacts before reporting them complete.
8. Sync the validated repository-owned FlowPilot skill into the local installed skill and run install audit/check.
