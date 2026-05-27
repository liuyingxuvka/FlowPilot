## Context

FlowPilot currently has separate mechanisms for JSON write locks, Router daemon
locks, lifecycle stop requests, startup daemon scheduling, and user-visible
runtime projections. The failure sequence showed that those mechanisms can
disagree under stress: a writer can die after creating a fresh `.write.lock`,
another daemon can time out and exit fatally, and a later user stop can mark
run state terminal while daemon-owned startup work is still allowed to schedule.

The repair has to preserve existing run-scoped daemon ownership and persisted
ledger replay. It must also avoid broad router rewrites while still fixing the
root contracts: lock owner liveness, daemon crash containment, terminal
fencing, and projection consistency.

## Goals / Non-Goals

**Goals:**

- Make fresh dead-owner JSON locks recoverable without waiting for the stale
  age threshold.
- Make live-writer contention a deferred daemon tick rather than a fatal daemon
  exit.
- Make user stop/cancel write a terminal fence before any new nonterminal
  daemon/startup/heartbeat work can be scheduled.
- Prove with FlowGuard that bad historical cases fail and safe recoveries
  either rejoin normal active daemon flow or settle terminally.
- Keep public FlowPilot commands and router facade imports compatible.
- Synchronize and verify the installed local FlowPilot skill after the fix.

**Non-Goals:**

- No release publication, tag, push, or GitHub release.
- No rewrite of the whole router or Controller action protocol.
- No weakening of daemon single-writer semantics.
- No attempt to recover sealed packet/result body contents from chat history.

## Decisions

1. **Use one JSON write-lock classifier.**

   Runtime JSON write-lock decisions will go through a shared classifier that
   reports `missing`, `owned_by_self`, `active_live_owner`,
   `dead_owner_takeover`, `stale_takeover`, `malformed_takeover`, or
   `unknown_defer`. This removes the current ambiguity where freshness alone
   can make a dead-owner lock look active.

   Alternative considered: only reduce the stale timeout. That would make some
   incidents faster but would still misclassify dead owners and still hide why
   the original writer died.

2. **Keep acquisition errors typed.**

   A live owner or uncertain owner causes a typed write-in-progress/defer
   condition. A confirmed dead owner or stale lock is taken over and recorded.
   A malformed lock without live-owner evidence is repair/takeover evidence,
   not a daemon-fatal timeout.

   Alternative considered: catch all Router errors inside the daemon loop. That
   would keep the daemon alive but blur real protocol faults with transient
   write settlement.

3. **Fence terminal lifecycle at the stop entry point.**

   `user_requests_run_stop` and equivalent terminal lifecycle requests will
   write terminal daemon status, mark the daemon lock terminal, cancel or
   supersede pending nonterminal controller/startup rows, and refresh current
   projections before ordinary daemon cleanup resumes. Later terminal summary
   remains useful, but it is no longer the first place daemon mode becomes safe.

   Alternative considered: rely on the existing terminal summary cleanup. The
   observed run showed that this is too late because daemon ticks can still use
   old in-memory state before summary cleanup.

4. **Guard background entry points.**

   Daemon ticks, startup daemon scheduling, heartbeat binding creation, and
   startup bootstrap action scheduling will check the terminal fence before
   producing nonterminal side effects. Terminal state may still write terminal
   status/projection evidence; it may not create heartbeat automations, start
   roles, or schedule startup rows.

   Alternative considered: add a guard only at the top daemon loop. The failure
   already demonstrated that nested startup scheduling can run inside a tick,
   so the nested entry points need their own fence.

5. **Model the miss before trusting tests.**

   The focused persistent-daemon FlowGuard model will include the real miss:
   fresh dead-owner lock, writer death while holding a lock, stop during startup
   scheduling, and false recovery that neither rejoins active flow nor settles
   terminal. Runtime tests then cover the code paths that implement those model
   obligations.

## Risks / Trade-offs

- **Risk: process liveness checks differ across platforms.** Mitigation:
  preserve the existing process-liveness helper and add tests using impossible
  PIDs plus owned-by-self cases instead of relying on OS-specific process
  creation timing.
- **Risk: terminal fencing could cancel a terminal cleanup action.**
  Mitigation: distinguish terminal cleanup/controller actions from nonterminal
  startup/heartbeat/role/route actions.
- **Risk: takeover hides the original writer crash.** Mitigation: write a
  durable dead-owner takeover incident with lock metadata and affected path.
- **Risk: broad model checks are slow.** Mitigation: run focused daemon checks
  first, then run router/release tiers and Meta/Capability checks in background
  with the repository's background artifact contract.

## Migration Plan

1. Add OpenSpec deltas and tasks for the daemon lock/terminal-fence repair.
2. Update the focused persistent Router daemon FlowGuard model and runner
   expectations.
3. Implement runtime helpers and narrow guards while preserving public facade
   compatibility.
4. Add focused runtime tests and run them before wider suites.
5. Run router/release tiers and required FlowGuard checks; inspect final
   background artifacts before claiming pass.
6. Sync the installed FlowPilot skill with the repository copy and verify local
   install freshness.
7. Commit locally without push/tag/release.

Rollback is ordinary git rollback of this local change set plus reinstalling
the previous skill copy if needed. No persisted user run migration is required;
the new logic only changes future lock/fence handling and projection refresh.

## Open Questions

None for implementation. Remote publication remains explicitly out of scope.
