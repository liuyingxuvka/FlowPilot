## Why

Recent FlowPilot runtime evidence showed that a fresh JSON write lock whose
owner process had already died could still be treated as active until timeout,
turning a recoverable writer crash into a fatal Router daemon exit. The same
run also showed that a user stop did not immediately fence the daemon, allowing
startup/heartbeat work to be scheduled after terminal lifecycle had already
been requested.

## What Changes

- Classify JSON write locks by both age and owner liveness, and allow immediate
  takeover of fresh locks whose owner process is confirmed dead.
- Record dead-owner lock takeover as diagnostic runtime evidence so the writer
  crash is visible instead of silently hidden.
- Treat transient JSON write contention as a deferred daemon tick, not a fatal
  daemon error, when the owning writer may still be alive.
- Add an immediate terminal fence for user stop/cancel paths that marks daemon
  mode terminal, cancels or supersedes pending nonterminal controller work, and
  prevents new startup, heartbeat, role, or route actions.
- Guard daemon and startup scheduler entry points so terminal runs return to
  terminal projection only and never rejoin active startup/heartbeat flow.
- Refresh visible runtime projections from the same terminal lifecycle fact so
  current/index/router state/daemon status do not disagree after stop.
- Extend FlowGuard coverage with known-bad hazards for dead-owner fresh locks,
  writer death while holding a lock, stop-during-startup scheduling, and false
  recovery that does not reconnect to normal active or terminal flow.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `active-writer-settlement`: distinguish live active writers from fresh locks
  whose owner process is already dead, and require observable dead-owner
  takeover evidence.
- `persistent-router-daemon`: downgrade transient JSON write-lock contention to
  a deferred tick and require terminal ticks to stop without scheduling active
  work.
- `daemon-lifecycle-recovery`: make user stop/cancel immediately fence daemon
  mode and background actions before terminal summary cleanup.
- `startup-daemon-first-driver`: prevent startup scheduler rows after terminal
  lifecycle has been requested.
- `daemon-projection-reconciliation`: require terminal projections to be
  refreshed from one terminal fact and to avoid stale next-action descriptions.

## Impact

- Runtime code under `skills/flowpilot/assets/` for JSON write locking, daemon
  tick/error handling, lifecycle stop requests, startup scheduling, heartbeat
  binding, and daemon status projection.
- Focused FlowGuard model/checks for persistent Router daemon behavior.
- Router runtime tests covering dead-owner lock takeover, writer-death
  diagnostics, nonfatal lock deferral, immediate stop fence, terminal
  projection consistency, and no post-stop startup/heartbeat scheduling.
- Local install sync scripts/checks for the installed FlowPilot skill copy.
