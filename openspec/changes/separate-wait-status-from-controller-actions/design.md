## Context

FlowPilot already has two related mechanisms:

- a Controller action ledger that is meant to be a simple work board; and
- Router daemon status plus continuous standby that keeps the foreground Controller attached while Router-owned progress waits on external events.

The defect class appears when a pure wait state is projected as an ordinary Controller action row. The Controller cannot execute that row. Worse, if the wait becomes the current pending action, it can hide Router-owned local obligations, such as startup audit or display-status reconciliation, that would clear the blocker.

## Goals / Non-Goals

**Goals:**

- Ensure ordinary Controller action rows are executable work only.
- Keep role/card/current-scope wait information visible through monitor/status projections.
- Make due wait-target reminders generic for any current waiting role, with Router-authored text and a Controller receipt.
- Preserve continuous standby as the only Controller-facing duty while there is no executable Controller work.
- Prevent pure wait rows from increasing active Controller work counts or blocking Router-local reconciliation.
- Add focused FlowGuard and runtime checks that fail if pure waits re-enter the ordinary Controller work board.
- Preserve compatible parallel-agent changes. Heavyweight Meta/Capability models may run in the background when practical.

**Non-Goals:**

- Do not remove wait tracking, reminders, liveness probes, blocker escalation, or current wait status.
- Do not let Controller advance route progress from monitor state.
- Do not replace existing card, packet, role, or blocker settlement contracts.
- Do not broaden this change into controller-core startup boundary work owned by other active changes.

## Decisions

1. **Classify Controller projections by executability.**

   Router will distinguish ordinary executable Controller actions from passive wait projections. Executable actions have a host/controller side effect, a receipt, a relay, a display, or a repair action that Controller can perform. Passive waits only describe an external event or a Router-owned reconciliation condition.

2. **Pure waits stay in Router status, not the ordinary work board.**

   `await_role_decision`, `await_card_return_event`, `await_card_bundle_return_event`, and `await_current_scope_reconciliation` are passive wait projections unless a future variant explicitly declares a Controller-side side effect. They may remain in `run_state.pending_action` as Router state for compatibility, but they must not be written as ordinary Controller action rows.

3. **Continuous standby remains the Controller-facing empty-board duty.**

   When the Controller work board has no executable rows and the run is nonterminal, Controller should run standby/patrol and watch Router daemon status. Standby payloads must name the current wait target, so the user still sees who or what FlowPilot is waiting for.

4. **Router-local obligations preempt passive waits.**

   Before preserving or displaying a passive wait, Router reconciliation must still expose or consume Router-owned local obligations. A passive wait must not be allowed to hide mechanical audit, display status, controller-boundary projection, startup joins, receipt reconciliation, or similar local fixups.

5. **Due wait-target reminders become generic executable rows.**

   The passive `await_*` wait itself remains status, but a due reminder is a different thing: concrete Controller work. Router creates a `send_wait_target_reminder` row for the current waiting role, carrying the Router-authored reminder text, target role, wait class, source wait identity, and receipt contract. Controller must send that exact text, avoid sealed bodies, and write a receipt with the matching reminder hash. Report-result reminders also require a fresh liveness probe; unhealthy liveness continues to route into the existing blocker/recovery path.

## Risks / Trade-offs

- Existing tests may assert old `await_*` next actions -> Update them to assert monitor/current-wait plus empty ordinary action queue or standby.
- Some wait rows may carry useful metadata -> Preserve that metadata in `current_wait`, daemon status, scheduler rows, and current status summaries.
- Removing wait rows from active counts could accidentally permit foreground exit -> Keep continuous standby as an in-progress anti-exit duty and validate `controller_stop_allowed=false` while nonterminal.
- Historical runs can still contain old waiting rows -> Rebuild/reconciliation should treat old wait rows as status history and avoid letting them block new executable actions.

## Migration Plan

1. Add a wait-action inventory and FlowGuard coverage for passive waits versus executable Controller actions.
2. Implement a Router helper that identifies passive wait projections and prevents them from being written as ordinary Controller action rows.
3. Update daemon queue fill, observe mode, ledger counts/status summaries, and `next_action`/standby behavior so pure waits are status only.
4. Update focused runtime tests for role waits, card waits, current-scope reconciliation waits, startup self-blocking waits, and continuous standby.
5. Run focused FlowGuard checks and runtime tests. Run heavyweight Meta/Capability regressions in the background when they are needed and practical.
6. Sync the installed FlowPilot skill from repository source and run install/audit checks.
