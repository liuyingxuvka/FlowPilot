## Why

A live fast-restart sequence showed that an older Router daemon can reload the
top-level current pointer after a newer FlowPilot run starts. The older daemon
then writes mixed run metadata and can leave stale active-looking daemon status.

That bug is a single-run assumption leaking into runtime control. Future
FlowPilot usage must allow multiple FlowPilot runs to exist and, where the host
permits it, run in parallel. The top-level current pointer can be a UI focus
hint, but it must not be daemon authority.

## What Changes

- Bind every Router daemon to one immutable `run_id` and `run_root` at startup.
- Pass the bound run identity to daemon subprocesses and daemon-stop commands.
- Make daemon ticks reload state from the bound run root, not from
  `.flowpilot/current.json`.
- Treat non-current running runs as background/parallel runs, not stale merely
  because UI focus moved.
- Preserve one Router writer per run while allowing different runs to have
  independent locks.
- Prevent released/error/terminal daemon locks from being refreshed back to
  active.
- Project controller work boards by active rows (`pending`, `waiting`,
  `in_progress`, repair states), not by historical `done` rows.

## Capabilities

### New Capability

- `parallel-flowpilot-run-isolation`: multiple run roots can coexist without
  daemon cross-writes or focus-pointer authority leaks.

### Modified Capabilities

- `startup-daemon-first-driver`: the daemon subprocess is launched with an
  explicit run binding.
- `daemonize-flowpilot-router`: daemon tick, stop, status, and lock refresh are
  run-scoped.
- `cross-plane-runtime-friction`: active UI task projection distinguishes UI
  focus from background active runs.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `tests/test_flowpilot_router_runtime.py`
- Focused FlowGuard model and runner under `simulations/`
- OpenSpec artifacts for this change
- Local installed FlowPilot skill copy after verification

Heavyweight Meta and Capability simulations are skipped for this change by
user direction. Focused FlowGuard checks and targeted runtime tests are
required before and after production edits.
