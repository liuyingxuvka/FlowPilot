## Context

FlowPilot startup now uses a Router daemon plus two runtime tables: Router owns
ordering in the scheduler ledger, while Controller clears exposed rows in the
Controller action ledger. Today `emit_startup_banner`, `start_role_slots`, and
`create_heartbeat_automation` can be projected before `load_controller_core`.
Those rows are Controller-ledger work, so exposing them before the Controller
core handoff makes the foreground role act as Controller before the protocol
says Controller is loaded.

The previous heartbeat ordering work intentionally kept first-time heartbeat
binding before route execution. This change keeps that safety property, but
moves the boundary from "before Controller core" to "after Controller core and
before startup review, PM activation, role work, or route work."

## Goals / Non-Goals

**Goals:**

- Make `load_controller_core` the first Controller-ledger startup row after
  native startup intake and deterministic bootstrap materialization.
- Queue `emit_startup_banner`, `create_heartbeat_automation`, and
  `start_role_slots` only after Controller core is reconciled.
- Keep heartbeat host proof required before startup review or PM activation.
- Keep startup intake body sealing, Controller receipt reconciliation, and
  Router scheduler ownership unchanged.
- Add FlowGuard and runtime coverage for the old bad order.

**Non-Goals:**

- No new startup action type, table, payload schema, heartbeat cadence, or role
  spawn payload contract.
- No change to startup intake UI behavior or PM access to sealed user intake.
- No release, publish, or public API change.

## Decisions

1. `load_controller_core` becomes a startup barrier before Controller-owned
   startup obligations.

   The daemon may continue to own queueing, but it must not expose banner,
   heartbeat, or role-slot rows until the Controller core postcondition is
   reconciled. This matches the user's mental model: first put Controller on
   duty, then let Controller clear its startup work board.

2. First-time heartbeat binding remains mandatory before route work.

   The older invariant "heartbeat before Controller core" is too early for the
   Controller-ledger design. The replacement invariant is "heartbeat before
   startup review, PM activation, and route work." Manual-resume startup still
   skips heartbeat automation.

3. Model the rejected order explicitly.

   FlowGuard meta/capability models and the async scheduler model should reject
   traces where a Controller-ledger startup obligation is exposed before
   Controller core is loaded, while accepting traces where Controller core is
   loaded first and startup obligations complete before work beyond startup.

4. Preserve peer-agent prompt-boundary work.

   Existing uncommitted work that clarifies the startup-intake handoff remains
   compatible. This change should build on that wording rather than reverting
   it.

## Risks / Trade-offs

- [Risk] Existing tests and models encode heartbeat before Controller core.
  Mitigation: update them to the new, narrower safety property: heartbeat must
  be bound before startup review/PM activation/route work.
- [Risk] Moving role-slot queueing later could hide startup work until
  Controller core is reconciled.
  Mitigation: keep the rows daemon-projected immediately after Controller core,
  and keep Controller standby active while FlowPilot is running.
- [Risk] A stale `load_controller_core` reconciliation bug could block all
  later startup obligations.
  Mitigation: keep focused reconciliation tests for Controller receipts and the
  prior false-PM-blocker class.
