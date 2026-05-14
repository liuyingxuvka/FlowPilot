## Context

FlowPilot now runs a one-second Router daemon that publishes Controller actions through `runtime/controller_action_ledger.json`. Controller receipts are useful local evidence, but they do not always mean the workflow item is complete. Some actions only deliver work to another role, some write Router-owned durable evidence, and some are lightweight display/status updates.

The observed failure is in this boundary: a Controller receipt for `write_startup_mechanical_audit` was marked done and the audit/proof files existed, but `startup_mechanical_audit_written` was still false. Router created a stateful postcondition blocker before reclaiming the valid Router-owned artifact.

## Goals / Non-Goals

**Goals:**

- Keep Controller action completion separate from Router workflow completion.
- Add Router-owned reconciliation before every next-action/blocker decision.
- Reclaim valid Router-owned durable artifacts from the current run before declaring a missing stateful postcondition.
- Make the startup mechanical audit failure class executable in focused tests and FlowGuard checks.
- Keep the recurring daemon tick lightweight by inspecting only known current-run action and artifact paths.

**Non-Goals:**

- Do not move the startup route-sign/display action earlier.
- Do not make Controller responsible for Router-owned workflow completion.
- Do not add screenshot or heavy evidence requirements for small Controller-only status work.
- Do not run heavyweight meta/capability model regressions for this change.

## Decisions

1. **Use two ledgers instead of overloading the Controller ledger.**
   The Controller ledger remains Controller-writable receipt state: pending, waiting, done, blocked, or skipped. A new Router ownership ledger records Router decisions such as `controller_receipt_done`, `router_reclaim_pending`, `router_reclaimed`, `waiting_for_role`, and `blocked`.

   Alternative considered: add more statuses to the Controller ledger. That keeps the original ambiguity, because a Controller-owned checkmark would still appear to represent downstream workflow state.

2. **Classify actions centrally.**
   Router will map action types to completion classes: Controller-only, Router-owned durable artifact, role delivery/wait, display/status, and stateful host action. The map keeps this from becoming a new pile of one-off blocker exceptions.

   Alternative considered: special-case only `write_startup_mechanical_audit`. That would fix the current blocker but leave the same class of problem available for the next Router-owned file.

3. **Reconcile before blocker creation.**
   `compute_controller_action()` and daemon ticks already run reconciliation before selecting new work. The new durable-reclaim step belongs in that barrier, before pending-action stateful blockers and before `router_no_legal_next_action`.

   Alternative considered: let PM repair packets handle the false blocker. That makes every normal startup carry an avoidable manual repair.

4. **Use known artifact paths, not broad scans.**
   The daemon tick will read only the pending action, controller receipt, Router ownership ledger, and registered artifact/proof paths. It will not scan the repository or require screenshots.

## Risks / Trade-offs

- **Risk:** Router could accept stale or wrong-run evidence.  
  **Mitigation:** Reclaim only when the existing proof validator confirms schema, run id, hash, owner, trusted source, and mechanical-only scope.

- **Risk:** The Router ownership ledger becomes another source of drift.  
  **Mitigation:** Rebuild or refresh entries from durable Controller receipts and known artifacts before next-action decisions; do not trust it alone.

- **Risk:** A real incomplete stateful host action could be hidden by generic reclaim.  
  **Mitigation:** Only registered Router-owned durable artifacts can be reclaimed this way. Existing hard blockers remain for unsupported stateful actions like incomplete role rehydration.

- **Risk:** The daemon tick becomes expensive.  
  **Mitigation:** Reconciliation is path-indexed and current-run scoped; full sweeps are reserved for run resume or stage transition style paths.
