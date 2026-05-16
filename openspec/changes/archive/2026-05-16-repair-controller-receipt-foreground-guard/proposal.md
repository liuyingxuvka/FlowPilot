# Repair Controller Receipt Foreground Guard

## Why

Live FlowPilot startup exposed two related control-plane misses:

- Router repeatedly issued `sync_display_plan` after Controller receipts because
  receipt reconciliation cleared the pending action without updating the
  Router-owned display sync fact.
- The foreground Controller ended while the daemon was still live and the
  Controller action ledger still contained an executable action.

Both failures come from the same boundary: Controller receipts are local action
evidence, while Router owns the workflow facts and the foreground keepalive
contract.

## What Changes

- Reconcile display/status Controller receipts through the same Router-owned
  display fact writer used by direct `sync_display_plan` application.
- Expose a stricter foreground exit policy from `controller-standby` and status
  summaries so `controller_action_ready` cannot be mistaken for permission to
  end the foreground turn.
- Keep the repair narrow: no new daemon, no new ledger family, no duplicate
  display system, and no changes to PM/worker route authority.

## Out Of Scope

- The two heavyweight meta/capability regressions remain skipped for this task.
- No route execution behavior beyond Controller receipt reconciliation and
  foreground standby/exit policy is changed.
