# FlowPilot Global Watchdog Supervisor Automation Prompt

This prompt is intended for a Codex controller turn or a quiet thread-bound
`heartbeat` automation, not a Windows scheduled task. Do not install a
high-frequency Codex `cron` by default: cron runs create standalone Codex jobs
and can flood the user's conversation list. Use legacy cron only after explicit
user opt-in that accepts that UI cost.

Run the FlowPilot global watchdog supervisor scan for this user environment.
Use `$FLOWPILOT_GLOBAL_RECORD_DIR` when set; otherwise use
`$CODEX_HOME/flowpilot/watchdog`.

Steps:

1. Load the global watchdog registry.
2. Run `python scripts/flowpilot_global_supervisor.py --json` from the
   FlowPilot skill/project workspace.
3. For each project result with `controller_action.required: true`, confirm
   the project-local state is still running and the route generation is not
   superseded.
4. Use the Codex app automation interface to update the recorded heartbeat
   automation id to `PAUSED`, then back to `ACTIVE`.
5. Do not edit `automation.toml` directly.
6. Do not treat the reset as recovery proof. Recovery proof is a later
   heartbeat with a newer timestamp.
7. Write or preserve the scanner's local/global supervisor evidence. If the
   official reset fails, record the failure and do not retry indefinitely for
   the same cooldown key.

Hard boundaries:

- This is the official user-level global supervisor because it runs inside
  Codex and can call the official automation API.
- Windows Task Scheduler or other external processes may observe and write
  evidence only; they must not be modeled as the official global reset actor.
- There must be only one active FlowPilot global watchdog supervisor automation
  per user environment.
- A default supervisor must be conversation-quiet: repeated checks should
  continue in one thread rather than create a new Codex conversation per run.

Creation and verification contract:

- When heartbeat and watchdog are established for a formal long-running
  FlowPilot route, also verify this singleton supervisor.
- First inspect existing Codex automations by id, name, kind, and prompt.
  Reuse one active quiet `heartbeat` singleton. If an active legacy `cron`
  singleton exists, pause or replace it with a quiet heartbeat when the user
  wants conversation hygiene. If no quiet singleton exists, record
  `setup_required` or run this prompt on demand; do not auto-create cron.
- Use the Codex app automation interface, not file edits. With the current
  `automation_update` tool shape, the preferred quiet creation uses:
  - `mode`: `create`
  - `kind`: `heartbeat`
  - `name`: `FlowPilot Global Watchdog Supervisor`
  - `rrule`: `FREQ=MINUTELY;INTERVAL=10`
  - `destination`: `thread`
  - `status`: `ACTIVE`
- Legacy `cron` creation is an explicit opt-in fallback only. If used, pass
  `cwds` as the FlowPilot skill/project workspace string, use local execution,
  and record that the user accepted new-conversation noise.
