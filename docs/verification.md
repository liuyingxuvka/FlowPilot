# Verification

## Preflight Checks

Run:

```powershell
python simulations/run_startup_guard_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/smoke_autopilot.py
```

Expected:

- zero invariant failures;
- zero missing required labels;
- zero progress findings;
- zero stuck states;
- reachable success.
- execution frontier and visible Codex plan sync labels are present before
  behavior-bearing work.
- startup guard checks reject shadow routes and require the guard pass before
  child-skill, imagegen, implementation, or route-execution work.

Route-local models under `.flowpilot/task-models/` belong to an adopted target
project's runtime evidence. They should be checked when present in that target
project, but this public package check does not require this repository's
private development `.flowpilot/` state.

## Install Checks

Run:

```powershell
python scripts/check_install.py
```

Expected:

- real FlowGuard import works;
- required project files exist;
- `skills/flowpilot/SKILL.md` exists and declares `name: flowpilot`;
- reusable FlowPilot templates exist;
- simulation scripts exist;
- template JSON files parse.
- `templates/flowpilot/execution_frontier.template.json` parses.
- If local `.flowpilot/` runtime state exists, its main JSON files parse.

## Smoke Checks

Run:

```powershell
python scripts/smoke_autopilot.py
```

Expected:

- meta simulation passes;
- capability simulation passes.
- startup guard simulation passes.

## Startup Guard Check

For an active target project after route, state, frontier, crew, role memory,
continuation, and visible-plan evidence have been written, run:

```powershell
python scripts/flowpilot_startup_guard.py --root . --route-id <active-route> --record-pass --json
```

Expected:

- `state.json`, `execution_frontier.json`, and `routes/<active-route>/flow.json`
  agree on the same active nonterminal route;
- `crew_ledger.json` is current for that route and all six role memory packets
  are present and current;
- continuation is either a complete automated bundle or explicit
  `manual-resume` evidence with no automation claim;
- `startup_activation.live_subagent_startup` records either six live
  background agents started/resumed after a user decision or explicit
  user-authorized single-agent six-role continuity;
- `startup_activation` in state and frontier records the hard gate;
- the command writes `.flowpilot/startup_guard/latest.json` and sets
  `work_beyond_startup_allowed: true`.

If this command fails, FlowPilot must not run child skills, image generation,
implementation, route chunks, or completion work. A route-local file without
matching canonical state/frontier/crew/continuation evidence is a shadow route,
not a recoverable partial pass.

## External Watchdog Check

Run:

```powershell
python scripts/flowpilot_watchdog.py --root . --stale-minutes 10 --dry-run --json
python scripts/flowpilot_global_supervisor.py --status --json
```

The default stale threshold is 10 minutes. For long operations that may run
past the stale threshold, create a bounded busy lease before the operation and
clear it afterward. Clearing the lease
starts a bounded post-busy grace window, defaulting to 10x the heartbeat
interval, before stale reset can be required:

```powershell
python scripts/flowpilot_busy_lease.py start --root . --operation "build or validation step" --max-minutes 30 --json
python scripts/flowpilot_busy_lease.py clear --root . --reason "operation finished" --json
```

For command-line operations, prefer the wrapper so start/clear evidence cannot
be forgotten:

```powershell
python scripts/flowpilot_run_with_busy_lease.py --root . --operation "long validation step" --max-minutes 30 -- python -c "print('ok')"
```

For Windows Task Scheduler watchdogs, use the bundled helper so the task is
hidden/noninteractive:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_windows_watchdog_task.ps1 `
  -TaskName "FlowPilot Route XXX Watchdog" `
  -ProjectRoot . `
  -HeartbeatAutomationId "<heartbeat-automation-id>"
```

Inspect or disable a residual watchdog without starting it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_windows_watchdog_task.ps1 `
  -TaskName "FlowPilot Route XXX Watchdog" -Status

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_windows_watchdog_task.ps1 `
  -TaskName "FlowPilot Route XXX Watchdog" -Disable
```

Verify the user-level singleton global supervisor through the Codex app
automation interface. It should be a `cron` automation, use the prompt in
`templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md`, and run
at the fixed 30-minute cadence. Do not create a Windows global scheduled task
for this role.

With the current Codex app `automation_update` interface, use `kind: cron`,
`rrule: FREQ=MINUTELY;INTERVAL=30`, `cwds` as a single workspace string path,
`executionEnvironment: local`, `reasoningEffort: medium`, and `status:
ACTIVE`. Inspect existing Codex cron automations before creation. Reuse one
active singleton, update one paused singleton when global protection is
required, and create only when no singleton exists and at least one active
project registration exists. Verify every heartbeat refreshes its global
registration lease. On pause, stop, or completion, unregister the project first
and delete the global supervisor last only after confirming that no active,
unexpired registrations remain.

Expected:

- the active route and latest heartbeat are loaded;
- project-local watchdog evidence includes a `global_record` link unless global
  recording was explicitly disabled for a test;
- the user-level global registry is treated as an index and the supervisor
  rereads project-local evidence before recording reset requirements;
- at most one Codex global supervisor automation is active;
- lifecycle metadata shows the watchdog is paired with the heartbeat and, for
  active long-running routes, the watchdog automation is active;
- for Windows scheduled tasks, lifecycle metadata shows
  `hidden_noninteractive: true` and `visible_window_risk: false`;
- for terminal routes, lifecycle metadata shows the watchdog is inactive and
  terminal lifecycle writeback is recorded in local state/frontier evidence;
- when a heartbeat is old but a valid busy lease matches the current route and
  node, the decision is `busy_not_stale` and reset is not required;
- when a heartbeat is old and a matching busy lease was recently cleared inside
  the grace window, the decision is `post_busy_grace` and reset is not
  required yet;
- `source_status.trusted_for_decision` lists only `state_json`,
  `latest_heartbeat`, and `busy_lease_json`;
- `source_status.live_subagent_state_used` is `false`;
- stale or disagreeing `execution_frontier.json` and `lifecycle/latest.json`
  appear as diagnostic drift warnings, not as reset-decision authorities;
- host automation metadata is reported when available;
- stale heartbeats produce `stale_official_reset_required` until FlowPilot
  invokes the official Codex app automation reset;
- the script does not claim recovery until a later heartbeat appears.

After FlowPilot invokes the official reset through the Codex app automation
interface, record that result:

```powershell
python scripts/flowpilot_watchdog.py --root . --stale-minutes 10 --official-reset-attempted --official-reset-ok --json
```

## Lifecycle Reconciliation Check

Before pausing, restarting, or closing a formal route, run a unified lifecycle
inventory:

```powershell
python scripts/flowpilot_lifecycle.py --root . --mode pause --include-windows-tasks --write-record --json
python scripts/flowpilot_lifecycle.py --root . --mode restart --include-windows-tasks --write-record --json
python scripts/flowpilot_lifecycle.py --root . --mode terminal --include-windows-tasks --write-record --json
```

Use the mode that matches the lifecycle operation. The command is read-only
except for writing `.flowpilot/lifecycle/latest.json` and events. It does not
change Codex automations or Windows tasks. If it reports required actions,
complete them through the official Codex app automation interface or the
Windows task helper, then rerun the inventory before claiming pause, restart,
or terminal cleanup.

Expected:

- Codex automations, global supervisor records, Windows scheduled tasks, local
  state, execution frontier, and watchdog evidence are all represented;
- disabled Windows FlowPilot scheduled tasks are reported as residual actions
  unless explicitly waived;
- local state/frontier/watchdog lifecycle fields agree with the intended
  operation;
- `.flowpilot/lifecycle/latest.json` exists for the latest lifecycle operation.
