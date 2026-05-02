# FlowPilot Global Watchdog Supervisor Automation Prompt

This prompt is intended for a Codex app `cron` automation, not a Windows
scheduled task. The schedule belongs to the automation metadata; use the fixed
30-minute interval. Do not expose a configurable cadence for this supervisor.

Run the FlowPilot global watchdog supervisor scan for this user environment.
Use `$FLOWPILOT_GLOBAL_RECORD_DIR` when set; otherwise use
`$CODEX_HOME/flowpilot/watchdog`.

Steps:

1. Load the global watchdog registry.
2. Run `python scripts/flowpilot_global_supervisor.py --json` from the
   FlowPilot skill/project workspace.
3. Treat inactive or expired project registrations as not eligible for reset.
4. For each project result with `controller_action.required: true`, confirm
   the project-local state is still running and the route generation is not
   superseded.
5. Use the Codex app automation interface to update the recorded heartbeat
   automation id to `PAUSED`, then back to `ACTIVE`.
6. Do not edit `automation.toml` directly.
7. Do not treat the reset as recovery proof. Recovery proof is a later
   heartbeat with a newer timestamp.
8. Write or preserve the scanner's local/global supervisor evidence. If the
   official reset fails, record the failure and do not retry indefinitely for
   the same cooldown key.
9. If the scanner reports no active, unexpired project registrations, delete
   this user-level global supervisor last after confirming no other FlowPilot
   route still needs it.

Hard boundaries:

- This is the official user-level global supervisor because it runs inside
  Codex and can call the official automation API.
- Windows Task Scheduler or other external processes may observe and write
  evidence only; they must not be modeled as the official global reset actor.
- There must be only one active FlowPilot global watchdog supervisor automation
  per user environment.

Creation and verification contract:

- When heartbeat and watchdog are established for a formal long-running
  FlowPilot route, also verify this singleton supervisor.
- Each project heartbeat must refresh its own global registration lease before
  continuing route work.
- First inspect existing Codex cron automations by id, name, and prompt. Reuse
  one active singleton at the fixed cadence. If exactly one paused singleton
  exists and at least one project registration is active, update that existing
  automation to `ACTIVE` with the fixed cadence rather than creating a
  duplicate.
- Create only when no singleton exists and at least one project registration is
  active.
- On pause, stop, or completion, unregister the current project first, stop the
  project heartbeat/watchdog, reread the registry under the singleton lock, and
  delete the user-level global supervisor last only when no active,
  unexpired registrations remain.
- Use the Codex app automation interface, not file edits. With the current
  `automation_update` tool shape, use these fields:
  - `mode`: `create`
  - `kind`: `cron`
  - `name`: `FlowPilot Global Watchdog Supervisor`
  - `rrule`: `FREQ=MINUTELY;INTERVAL=30`
  - `cwds`: the FlowPilot skill/project workspace as a single string path
  - `executionEnvironment`: `local`
  - `model`: a supported Codex automation model
  - `reasoningEffort`: `medium`
  - `status`: `ACTIVE`
- Do not pass `cwds` as an array for this creation path unless the Codex app
  automation interface explicitly requires it in a future version.
