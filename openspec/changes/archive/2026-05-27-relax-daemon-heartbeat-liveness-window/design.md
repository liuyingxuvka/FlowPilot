## Context

The Router daemon writes a frequent lock/status heartbeat, but a real tick can also perform startup scheduling, receipt reconciliation, status projection, and ledger writes. Current runtime evidence showed a live, CPU-active daemon with heartbeat files delayed beyond five seconds, which made the foreground Controller repeatedly enter daemon liveness-check mode even though the daemon was not dead.

The existing safety model is still correct: the monitor may report that liveness needs checking, but only Controller may decide attach or recover after inspecting process/lock/status evidence. The problem is the monitor window, not the recovery ownership model.

## Goals / Non-Goals

**Goals:**

- Change the daemon heartbeat check window and daemon lock stale threshold to thirty seconds.
- Keep the daemon tick interval unchanged so healthy runs can still refresh quickly.
- Preserve the existing rule that delayed heartbeat evidence is not restart authority.
- Update OpenSpec, FlowGuard model evidence, tests, prompt text, and installed skill copy together.

**Non-Goals:**

- Do not change the one-minute host heartbeat automation cadence.
- Do not change the Router daemon single-writer lock semantics.
- Do not add a second daemon monitor or make Controller drive normal Router progress.
- Do not touch unrelated README or visual-asset work currently present in the working tree.

## Decisions

- Use a thirty-second monitor grace window and lock stale threshold. This is longer than the observed thirteen-to-sixteen-second delay and gives room for Windows/Python file I/O and multi-step daemon ticks without hiding genuinely stopped daemons for too long.
- Leave `ROUTER_DAEMON_TICK_SECONDS` at one second. The daemon should still refresh promptly when idle; the change only affects when foreground code treats delayed metadata as worth checking.
- Leave stale/recovery authority with Controller process/lock/status checks. The FlowGuard model and tests must continue to reject monitor-only recovery decisions and second-writer startup.
- Update human-facing prompt text from hard-coded "five seconds" to "thirty seconds" so heartbeat/manual resume instructions match runtime behavior.

## Risks / Trade-offs

- A truly dead daemon may be noticed up to thirty seconds later than before. Mitigation: Controller recovery still occurs after the window, and the one-minute continuation heartbeat remains a separate higher-level continuation mechanism.
- A truly wedged daemon whose process stays alive but stops refreshing the lock may be noticed later. Mitigation: the delayed threshold is still thirty seconds, Controller liveness checking remains required, and recovery still preserves the single-writer rule.
- Background regression runs may take time. Mitigation: run focused FlowGuard/test checks first, then start broader model/test suites under the repository's background artifact contract and inspect completion artifacts before claiming pass.
