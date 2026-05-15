# Async Startup Obligation Join

## Why

FlowPilot startup still behaves more serially than the normal runtime loop:
Router often waits for one startup card ACK before issuing the next independent
startup card. That preserves safety, but it wastes time because later startup
obligations usually do not depend on the earlier ACK being returned first.

The runtime already has the safer pattern we want after Controller core loads:
Router owns the action ledger, Controller performs Router-authorized actions,
roles check in through ACK/return events, and Router blocks only at the gate
where the missing obligation actually matters.

## What Changes

- Make startup card delivery use the same Controller action ledger, system-card
  pending return ledger, ACK clearance, and Router synchronization rules as the
  rest of runtime.
- Allow Router to issue independent startup card deliveries while startup-scope
  card ACKs remain pending.
- Add a startup activation join that reuses the existing ACK clearance and
  event-dependency blocker path before PM can approve, repair, or dead-end
  startup activation.
- Preserve all hard startup gates: current-run startup answers, run shell,
  six-role receipts, early heartbeat, Controller sealed-body boundary, reviewer
  fact check, PM prep, and no route/material work before startup opens.
- Keep remediation ordinary: if the join sees a missing startup ACK, Router
  returns the existing pending-card-return action for the responsible role
  instead of introducing a second startup-specific wait mechanism.

## Capabilities

- Modified: FlowPilot startup control plane.
- Modified: FlowPilot system-card ACK clearance.
- Modified: FlowPilot Controller action ledger progression.

## Impact

- Startup becomes less serial without weakening the startup activation gate.
- Controller continues to use one interaction table: Router appends and syncs
  actions in `runtime/controller_action_ledger.json`; Controller receipts clear
  ledger rows; role ACKs clear existing pending returns.
- No new ledger family, no Controller authority increase, no route work before
  startup activation, and no heavyweight meta/capability regression runs for
  this change.
