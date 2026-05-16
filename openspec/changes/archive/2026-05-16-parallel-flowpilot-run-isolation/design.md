## Context

FlowPilot currently has a top-level `.flowpilot/current.json` pointer and
run-scoped directories under `.flowpilot/runs/<run-id>/`. Earlier work already
moved most durable runtime state into run-scoped files, but the Router daemon
still reloads the current pointer during ticks. That is safe only if one
FlowPilot exists at a time.

The target behavior is parallel-safe:

```text
.flowpilot/index.json          catalog of runs
.flowpilot/current.json        UI focus / default target only
.flowpilot/runs/run-A/         run A state, lock, daemon status, board
.flowpilot/runs/run-B/         run B state, lock, daemon status, board
```

## Optimization Inventory

| Order | Optimization point | Current behavior | Target behavior | Verification |
| --- | --- | --- | --- | --- |
| 1 | Record the plan and risk matrix | The parallel-run risk exists only in discussion and runtime evidence | OpenSpec design records exact slices, bugs, and model coverage | OpenSpec validate |
| 2 | FlowGuard run-isolation model | Existing models cover daemon and cross-plane risks, but not parallel current-pointer focus changes | Add focused model where bad variants fail and safe parallel plan passes | `run_flowpilot_parallel_run_isolation_checks.py` |
| 3 | Daemon run binding | Daemon starts from current run, then ticks reload current pointer | Daemon startup and tick use immutable bound `run_id/run_root` | Unit test fast restart with old daemon tick |
| 4 | Daemon CLI target | `daemon` and `daemon-stop` default to current run only | CLI and Python functions accept explicit `--run-id` or `--run-root`, while current remains default | Unit tests for targeted stop/start |
| 5 | Lock lifecycle | A released lock can be refreshed back to active by a still-running daemon loop | Released/error/terminal locks stay non-active and daemon exits cleanly | Unit test release cannot reactivate |
| 6 | Active task projection | Non-current running index entries are marked stale | Non-current running runs remain background active unless lock/process evidence says stale | Unit test non-current running stays running |
| 7 | Board projection | Any ledger row can make the board look non-empty | Status distinguishes historical done rows from active work rows | Unit test done-only board has zero active work |
| 8 | Sync installed skill | Repo and local installed skill may diverge | Sync after focused checks pass | install sync and audit commands |

## Risk Catalog

| Risk ID | Possible bug | Why it matters | FlowGuard coverage |
| --- | --- | --- | --- |
| R1 | Old daemon reads new `current.json` after focus changes | Cross-run writes corrupt the old run or new run | `daemon_reads_current_after_focus_change` |
| R2 | Daemon writes to a run different from its bound run | Boards, locks, and receipts are no longer trustworthy | `daemon_cross_writes_other_run` |
| R3 | Two daemons write the same run | Ledger corruption or duplicate rows | `duplicate_writer_same_run` |
| R4 | Different runs are blocked from parallel execution | Future multi-FlowPilot usage breaks | `parallel_runs_forced_singleton` |
| R5 | Non-current active run is marked stale just because focus moved | Background FlowPilot runs disappear or get misreported | `focus_change_marks_background_run_stale` |
| R6 | Stop command without target releases the wrong run | One FlowPilot can stop another | `untargeted_stop_releases_wrong_run` |
| R7 | Released lock is refreshed back to active | UI believes a stopped daemon is still alive | `released_lock_reactivated` |
| R8 | Status reports active with no live process | Controller or UI waits on a dead daemon | `active_status_without_live_process` |
| R9 | Historical done row is reported as active work | User sees "background board not empty" when no work is pending | `done_history_reported_as_active_work` |
| R10 | `current.json` remains a hidden daemon authority | Future code reintroduces the same bug class | `current_focus_used_as_daemon_authority` |
| R11 | Prompt/docs keep saying non-current means stale | A future role or agent may undo the parallel semantics | Covered by prompt/protocol text review |
| R12 | Peer-agent changes are overwritten | Other in-progress optimizations are lost | Covered by git status checks and scoped edits |

## FlowGuard Coverage Matrix

| Planned change | Modeled state/events | Known-bad hazards that must fail | Safe path that must pass |
| --- | --- | --- | --- |
| Immutable daemon binding | `daemon_bound_run`, `current_focus`, `tick_source` | R1, R2, R10 | Old daemon ticks after focus moves and still writes only its bound run |
| Per-run writer lock | `writer_count_by_run`, `parallel_run_count` | R3, R4 | Run A and Run B each have one writer |
| Targeted stop | `stop_target`, `released_run`, `other_run_active` | R6 | Stop A releases A only and leaves B active |
| Lock terminal handling | `lock_status`, `refresh_after_release`, `process_live` | R7, R8 | Released lock remains released and status is non-live |
| Active task projection | `focus_run`, `background_run_status` | R5 | Background active run remains running but is not UI focus |
| Board active-work projection | `done_rows`, `active_rows`, `reported_active_work` | R9 | Done-only board reports zero active work |

## Decisions

1. `current.json` is UI focus/default target, not daemon authority.
   - A CLI without `--run-id` or `--run-root` may still default to current for
     operator convenience.
   - Once a daemon starts, it must not use current to choose its state root.

2. Parallelism is per run, not per repository singleton.
   - The invariant is one daemon writer for one run.
   - Two different run roots may have two different daemon locks.

3. Stop is target-scoped.
   - Default stop may target current for backward compatibility.
   - Explicit `--run-id`/`--run-root` is required for automation-safe stop and
     for future UI controls.

4. Non-current is not stale.
   - Stale requires evidence such as expired lock, missing process, missing
     state, or explicit supersession.

5. Board "active work" means unfinished rows.
   - Historical `done` rows remain audit evidence but do not mean there is
     pending background work.

## Migration Plan

1. Add the focused FlowGuard model and runner.
2. Prove known-bad hazards fail and the safe plan passes.
3. Add bound-run load helpers and daemon CLI target arguments.
4. Update daemon subprocess spawn and tests to pass the bound run root.
5. Update daemon tick and start attach code to reload from the bound run root.
6. Harden lock refresh/release status so stop cannot reactivate a lock.
7. Update active task projection so non-current running runs remain background
   active instead of stale.
8. Add board active-work counts.
9. Run focused model and targeted runtime tests after each slice.
10. Sync the installed local FlowPilot skill and verify freshness.

## Residual Risk

- Existing UI code outside this Python router may still display "current" as
  if it were the only active run. This change fixes the router/runtime
  authority boundary and exposes safer metadata, but a separate UI pass may
  improve presentation.
- Meta and Capability simulations are skipped by user direction. The focused
  model owns this change boundary; broad route/capability confidence remains
  deferred.
