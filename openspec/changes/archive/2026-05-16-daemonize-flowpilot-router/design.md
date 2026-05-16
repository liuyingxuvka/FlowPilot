## Context

FlowPilot currently has a strong file-backed control plane:

- Router state lives under `.flowpilot/runs/<run-id>/`.
- Cards, card bundles, packets, ACKs, result envelopes, route memory, packet
  ledgers, and display state are durable files.
- Roles open cards and packets through runtime helpers and write ACKs, reports,
  or result envelopes into Router-recognized mailbox locations.
- Controller may relay envelopes, show router-authored display text, create
  host resources, and apply Router actions, but it must not read sealed bodies
  or decide route progress.
- Heartbeat/manual resume can re-enter the Router loop and rehydrate roles from
  current-run memory.

The weak point is process liveness. Router is currently invoked as a short CLI
command: `next`, `run-until-wait`, `apply`, or `record-event`. If a role writes
an ACK after Controller has already stopped at an ordinary wait boundary,
Router does not observe that ACK until something calls Router again. In the
Codex desktop host, ending the foreground Controller turn may also make the live
background role cohort unreliable. That makes ordinary card/bundle waits a
stuck point even when all required files exist.

This design keeps the existing Router, packet, card, and role-boundary model,
but changes how it is driven. Router becomes a persistent per-run daemon that
ticks every one second. Controller becomes a persistent executor that clears a
Router-authored checklist.

## Goals / Non-Goals

**Goals:**

- Make Router responsible for waiting, mailbox reconciliation, and deciding the
  next legal state transition.
- Make Controller responsible for executing Router-authored host actions from a
  durable action ledger.
- Use a fixed one-second tick for Router daemon polling and Controller ledger
  polling while the run is active.
- Preserve current authority boundaries: roles do not advance Router; Controller
  does not approve gates; Router does not perform host actions.
- Ensure every Controller action has a durable checklist entry and a durable
  receipt.
- Ensure Controller repeatedly checks the ledger for missed work instead of
  stopping at ordinary role waits.
- Make heartbeat/manual resume restore Router daemon, Controller executor, and
  role cohort from persisted current-run state.
- Reuse existing card, bundle, packet, ACK, return-ledger, and `next`/`apply`
  logic instead of replacing the control plane.
- Add FlowGuard and runtime tests before production behavior is trusted.

**Non-Goals:**

- No remote GitHub push, release, or deployment.
- No replacement of cards, packet runtime, sealed body boundaries, or role
  authority.
- No role-to-Router direct process control. Roles write files; Router daemon
  observes those files.
- No Controller access to sealed packet, result, report, or card bodies unless
  an existing terminal-only exception explicitly allows it.
- No dynamic tick backoff in the first implementation. The active-run tick is
  fixed at one second.
- No broad rewrite of route planning, PM authority, reviewer gates, or officer
  modeling gates.

## Decisions

### Decision 1: Router becomes a per-run daemon, not a global service

Each formal FlowPilot run gets at most one active Router daemon. The daemon is
bound to `.flowpilot/runs/<run-id>/`, reads that run's state, and writes that
run's daemon status.

This preserves the current rule that each formal invocation has an isolated run
root. It also avoids a global service that must understand multiple unrelated
runs before the current single-run control plane is ready.

Alternative considered: one global Router service for every FlowPilot run. That
would eventually be useful, but it adds cross-run scheduling, permissions,
cleanup, and UI routing before the single-run liveness problem is fixed.

### Decision 2: The active daemon tick is exactly one second

Router daemon SHALL tick once per second while the run is active. Controller
executor SHALL check the Controller action ledger once per second while attached
to an active run.

The first implementation should not include dynamic backoff. A fixed tick is
easier to reason about, easier to test, and matches the user's desired behavior:
when the system is waiting, it simply checks every second.

Alternative considered: exponential or idle backoff. That reduces file-system
polling noise, but it makes live debugging harder and can reintroduce surprising
latency.

### Decision 3: Router owns waiting; Controller owns execution

Router daemon tracks the current wait condition, such as:

- expected card ACK path;
- expected card bundle ACK path;
- expected packet holder ACK;
- expected result envelope;
- expected role report envelope;
- expected Controller action receipt;
- user/host boundary;
- terminal lifecycle state.

Controller does not wait on role chat for ordinary ACK/report/result progress.
Controller only executes Router-authored actions and writes receipts. Router
keeps checking the mailbox evidence and decides when to move forward.

Alternative considered: Controller polls each expected ACK/result file. That
would repair the immediate bug, but it keeps waiting logic split between
Controller and Router.

### Decision 4: Router and Controller communicate through an action ledger

Router writes Controller-visible work into:

- `.flowpilot/runs/<run-id>/controller_actions/<action-id>.json`
- `.flowpilot/runs/<run-id>/controller_action_ledger.json`

Controller writes one receipt per action into:

- `.flowpilot/runs/<run-id>/controller_receipts/<action-id>.json`

The action ledger is a checklist, not a single "next action" slot. Controller
loops over all pending actions whose dependencies are satisfied, performs them,
writes receipts, and then scans the ledger again to catch missed work.

Alternative considered: one `controller_next_action.json` file. That is simpler,
but it can hide missed actions and does not represent parallel-safe or
dependency-ordered Controller work.

### Decision 5: Action status is explicit and owned by role

Controller action entries use a small status machine:

- `pending`
- `in_progress`
- `done`
- `blocked`
- `retry_requested`
- `superseded`
- `cancelled`

Router may create actions and mark them `pending`, `retry_requested`,
`superseded`, or `cancelled`. Controller may mark its own attempt
`in_progress`, `done`, or `blocked` through a receipt. Router reconciles
Controller receipts back into the ledger.

This prevents Controller from silently inventing route progress and prevents
Router from pretending a host action was completed without Controller evidence.

### Decision 6: Locks protect recovery, not normal role flow

Normal role flow does not directly call Router. Roles write files. Router daemon
observes those files. Therefore normal operation has only one Router writer.

The lock is still required for recovery cases:

- heartbeat starts while Router is already active;
- user manually resumes while heartbeat is starting Router;
- Controller reconnect tries to start Router;
- a stale process appears alive but no longer writes heartbeats.

The daemon should write:

- `.flowpilot/runs/<run-id>/runtime/router_daemon.lock`
- `.flowpilot/runs/<run-id>/runtime/router_daemon_status.json`

The lock record must include run id, process id when available, host/thread
identity when available, last tick time, and stale-lock rules.

### Decision 7: Router daemon wraps existing `next` and `apply`

The first implementation should not fork a parallel Router algorithm. Instead,
the daemon loop should call the same internal functions used by `next`,
`run-until-wait`, and `apply`:

1. reconcile durable evidence;
2. consume valid ACKs/results/reports idempotently;
3. compute the next legal Router action;
4. auto-apply safe internal actions;
5. write Controller ledger entries for Controller-required actions;
6. wait for Controller receipts or external mailbox evidence.

This lowers migration risk and keeps existing unit tests meaningful.

### Decision 8: Heartbeat becomes a recovery supervisor

Heartbeat/manual resume should stop being the ordinary way to advance a waiting
run. Its job becomes:

1. record the wake event;
2. check Router daemon status;
3. if Router is alive, do not start a second Router;
4. if Router is dead or stale, restart it from `.flowpilot` state;
5. check Controller executor attachment;
6. reattach/restart Controller executor behavior in the current thread;
7. check six role slots and rehydrate missing roles from current-run memory;
8. return to the Controller action ledger instead of manually advancing route
   work.

This aligns heartbeat with lifecycle repair rather than normal progress.

### Decision 9: Prompt changes are part of the protocol

The following prompt surfaces must change:

- Controller role card: Controller must stay attached to the action ledger
  while Router daemon is active and must not final at ordinary card/bundle/packet
  waits.
- FlowPilot skill bootloader: startup must create or verify Router daemon and
  then attach Controller to the ledger loop.
- Protocol reference: Router-owned waiting and Controller checklist execution
  become the canonical control model.
- Role cards: roles write ACKs/reports/results to Router mailbox, but do not
  directly advance Router or treat ACK as work completion.
- Packet/card check-in text: ACK is receipt-only; Router daemon will consume it
  through mailbox reconciliation; semantic work must continue through the
  proper packet/report/result path.

Prompt coverage must reject text that tells Controller to stop at ordinary
nonterminal ACK waits when Router daemon is active.

## Risks / Trade-offs

- Two Router daemons write the same run state -> Mitigation: run-scoped lock,
  daemon status heartbeat, stale-lock rules, and tests for duplicate start.
- Controller misses an action -> Mitigation: action ledger checklist, one-second
  Controller polling, dependency checks, and Controller self-audit for pending
  or stale `in_progress` actions.
- Router repeats the same action -> Mitigation: action idempotency keys,
  action ledger reconciliation, receipt hashes, and tests for duplicate ACK
  scans.
- Router consumes stale or wrong-role mailbox evidence -> Mitigation: preserve
  existing run id, role, agent id, hash, delivery id, route/frontier, and
  expected path validation.
- Router performs Controller work -> Mitigation: Controller-required actions
  are written to the ledger and cannot be marked done without Controller
  receipt.
- Controller resumes route work after terminal stop -> Mitigation: terminal
  lifecycle state cancels pending actions, stops daemon loop, stops Controller
  ledger execution, pauses heartbeat, and closes roles.
- One-second polling adds file-system noise -> Mitigation: the run root is
  local, active-run polling is bounded, and fixed polling is simpler and more
  predictable than hidden backoff.
- Existing CLI users still call `next`/`apply` manually -> Mitigation: keep CLI
  commands for diagnostics and recovery, but make formal startup prefer daemon
  mode and warn when manual commands are used against an active daemon.
- Host cannot truly keep Controller alive -> Mitigation: heartbeat/manual resume
  reattaches Controller to the ledger and Router daemon status rather than
  relying on chat history.

## Migration Plan

1. Add OpenSpec requirements and tasks for the persistent Router daemon,
   Controller action ledger, and daemon lifecycle recovery.
2. Add a FlowGuard model for the daemon/control-ledger state machine before
   runtime edits.
3. Add known-bad scenarios for the live bug: PM bundle ACK exists, Router can
   continue, but Controller stopped and no daemon consumes the ACK.
4. Add read-only daemon status scaffolding and lock files.
5. Add Router daemon loop in observation-only mode: one-second tick, mailbox
   scan, status writes, no state advancement.
6. Enable safe mailbox evidence consumption for card and bundle ACKs.
7. Add Controller action ledger files and Router ledger writer.
8. Add Controller receipt reconciliation.
9. Move existing Controller-required router actions into ledger entries.
10. Update Controller prompt to clear the ledger continuously.
11. Update FlowPilot startup to start/verify Router daemon and attach
    Controller executor.
12. Update heartbeat/manual resume to supervise daemon, Controller, and roles.
13. Update role, card, and packet prompts to describe mailbox evidence and
    Router daemon consumption.
14. Run focused FlowGuard, router runtime, card/packet runtime, prompt coverage,
    install sync, and audit checks.
15. Only after the focused path is stable, run broader FlowPilot check suites.

Rollback is local: stop the daemon, mark daemon mode disabled in run state, and
use the existing manual `next`/`apply` CLI loop. No remote publication is part
of this change.

## Open Questions

- Should daemon mode be mandatory for every formal FlowPilot run immediately,
  or should it start behind a `daemon_mode_enabled` flag for one validation
  cycle?
- Should Controller executor be implemented first as explicit prompt protocol
  in the foreground assistant, or as a separate local helper that emits
  Controller action prompts to Codex?
- What exact stale-lock timeout should be used before heartbeat may restart a
  Router daemon? The tick is one second, but stale detection may need a larger
  threshold such as ten seconds to avoid false restarts.
- Should multiple Controller actions be allowed to execute concurrently, or
  should the first implementation execute them serially while preserving
  dependency metadata for later parallelization?
