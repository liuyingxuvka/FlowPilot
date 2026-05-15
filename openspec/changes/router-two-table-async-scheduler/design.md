## Context

FlowPilot already has a Controller action ledger and card ACK ledgers. It also has a Router-owned ownership ledger for reconciliation evidence. The gap is that the daemon tick still behaves like a single-current-action loop: Router often waits for Controller to clear one row before it exposes the next independent row.

The desired control shape is two tables:

- the Controller table is a simple work board for Controller;
- the Router scheduler table is Router's own planning, dependency, barrier, and reconciliation board.

Startup must be folded into the same rule as later route work. Router may keep scheduling until it reaches a barrier; at the pre-review gate it must reconcile the current scope and wait or repair only what is still unresolved.

## Goals / Non-Goals

**Goals:**
- Start and use the Router daemon as the one-second driver for startup and route control.
- Make daemon ticks enqueue multiple independent Controller rows when no barrier is active.
- Keep Controller rows simple and move dependency/barrier complexity into a Router-only scheduler ledger.
- Keep Controller's foreground plan non-empty during live waits by exposing a continuous standby/watch row whenever there is no ordinary Controller work ready.
- Let Controller mark rows done independently, then let Router reconcile receipts and postconditions on later ticks.
- Enforce startup Reviewer fact review through the same current-scope reconciliation helper used for current-node review.
- Preserve PM startup activation's existing same-role ACK blocker without adding a second all-startup gate.

**Non-Goals:**
- No new startup-only table or alternate startup protocol.
- No broad rewrite of card runtime, packet runtime, or route execution.
- No heavyweight `meta` or `capability` regression run for this change.
- No push, release, or publish action.

## Decisions

### Router Scheduler Ledger

Add `runtime/router_scheduler_ledger.json` as a Router-only table. It records one row per planned Controller action, including Router row id, action id, scope, dependencies, barrier classification, receipt status, and reconciliation status.

Rationale: Controller should not need to understand why a row is safe to run. Router needs a durable board so it can dedupe rows, rehydrate after resume, and distinguish "row sent" from "row reconciled".

Alternative considered: put all dependency metadata into the Controller table. Rejected because it makes Controller own routing complexity and contradicts the two-table boundary.

### Simple Controller Table

Keep `runtime/controller_action_ledger.json` as the Controller-facing work board. It may include Router row ids and scope tags for traceability, but dependencies and barrier policy remain Router-owned metadata.

Rationale: the Controller's job is "do this row and receipt it"; the Router owns sequencing.

### Continuous Standby Row

When the Router daemon is live and there is no ordinary ready Controller row, Router writes or refreshes one stable Controller-facing row for `continuous_controller_standby`.

That row is not a one-time checklist item. It is the formal Controller duty to stay attached, keep the visible Codex plan synced from the Controller action ledger, check unfinished rows and receipts, and watch Router daemon status until Router exposes a real next action, terminal state, user input, daemon repair, reminder/liveness check, or blocker. A bounded diagnostic timeout can report `timeout_still_waiting`, but normal foreground standby must keep waiting rather than treat that timeout as completion.

Rationale: the foreground Controller should always have a visible task that says who it is watching and what condition will release it. An empty plan encourages the host agent to stop even though FlowPilot is still alive.

### Queue-Until-Barrier Daemon Tick

On each daemon tick, Router:

1. refreshes the daemon lock;
2. syncs Controller receipts into the Controller table;
3. applies Router-owned postconditions for completed rows;
4. updates the Router scheduler table;
5. computes and enqueues the next action;
6. continues only when the action is non-blocking and independent;
7. stops at barriers such as user input, host automation, control blockers, role-result waits, non-startup ACK waits, or current-scope reconciliation waits;
8. refreshes the continuous standby row when the stop condition leaves Controller with no ordinary executable row.

Rationale: this matches the user's desired model: Router keeps putting rows on the board while there is no wall in front of it.

### Startup As A Current Scope

Add startup blockers to the current-scope pre-review reconciliation helper. Before `reviewer.startup_fact_check` delivery or `reviewer_reports_startup_facts` acceptance, Router checks startup-local Controller rows, startup prep cards, prep ACKs, heartbeat/boundary/display/mechanical evidence, and active local blockers.

Rationale: startup should use the same "clear this current scope before Reviewer live review" rule as later node review.

### PM Activation Remains Same-Role ACK Gated

Do not add a second activation-layer join. After Reviewer reports startup facts, the existing same-role pending-card-return blocker already ensures PM cannot approve activation before ACKing `pm.startup_activation`.

Rationale: adding another global startup gate would duplicate the card-runtime ACK rule and create the "second layer" the user called out as redundant.

## Risks / Trade-offs

- [Risk] Async scheduling can duplicate side effects after daemon retries. → Use deterministic idempotency keys and Router scheduler row ids for daemon-enqueued actions.
- [Risk] Router may move past a local Controller row whose postcondition is actually required. → Mark such rows as barriers unless the next action is independent; use current-scope reconciliation before Reviewer gates.
- [Risk] Completed receipts might not update Router-visible flags. → Route done receipts through shared postcondition appliers before marking Router scheduler rows reconciled.
- [Risk] Existing tests assume single-current-action behavior. → Preserve `next_action` foreground behavior and apply queue filling only in daemon ticks.
- [Risk] Controller treats the standby row as "checked once, done". → Encode explicit do-not-complete conditions in the row, standby payload, prompt cards, and focused tests.
- [Risk] Heavy model regressions are skipped. → Add and run focused FlowGuard and runtime tests, and record the skip explicitly in adoption notes.
