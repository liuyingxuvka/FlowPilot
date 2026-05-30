## Why

The new FlowPilot runtime already has foreground duty, timed patrol, progress,
and liveness recovery states, but the latest live audit exposed three remaining
control-plane gaps: user stop/cancel is not a durable terminal fence, real host
liveness such as `not_found` is not bridged into the current-run ledger, and
completed mechanical evidence can be orphaned without a formal result envelope.

This change borrows the useful old Router ideas without restoring the old
daemon, fixed crew topology, monitor UI, or compatibility surface.

## What Changes

- Add first-class `stop` and `cancel` commands for `flowpilot_new.py` that mark
  the active new-runtime run terminal, close active leases, settle open packets
  as stopped/cancelled, refresh lifecycle guard/foreground duty, and update the
  current-run pointer without claiming project completion.
- Add a public host-liveness report path so current host observations
  (`active`, `still_working`, `not_found`, `cancelled`, `timeout_unknown`,
  `completed_without_result`, `no_output`) become machine-readable lease
  evidence instead of chat-only status.
- Extend wait recovery so current host failure or no-output evidence overrides
  stale progress and routes to recovery/reissue, while ordinary progress still
  remains liveness-only and never completes a packet.
- Detect FlowGuard/mechanical runner evidence that completed without a formal
  result envelope and expose an orphan-evidence recovery duty instead of
  waiting forever.
- Add FlowGuard model coverage, public fake AI rehearsal, and focused tests for
  stop/cancel fences, host `not_found` after progress, completed-without-result
  no-output, and orphan FlowGuard evidence recovery.
- Sync the installed local `flowpilot` skill and commit the scoped local git
  version after validation.

## Capabilities

### New Capabilities

- `new-flowpilot-stop-host-orphan-recovery`: New-runtime terminal lifecycle,
  host-liveness, no-output, and orphan-evidence recovery contract.

### Modified Capabilities

- `runtime-ledger-persistence`: Persist stop/cancel terminal state, host
  liveness evidence, orphan evidence records, lease closures, and foreground
  duty refreshes in the current-run ledger.
- `multiround-fake-ai-control-rehearsal`: Rehearse stop/cancel, host loss after
  progress, no-output, and orphan-evidence branches through public new-runtime
  CLI surfaces.
- `known-friction-regression-gates`: Treat the observed active run class
  (`active` lease plus missing host/result/orphan evidence) as a required
  regression family before claiming the control plane is clean.

## Impact

- Runtime: `skills/flowpilot/assets/ai_project_runtime/runtime.py`,
  `skills/flowpilot/assets/ai_project_runtime/host.py`,
  `skills/flowpilot/assets/flowpilot_new.py`
- Models/rehearsals: lifecycle guard, fake project rehearsal, a focused
  FlowGuard model/check for stop-host-orphan recovery, and known-friction
  regression wiring.
- Tests: focused new-runtime lifecycle tests and fake AI public CLI rehearsal.
- Install/git: synchronize the local installed skill and commit only the scoped
  files for this change, preserving peer-agent edits.
