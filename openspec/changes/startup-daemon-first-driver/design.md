## Context

FlowPilot already has the table protocol the user wants after Controller core:
Router owns the scheduler table, Controller owns a compact work table, and
Controller writes receipts/check-offs. Router may keep enqueueing independent
work until a barrier, then reconciles receipts, ACKs, and postconditions before
crossing the gate.

Startup has not fully used that same protocol. It has a bootloader list, and
the daemon starts late enough that startup intake, role slots, and heartbeat
binding can happen before the daemon is the active driver.

## Goals / Non-Goals

**Goals:**

- Start the Router daemon immediately after the minimal run shell, pointer,
  and index exist.
- Route startup bootloader work through the same Controller action ledger and
  Router scheduler ledger used later in the run.
- Keep Controller's table small and human-readable: action row, status,
  receipt/check-off, allowed reads/writes, and postcondition.
- Keep Router's table responsible for ordering, dependency metadata, scope,
  barrier classification, and reconciliation.
- Treat reviewer startup real-time/fact review as meaningful only after
  startup-scope queues are clean.

**Non-Goals:**

- Do not introduce a third startup-only table or a separate startup protocol.
- Do not require Controller to understand Router dependency graphs.
- Do not run heavyweight meta/capability model regressions for this focused
  repair.

## Decisions

1. **Minimal shell before daemon**

   A daemon needs a run root, current pointer, index entry, runtime directory,
   lock, status, and ledgers. Therefore `create_run_shell`,
   `write_current_pointer`, and `update_run_index` remain foreground-safe
   bootloader setup. The next startup row is `start_router_daemon`.

2. **Daemon owns external startup work**

   After `start_router_daemon`, external or user-visible startup actions such
   as startup intake UI, role startup, heartbeat binding, and Controller core
   handoff must be scheduled by the daemon. Foreground `next` may return a
   daemon-scheduled pending row, but it may not compute a fresh bootloader row
   directly while the daemon controls startup.

3. **Same two-table rule**

   For daemon-scheduled startup rows, Router writes:

   - a Controller action row in `runtime/controller_action_ledger.json`;
   - a Router scheduler row in `runtime/router_scheduler_ledger.json`;
   - startup scope metadata so current-scope reconciliation can join them.

   Controller completion remains a check-off/receipt. Router then reconciles
   the matching row and advances only when the required postcondition exists.

4. **Barriers are explicit**

   Router may continue scheduling only when the next row is nonblocking. It
   must stop at barriers such as user answer collection, host automation/spawn,
   required payload, current-scope reconciliation, and Controller core handoff.

5. **Review starts after cleanup**

   Startup reviewer fact/real-time review is downstream of startup mechanical
   audit and current startup-scope reconciliation. It must not begin while
   startup daemon rows, ACKs, receipts, or required postconditions are still
   pending.

## Risks / Trade-offs

- [Risk] A background daemon tick may race with foreground startup apply.
  -> Mitigation: foreground only returns existing daemon-scheduled rows while
  daemon controls startup, and row completion is idempotent by scheduler id.
- [Risk] Legacy runs already in the old startup order may be resumed.
  -> Mitigation: only enforce daemon-first ownership for new or not-yet-core
  runs; legacy completed flags remain readable.
- [Risk] More rows appear in Controller's ledger during startup.
  -> Mitigation: rows stay simple; Router metadata remains in the Router
  scheduler ledger.
