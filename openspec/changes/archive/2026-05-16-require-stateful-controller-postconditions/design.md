## Context

FlowPilot currently uses Controller receipts both for ordinary Controller-local
work and for stateful work that changes Router-visible startup/runtime facts.
The live blocker happened because `confirm_controller_core_boundary` produced a
minimal `done` receipt, but the Router-visible confirmation artifact and flags
were absent. The persistent Router daemon model did not distinguish that action
from a generic receipt-only action.

## Goals / Non-Goals

**Goals:**
- Make stateful Controller receipt handling use the same ledger/table contract
  as later route work: Router issues the action, Controller performs the work,
  Router reconciles only after the required evidence exists.
- Ensure `done` means both receipt present and postcondition evidence satisfied
  for actions that declare a postcondition.
- Keep the production repair narrow: centralize receipt reconciliation instead
  of adding one-off blockers around each observed action.

**Non-Goals:**
- Do not change release, publish, install, or deployment behavior.
- Do not rerun heavyweight `meta_model` or `capability_model` regressions for
  this focused model and design update.
- Do not make display/status Controller actions into hard postcondition gates.

## Decisions

1. Use an action-level postcondition contract.

   Stateful Controller actions will carry a Router-owned postcondition contract
   such as "controller boundary confirmation artifact exists and flags are
   synced." Generic Controller actions keep the existing receipt-only flow.
   This avoids making every Controller receipt heavy while preventing stateful
   receipts from masquerading as complete.

2. Reconcile through a shared postcondition validator.

   Router receipt reconciliation should dispatch stateful action types through a
   small validator table before clearing the action. For
   `confirm_controller_core_boundary`, the validator reclaims an already valid
   `startup/controller_boundary_confirmation.json`, validates the confirmation
   context, and syncs `controller_role_confirmed`,
   `controller_role_confirmed_from_router_core`, and
   `controller_boundary_confirmation_written`. If the artifact is missing,
   Router marks the original row incomplete and issues a Controller repair row;
   it does not silently write the Controller deliverable during receipt
   reconciliation.

3. Prefer reclaim, then bounded repair, then blocker.

   If a receipt arrives before a Router-owned artifact flag is synced, Router
   first checks whether valid durable evidence already exists and reclaims it.
   Missing evidence becomes a `complete_missing_controller_deliverable` row for
   Controller. Only after the repair budget is exhausted, or after invalid
   repair evidence, does Router create a control blocker. This keeps the fix
   root-level without turning valid half-synced states into unnecessary PM
   repair work.

4. Model the miss at the daemon/startup boundary.

   The existing reconciliation and control-plane models already contain
   abstract stateful receipt invariants. The persistent daemon model now also
   models startup boundary evidence, so this class is caught before route
   startup advances.

## Risks / Trade-offs

- Over-broad postcondition gating could slow harmless display/status work.
  Mitigation: only actions that declare a stateful postcondition use the applier
  gate.
- Router-side reclaim can hide a bad Controller receipt if the artifact writer
  is too permissive. Mitigation: appliers must validate the exact durable
  evidence and sync only the flags covered by that evidence.
- A partial implementation could fix `confirm_controller_core_boundary` but miss
  the next stateful action. Mitigation: use the shared applier table and tests
  that inject minimal `done` receipts for each stateful action type.
- Repair rows can loop if the missing deliverable never appears. Mitigation:
  each original Controller row carries a repair-attempt counter and escalates to
  a precise control blocker after two failed repair rows.
