## Why

FlowPilot can leave a runtime JSON `.write.lock` behind after a successful
write if the final lock cleanup fails. If the owning process is still the live
Router daemon, the current liveness rule treats that lock as another active
writer forever. The daemon then blocks future writes to the same ledger even
though the target JSON is complete and the writer is itself.

## What Changes

- Distinguish the current daemon's own lock from another live process lock.
- Keep normal same-call cleanup simple: after a successful write, retry lock
  unlink briefly and record cleanup failure diagnostics if it still fails.
- Recover only later-discovered self-owned stale locks after safety checks:
  lock age is stale, target JSON is valid, and no matching temporary write file
  remains.
- Keep other live-owner locks protected; do not steal a lock from another live
  process.
- Extend FlowGuard and focused runtime tests for self-owned stale locks,
  cleanup-failure diagnostics, and unsafe recovery rejection.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtime-ledger-persistence`: Runtime JSON write-lock liveness classifies
  self-owned stale locks separately from other live owners and records cleanup
  diagnostics.
- `persistent-router-daemon`: Daemon replay may clear its own stale write-lock
  sentinel only after safe artifact checks, then rejoin normal replay.
- `blocker-repair-policy`: Self-owned runtime write-lock recovery remains a
  mechanical persistence settlement issue before PM semantic repair.

## Impact

- Runtime JSON helper in `skills/flowpilot/assets/flowpilot_router_io.py`.
- Focused startup/daemon runtime tests in `tests/router_runtime/startup_daemon.py`
  and the startup daemon aggregate.
- Persistent daemon FlowGuard model and runner.
- Local installed FlowPilot skill sync, install audit, and local git commit.
