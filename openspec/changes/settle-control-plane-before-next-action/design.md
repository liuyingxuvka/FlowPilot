## Context

Router daemon ticks already reconcile several durable evidence sources before
choosing work. The live failure showed a gap in the ordering: an active control
blocker and a queued PM repair delivery could survive after the originating
startup Controller action was later reconciled by its scheduler row and
postcondition. Once that happens, the old repair work is stale control-plane
debt, not valid PM work.

The fix must fit alongside two related active changes:

- `internalize-router-mechanical-actions` moves pure local Router work out of
  Controller rows.
- `separate-controller-receipt-action-metadata` makes Controller rows expose a
  receipt completion contract instead of an apply contract.

This change owns only the settlement ordering around blockers and next-action
selection.

## Goals / Non-Goals

**Goals:**

- Treat every Router tick as two phases: settle durable evidence to a stable
  state, then emit at most one next action.
- Resolve same-origin control blockers when the source Controller action,
  scheduler row, and postcondition are reconciled.
- Supersede queued `handle_control_blocker` Controller rows if their blocker is
  resolved before delivery.
- Keep mechanical startup postcondition misses out of PM repair until direct
  Controller repair/reissue paths are exhausted.
- Add FlowGuard and runtime tests for the observed failure and same-class race.

**Non-Goals:**

- Do not replace the Controller action ledger.
- Do not change PM, reviewer, worker, or officer authority over semantic work.
- Do not run heavyweight Meta or Capability checks in this task.
- Do not merge or rewrite the parallel OpenSpec changes.

## Decisions

1. Settlement is part of next-action computation, not a PM-specific precheck.
   - Rationale: PM repair is just one possible result after settlement. Adding
     a special PM gate would leave other stale-action races alive.
   - Alternative rejected: check only before `_next_control_blocker_action`.
     That protects one call site but not the invariant that each tick starts
     from refreshed durable state.

2. Same-origin blocker resolution uses durable identity first and startup
   postcondition fallback second.
   - Rationale: new blockers can carry Controller action id, scheduler row id,
     action type, and postcondition. Existing live blockers may only carry
     action type, so startup bootloader reconciliation needs a conservative
     fallback when the postcondition is already true.
   - Alternative rejected: resolve by action type alone for every workflow.
     That could clear unrelated repeated actions outside startup.

3. Stale blocker delivery rows become `superseded`.
   - Rationale: Controller action rows are the user's work board. If a PM repair
     delivery row was queued but the source blocker is already resolved, keeping
     it pending recreates the bug.
   - Alternative rejected: delete queued rows. Preserving a superseded row keeps
     audit history and avoids destructive cleanup.

4. `load_controller_core` can be reconciled as a startup bootloader receipt
   when the daemon is ready.
   - Rationale: its durable effect is Router-owned state (`controller_ready`,
     holder, and `controller_core_loaded`). A done Controller receipt plus live
     daemon readiness is enough for Router to apply that postcondition.
   - Alternative rejected: require PM repair for this case. It is mechanical
     state settlement, not a product or route decision.

## Risks / Trade-offs

- [Risk] Over-clearing a real blocker with a matching action type. -> Mitigation:
  require exact Controller action or scheduler identity when available; use the
  action-type fallback only for startup bootloader postconditions that are
  already satisfied.
- [Risk] A queued stale repair row remains visible in the ledger. -> Mitigation:
  mark it `superseded`, reconcile its scheduler row, and rebuild the Controller
  ledger.
- [Risk] Focused checks miss a broader Meta/Capability interaction. ->
  Mitigation: record the skip by user direction and run focused daemon
  reconciliation, prompt-boundary, runtime, install, and smoke checks.
- [Risk] Parallel AI edits touch the same files. -> Mitigation: keep this
  change narrow, inspect git status before final sync, and preserve all
  compatible peer work.

## Migration Plan

1. Update the daemon reconciliation FlowGuard model/checks so the known-bad
   traces fail before relying on runtime changes.
2. Add Router helpers for same-origin blocker resolution and stale blocker-row
   supersession.
3. Apply the helpers from scheduled Controller action reconciliation and the
   next-action settlement barrier.
4. Add focused runtime tests for old blocker clearing and stale PM repair row
   supersession.
5. Run focused FlowGuard/runtime checks, then sync and verify the installed
   local FlowPilot skill.
