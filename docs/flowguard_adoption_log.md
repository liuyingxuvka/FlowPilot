# FlowGuard Adoption Log

This human-readable log summarizes FlowGuard adoption records for major protocol changes.
Machine-readable entries live in `.flowguard/adoption_log.jsonl`.

## 2026-05-02 - Control Surface Protocol Patches

- Trigger: the watchdog must not inspect unreliable background-agent busy state, and FlowPilot needed the four protocol patches for local busy leases, Mermaid route maps, role identity, and source drift evidence.
- Decision: `use_flowguard`.
- Models updated: `.flowpilot/task-models/control-surface-protocol-patches/`, `.flowpilot/task-models/external-watchdog-loop/`, `simulations/meta_model.py`, and `simulations/capability_model.py`.
- Main findings:
  - Long operations now require the busy-lease wrapper policy and terminal checkpoints require cleared leases.
  - Watchdog decisions trust only `state.json`, latest heartbeat evidence, and `busy_lease.json`.
  - `execution_frontier.json`, lifecycle records, automation metadata, and global records are diagnostic drift signals only.
  - Live subagent busy state is explicitly not inspected.
  - Visible route maps must be backed by refreshed Mermaid artifacts after route creation or mutation.
  - Role identity is split into `role_key`, `display_name`, and diagnostic-only `agent_id`.
- Validation:
  - `python .flowpilot\task-models\control-surface-protocol-patches\run_checks.py`
  - `python .flowpilot\task-models\external-watchdog-loop\run_checks.py`
  - `python simulations\run_meta_checks.py`
  - `python simulations\run_capability_checks.py`
  - `python scripts\check_install.py`
  - `python scripts\smoke_autopilot.py`
  - `python scripts\flowpilot_watchdog.py --root . --dry-run --json`
  - `python scripts\flowpilot_run_with_busy_lease.py --root . --operation "wrapper smoke" --max-minutes 1 --json -- python -c "print('lease-wrapper-ok')"`
