## Why

PM control-blocker repair decisions currently record a recovery intent and may
open a repair transaction, but the Router can still commit a transaction that
only waits for a future event without a concrete producer. That makes a valid
PM decision mechanically accepted while the route can still stall.

## What Changes

- Extend the existing blocker repair policy so `repair_transaction.plan_kind`
  is the executable authority for PM repair decisions.
- Treat top-level `recovery_option` and `repair_action` as PM explanation and
  policy context, not as Router execution instructions.
- Replace vague replay intent with explicit executable repair plan kinds:
  `operation_replay`, `controller_repair_work_packet`, `packet_reissue`,
  `role_reissue`, `router_internal_reconcile`, `await_existing_event`,
  `route_mutation`, and `terminal_stop`.
- Require Router to validate that each committed repair transaction either
  has an executable handler, queues a concrete next action, or is a real
  terminal stop.
- Reject PM repair decisions that would create an empty wait, including legacy
  `event_replay` decisions that do not identify an existing event producer.
- Update PM and Controller cards so PM selects the correct executable plan kind
  and Controller can safely execute bounded repair work packets.

## Capabilities

### New Capabilities

- `executable-repair-transactions`: Ensures PM repair decisions are consumed as
  executable Router repair transactions with validated plan-specific fields and
  no dead-wait commits.

### Modified Capabilities

- `blocker-repair-policy`: The existing PM recovery policy is narrowed so
  `recovery_option` describes the policy route, while `repair_transaction`
  carries the executable plan.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/contracts/contract_index.json`
- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- Focused router/runtime tests for executable PM repair decisions and
  dead-wait rejection
- FlowGuard repair transaction model/checks and adoption notes
