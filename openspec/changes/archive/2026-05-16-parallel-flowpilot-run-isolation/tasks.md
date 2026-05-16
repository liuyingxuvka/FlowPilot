## 1. Model Hardening Gate

- [x] 1.1 Add a focused FlowGuard model for parallel FlowPilot run isolation.
- [x] 1.2 Add known-bad hazards for current-pointer daemon authority, cross-run writes, duplicate same-run writers, singleton-only parallelism, focus-based stale marking, untargeted stop, lock reactivation, active-without-process status, done-history active-work confusion, and hidden current authority.
- [x] 1.3 Add safe scenarios for two parallel runs, per-run daemon locks, focus changes, targeted stop, released-lock exit, and done-only board projection.
- [x] 1.4 Run the focused FlowGuard checks and prove hazards fail while the safe plan passes.
- [x] 1.5 Record that Meta and Capability heavyweight simulations are skipped by user direction.

## 2. Runtime Binding

- [x] 2.1 Add run-scoped state loading helpers that do not consult `.flowpilot/current.json`.
- [x] 2.2 Bind `run_router_daemon` to an explicit `run_id` or `run_root` when provided.
- [x] 2.3 Pass the bound run root to the daemon subprocess spawned during startup.
- [x] 2.4 Update daemon tick and daemon startup attach paths to reload only the bound run state.

## 3. Stop And Lock Lifecycle

- [x] 3.1 Add explicit daemon-stop target arguments for `run_id` and `run_root`.
- [x] 3.2 Ensure released/error/terminal locks are not refreshed back to active.
- [x] 3.3 Ensure daemon status reports non-live when the lock is released, stale, error, terminal, or process-missing.

## 4. Parallel Projection

- [x] 4.1 Stop marking non-current running index entries as `stale_not_current`.
- [x] 4.2 Expose non-current running runs as background active/focus-not-selected metadata.
- [x] 4.3 Add active-work counts so done-only controller ledgers do not look like live work.
- [x] 4.4 Update prompt/protocol text that describes current pointer authority if needed.

## 5. Verification And Sync

- [x] 5.1 Run focused FlowGuard checks before production edits.
- [x] 5.2 Run targeted runtime tests after each implementation slice.
- [x] 5.3 Rerun the focused FlowGuard checks after production edits.
- [x] 5.4 Run install sync, install check, and local sync audit.
- [x] 5.5 Update FlowGuard adoption logs with commands, skipped heavy checks, findings, and residual risk.
- [x] 5.6 Run KB postflight and record reusable lessons.
