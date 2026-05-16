# Design

## Root Cause

`sync_display_plan` direct application writes `display_plan.json`,
`route_state_snapshot.json`, `current_status_summary.json`, and
`run_state.visible_plan_sync`. The daemon/receipt path only reconciled the
Controller receipt and cleared the pending action. Router then had no durable
Router-owned fact proving the display projection had been synchronized, so the
next daemon tick could issue the same display action again.

Foreground standby already existed, but its modeled and runtime contract was
stronger for role waits than for ready Controller actions. A ready Controller
action is not a wait boundary; it is foreground work that must be processed
before the Controller may end or re-enter standby.

## Minimal Repair

1. Extract the Router-owned display sync writer into one helper.
2. Use that helper from both direct `apply sync_display_plan` and Controller
   receipt reconciliation for `sync_display_plan`.
3. Keep visible/user-display confirmation checks when a display action requires
   them.
4. Add machine-readable foreground exit policy:
   - pending executable Controller actions block foreground exit;
   - ready Controller actions must be processed before ending;
   - live daemon waits without ready action require standby;
   - nonterminal active runs expose a required foreground mode instead of a
     generic stop permission;
   - only terminal runs allow Controller to stop; user-required or stale-daemon
     states may return to the caller for input or repair without marking the
     FlowPilot run complete.
5. Update Controller instructions to state that `controller_action_ready` means
   "process the ledger action now", `watch_router_daemon` means stay attached
   through `controller-standby`, and neither means "FlowPilot has stopped".

## Validation

- Persistent daemon FlowGuard model detects the three known-bad states.
- Focused Router runtime tests cover receipt-only display sync and standby
  foreground exit policy.
- Install sync/audit verifies the local skill copy matches the repository.
