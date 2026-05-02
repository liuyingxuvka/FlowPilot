# External Watchdog Loop Findings

This process-preflight model covers the outside-of-thread FlowPilot watchdog.
It exists because Codex host automation can be present and marked active while
the `.flowpilot` heartbeat evidence stops advancing.

## Modeled Rule

The watchdog is a third continuity layer:

1. FlowPilot heartbeat records inside `.flowpilot/heartbeats/`;
2. Codex host/thread automation when the host supports it;
3. an external process that checks for stale heartbeat evidence and requires
   FlowPilot to reset the active heartbeat automation through the official
   Codex app automation interface.

The watchdog does not edit `automation.toml` directly. The supported recovery
path is an official Codex app automation update: set the active heartbeat
automation to `PAUSED`, then back to `ACTIVE`. The reset is a recovery action;
a later new heartbeat is the proof.

The bundled watchdog writes both project-local evidence and a compact
user-level global record. The local `.flowpilot/watchdog/` evidence remains
authoritative; the global registry is only an index for a singleton supervisor
that must reread local state and watchdog evidence before recording a reset
requirement.

The watchdog also checks `.flowpilot/busy_lease.json`. Codex thread heartbeats
cannot interrupt a turn that is already running a long bounded operation, so
an old heartbeat timestamp is not automatically a stalled route. If a
route/node-matched busy lease is active and non-expired, the watchdog records
`busy_not_stale` and does not require reset. If a matching lease was just
cleared, the watchdog records `post_busy_grace` until the bounded grace window
expires. Default grace is 10x the heartbeat interval, so a one-minute heartbeat
gets a 10-minute post-busy window. Missing, old-cleared, expired, mismatched,
or malformed leases do not suppress reset.

The lifecycle is paired with the heartbeat. When FlowPilot creates or repairs a
real heartbeat continuation for a long-running formal route, it must create or
verify the external watchdog automation in the same setup window. When the
route reaches terminal closure, FlowPilot stops or deletes the watchdog first,
records that evidence, and only then stops or deletes the heartbeat
automation.

That pairing is stable lifecycle state. Checkpoint writes, node transitions,
user-flow-diagram refreshes, and visible plan syncs must preserve the recorded watchdog
policy and automation pairing. They may inspect watchdog evidence, but they
must not recreate, re-register, start, restart, or re-enable the paired
watchdog automation.

Windows Task Scheduler watchdogs must also be hidden/noninteractive. The
supported local setup helper is `scripts/register_windows_watchdog_task.ps1`,
which uses `pythonw.exe` when available or a hidden noninteractive PowerShell
wrapper. A direct interactive `python.exe` scheduled-task action can flash a
console window and is treated as a configuration failure risk.

The global supervisor is a Codex app cron automation, not a Windows scheduled
task. It must be singleton per user environment. Use
`templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md` as the
prompt source when creating or repairing it through the Codex automation
interface. Verify it in the same setup step that creates or repairs heartbeat
and watchdog. With the current Codex automation interface, use `kind: cron`,
`rrule: FREQ=MINUTELY;INTERVAL=30`, `cwds` as one workspace string path,
`executionEnvironment: local`, `reasoningEffort: medium`, and `status:
ACTIVE`. The cadence is fixed at 30 minutes. Project heartbeats refresh their
own global registration lease, and terminal/pause cleanup unregisters the
project before deleting the user-level global supervisor last when no active,
unexpired registrations remain. Windows Task Scheduler is only valid for
per-project external watchdogs that observe heartbeat freshness; it is not the
official global reset actor.

## Checks

```powershell
python .flowpilot/task-models/external-watchdog-loop/run_checks.py
```

Result after paired lifecycle, busy-lease, and global-record modeling:

- external watchdog loop: 25 states;
- external watchdog loop: 24 edges;
- 0 invariant failures;
- 0 missing labels;
- 0 stuck states.

Project-control regression checks also passed after adding the paired
lifecycle gate:

- meta model: 5304 states, 5901 edges;
- capability model: 330 states, 341 edges;
- 0 invariant failures, 0 missing labels, and 0 stuck states.

## Terminal Decisions

- `healthy`: latest heartbeat is inside the stale threshold; no reset attempt.
- `busy_not_stale`: latest heartbeat is older than the stale threshold, but a
  matching active non-expired busy lease proves bounded work is in progress.
- `post_busy_grace`: latest heartbeat is older than the stale threshold, but a
  matching busy lease was recently cleared and the post-busy heartbeat grace
  window has not expired.
- `stale_official_reset_required`: latest heartbeat is stale and FlowPilot must
  invoke the official Codex app reset.
- `recovered_after_official_reset`: the official `PAUSED -> ACTIVE` reset was
  accepted and a later heartbeat appeared.
- `stale_official_reset_failed`: latest heartbeat is stale and the official
  reset failed or was rejected.

## Protocol Impact

FlowPilot long-running routes should record an external watchdog policy:

- stale threshold;
- evidence path under `.flowpilot/watchdog/`;
- user-level global watchdog record path and registry entry;
- active automation metadata and official reset result;
- busy lease path, bounded active-work suppression policy, and post-busy grace
  window;
- paired heartbeat/watchdog lifecycle metadata;
- host automation metadata when available;
- no file-level automation record mutation as a recovery path;
- no scheduled-task restart caused by ordinary checkpoint or node progress;
- hidden/noninteractive Windows scheduled-task action when Task Scheduler is
  used;
- singleton user-level global supervisor for cross-project stale-event
  revalidation;
- no false guarantee that automation reset alone resumes the Codex model;
- terminal shutdown order: watchdog first, heartbeat second.
