## Context

FlowPilot has two ways to execute `deliver_mail`:

1. The direct Router `apply_action("deliver_mail")` path updates
   `router_state.delivered_mail`, the mail-delivery flag, and
   `packet_ledger.mail`.
2. The daemon Controller-ledger path asks Controller to perform the relay and
   write a `controller-receipt`. Router then reconciles that receipt through
   `_apply_stateful_receipt_postcondition`.

The bug is that the second path did not support `deliver_mail`, so a valid
Controller receipt could become `unsupported_stateful_controller_receipt` and
leave Router and packet ledgers stale.

## Goals / Non-Goals

**Goals:**

- Make direct apply and Controller receipt reconciliation use one shared
  Router-owned mail-delivery fold.
- Update every authoritative state surface for a mail delivery together.
- Keep sealed body boundaries intact: Controller and Router fold envelope and
  ledger metadata only, not packet bodies.
- Preserve bounded mechanical reissue and PM escalation when folding fails.
- Add focused FlowGuard and runtime coverage for the receipt path.

**Non-Goals:**

- Do not let Router bypass Controller for role-facing packet relay.
- Do not rebuild the blocker policy table.
- Do not run heavyweight Meta/Capability simulations for this focused fix.
- Do not alter unrelated startup, card, heartbeat, or role-output workflows.

## Decisions

1. Use a shared fold helper for `deliver_mail`.

   The helper is the single owner of mail delivery state mutation. Both direct
   apply and Controller receipt reconciliation call it, so the two paths cannot
   diverge.

2. Keep the fold metadata-only while using the packet runtime release path.

   The fold verifies the mail id, target role, current packet ledger, and
   receipt payload metadata, then calls the existing
   `packet_runtime.controller_relay_envelope` path to release the packet to the
   addressed role. It must not read sealed packet bodies.

3. Treat flag, ledger, and packet holder release as one atomic outcome.

   A mail delivery is not complete unless the Router flag and
   `packet_ledger.mail` agree and the packet ledger shows the packet relayed to
   the target role with a controller relay signature. Repeated reconciliation
   should detect existing delivery evidence and return success without
   duplicating rows, counters, holder history, or relay history.

4. Keep blocker recovery as the fallback.

   If the fold cannot be proven, Router keeps the existing
   `controller_action_receipt_missing_router_postcondition` blocker path. PM
   repair decisions then create a repair transaction/reissue rather than
   silently marking the original gate passed.

## Risks / Trade-offs

- Moving shared logic can accidentally change the direct path -> add focused
  tests for both direct apply and Controller receipt reconciliation.
- Packet holder/status updates must remain on the existing packet runtime path;
  do not hand-edit holder movement or treat a chat message as a packet relay.
- Live-run artifacts may change while checks run -> live projection is
  diagnostic evidence, while focused model-only checks and tests are the
  pre-implementation gate.

## Migration Plan

1. Upgrade the daemon reconciliation FlowGuard model and live projection.
2. Add a shared mail-delivery fold helper.
3. Route direct `apply_action("deliver_mail")` through the helper.
4. Route `_apply_stateful_receipt_postcondition` `deliver_mail` through the
   same helper.
5. Add focused tests for daemon/controller-receipt folding and idempotency.
6. Run focused FlowGuard checks, focused tests, OpenSpec validation,
   install/sync checks, and record Meta/Capability skips.
