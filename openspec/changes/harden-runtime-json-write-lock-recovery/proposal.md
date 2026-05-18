## Why

FlowPilot can mis-handle transient Windows JSON file locks as fatal daemon errors
or PM semantic repair blockers. This breaks active runs even though the underlying
condition is usually a mechanical runtime write collision or a dead-owner lock
that can be waited out or taken over.

## What Changes

- Treat transient `PermissionError` failures during atomic JSON replacement as
  runtime write-lock contention for daemon-critical ledgers instead of surfacing
  raw fatal exceptions.
- Keep daemon `RouterLedgerWriteInProgress` handling side-effect safe: status and
  state persistence during the wait path must not convert a recoverable write
  wait into a daemon error.
- Preserve dead-owner lock takeover evidence and resume normal daemon flow after
  takeover.
- Classify runtime JSON write-lock failures as mechanical runtime settlement
  issues, not PM semantic repair, until bounded wait/takeover recovery has been
  attempted.
- Add FlowGuard and ordinary regression coverage for scheduler ledger,
  `router_state.json`, and Controller action JSON write-lock failure shapes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtime-ledger-persistence`: Runtime JSON write locks and Windows replace
  failures must settle without corrupting ledgers or crashing the daemon.
- `persistent-router-daemon`: The daemon must remain live or cleanly deferred
  when a recoverable runtime write lock is encountered, including locks hit
  while recording wait status.
- `blocker-repair-policy`: Mechanical runtime write-lock failures must not be
  routed as PM semantic repair before runtime settlement/takeover has been tried.

## Impact

- Runtime JSON helpers in `skills/flowpilot/assets/flowpilot_router_io.py`.
- Router daemon wait/error handling in
  `skills/flowpilot/assets/flowpilot_router_daemon_runtime.py`.
- Control-blocker classification paths that receive `RouterLedgerWriteInProgress`
  from runtime ledger writes.
- FlowGuard persistent daemon model/checks and focused router runtime tests.
- Local installed FlowPilot skill sync and install audit after the source fix.
