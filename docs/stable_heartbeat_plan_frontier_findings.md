# Stable Heartbeat And Execution Frontier Findings

Date: 2026-05-01

## Scope

This model covers the FlowPilot control loop where heartbeat automation remains
a stable launcher while route changes, next-node decisions, and the visible
Codex plan are stored in persistent `.flowpilot` state.

## Design Result

The stable heartbeat prompt is not the route state. It loads:

- `.flowpilot/state.json`;
- the active route `flow.json`;
- `.flowpilot/execution_frontier.json`;
- latest heartbeat evidence;
- latest watchdog evidence.

The execution frontier stores the active route version, active node, next node,
current mainline, fallback, current-node completion guard, PM completion
runway, checks before advance, current chunk, next chunk, and visible Codex
plan projection. When the route changes or heartbeat resumes, FlowPilot
rechecks the affected route/subtree when needed, rewrites the frontier, asks
the PM for a completion-oriented runway, syncs the visible plan from that
runway, and continues without rewriting the heartbeat automation prompt.

At terminal closure, the paired watchdog shutdown is also written back to the
frontier. FlowPilot stops or deletes the watchdog first, writes watchdog
inactive and terminal heartbeat lifecycle state to local state/frontier evidence,
and only then stops or pauses the heartbeat. This is a final writeback gate, not
a repeated polling requirement during ordinary progress.

Pause, restart, and terminal cleanup now share one lifecycle reconciliation
gate. The controller scans Codex automation records, the global supervisor and
registry, Windows scheduled tasks, local state, execution frontier, and
watchdog evidence before claiming the lifecycle state is clean. Disabled
Windows FlowPilot scheduled tasks are residual lifecycle objects until
unregistered or explicitly waived. `scripts/flowpilot_lifecycle.py` provides
the read-only inventory and required-action list.

`next_node` is only a planned jump while the current node is unfinished. If
`unfinished_current_node` is true or
`current_node_completion.advance_allowed` is false, the heartbeat resumes
`active_node`. The PM resume decision must still be a long runway toward
completion, not a one-gate instruction.

## Findings From Simulation

The first model exposed two workflow bugs:

1. A route version could change while the old execution frontier and plan
   remained synced to the previous route version. That creates a stale
   next-jump path. The revised model now blocks work until frontier and plan
   versions match the checked route version.
2. A heartbeat could read a synced frontier and jump directly to `next_node`
   even though the current node had not written validation and completion
   evidence. The revised model requires a current-node completion guard before
   advance.
3. Unbounded route mutation in the abstract model caused state-space expansion.
   The task-local model bounds mutations for analysis while the runtime
   protocol still supports repeated route changes through checked route
   versions.
4. Route-013 exposed a terminal lifecycle writeback bug: external shutdown
   evidence showed the watchdog had been deleted, but local frontier/watchdog
   state still said `active: true`. The model now requires
   `terminal_lifecycle_frontier_written` before completion.

## Final Check Result

Command:

```powershell
python .flowpilot/task-models/stable-heartbeat-plan-frontier/run_checks.py
```

Result:

- states: 28
- edges: 27
- invariant failures: 0
- missing labels: 0
- progress findings: 0
- stuck states: 0
- non-terminating components: 0

The main meta and capability models now include `execution_frontier_written`
and `codex_plan_synced` before behavior-bearing work.
