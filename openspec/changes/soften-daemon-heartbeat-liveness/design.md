## Context

FlowPilot uses a per-run Router daemon that ticks once per second and writes
daemon status plus a run-scoped lock. The foreground Controller does not own
normal Router progress; it reads Router-authored status and Controller action
ledger rows, executes host-visible work, and stays attached while the run is
active.

The observed failure mode is a short heartbeat gap being surfaced as a
repair/restart duty. A one-second daemon tick is an ideal cadence, not a safe
death threshold. Host scheduling, file I/O, or transient write timing can make
the latest heartbeat appear older than one tick while the daemon is still
active. The monitor should therefore report a liveness-check condition, not a
recovery conclusion.

## Goals / Non-Goals

**Goals:**

- Preserve the one-second daemon tick.
- Treat daemon heartbeat age at or below five seconds as normal.
- Surface heartbeat age above five seconds as `check_liveness`, with explicit
  Controller instruction to inspect the process, lock, and status.
- Let Controller decide attach/continue versus safe recovery after the
  liveness check.
- Keep duplicate-writer prevention intact: if recovery finds an active daemon,
  it attaches instead of starting another writer.
- Make user-facing status describe "heartbeat delay" until a liveness check
  proves the daemon is stopped.

**Non-Goals:**

- Do not introduce long multi-tier timeout states.
- Do not let the monitor decide `needs_recover`.
- Do not make Controller a second source of Router progress.
- Do not alter role recovery, packet body access, ACK semantics, or startup
  acceptance gates.

## Decisions

1. **Two monitor states only**

   Monitor output uses `heartbeat_status=ok` when the last daemon heartbeat is
   at or below five seconds old, and `heartbeat_status=check_liveness` when it
   is older. There is no monitor-level `needs_recover` state. That keeps the
   monitor simple and avoids over-claiming from timestamps alone.

2. **Controller owns the liveness check after the threshold**

   On `check_liveness`, Controller checks whether the daemon process is still
   alive, whether the lock still belongs to the same run, and whether status or
   lock timestamps resume. If the daemon is alive, Controller continues
   attached. If the daemon is not alive, Controller executes the existing safe
   recovery path for the current run.

3. **Recovery remains attach-first**

   The recovery path keeps the current single-writer invariant. A replacement
   attempt that observes an active daemon is treated as attach/continue
   evidence rather than a failure. Starting a second writer for the same run
   remains forbidden.

4. **Patrol wording follows the monitor boundary**

   `controller-patrol-timer` should not tell Controller or the user that a
   daemon is stale merely because the heartbeat crossed five seconds. It should
   report the heartbeat delay and the exact liveness-check instruction.

## Risks / Trade-offs

- [Risk] A real daemon crash may be detected a few seconds later.
  -> Mitigation: five seconds is still short enough for interactive startup
  and prevents false recovery from ordinary one-tick delay.
- [Risk] Controller liveness checks can drift from Router lock semantics.
  -> Mitigation: use the same run-scoped lock/status helpers and keep the
  attach-first recovery path in one implementation boundary.
- [Risk] Existing tests expect `daemon_repair_or_restart` directly from patrol.
  -> Mitigation: update those tests to expect `check_liveness` first, then
  recovery only after Controller confirms the daemon is not alive.
- [Risk] Parallel work may already be changing daemon reconciliation models.
  -> Mitigation: extend existing dirty model files without reverting peer
  edits, and verify the combined model before installation sync.

## Migration Plan

1. Add OpenSpec requirements and focused tasks for the five-second heartbeat
   liveness window.
2. Extend FlowGuard daemon reconciliation or patrol model coverage before
   runtime edits.
3. Update Router monitor/patrol status payloads and Controller instructions.
4. Update tests for delayed heartbeat, alive daemon after delay, dead daemon
   after delay, and attach-first recovery.
5. Run focused tests and background project model regressions.
6. Sync the installed FlowPilot skill from the repository and verify the local
   install.

Rollback is narrow: revert the monitor/patrol status fields and the focused
tests/model additions. The daemon lock and recovery mechanisms remain the same.
