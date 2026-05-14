# AGENTS.md

## Operating Rule

This repository implements the `flowpilot` Codex skill.

Before implementation work, read:

- `HANDOFF.md`
- `.flowpilot/state.json` if this clone is already inside an active
  FlowPilot-controlled route
- `.flowpilot/routes/route-001/flow.json` if present for the active route
- `docs/flowguard_preflight_findings.md`
- `simulations/capability_model.py`
- `simulations/meta_model.py`

## FlowGuard Requirement

Use real FlowGuard. Do not create a fake mini-framework.

Long-running FlowGuard checks in this repository use a stable background log
contract. Default to `tmp/flowguard_background/` and use the command base name
for these artifacts:

- `<name>.out.txt` for stdout;
- `<name>.err.txt` for stderr and progress;
- `<name>.combined.txt` for human-readable merged output;
- `<name>.exit.txt` for the process exit code;
- `<name>.meta.json` for command, start/end time, status, and proof-reuse
  metadata.

For the heavyweight project checks, use these base names:

- `run_meta_checks` for `python simulations/run_meta_checks.py`;
- `run_capability_checks` for
  `python simulations/run_capability_checks.py`.

Before reporting a long check as complete, inspect the actual artifacts and
report the log root, stdout/stderr/combined paths, exit code, latest update
time, completion status, and whether a valid proof was reused. A path-only
report, an in-progress log, or a missing exit artifact is not completion
evidence. Progress lines are liveness evidence only; pass/fail still comes from
the executable check result and exit code.

Before changing behavior-bearing protocol, route, or skill logic, verify:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
```

If the change affects the project-control flow, update and rerun:

```powershell
python simulations/run_meta_checks.py
```

If the change affects skill/capability routing, update and rerun:

```powershell
python simulations/run_capability_checks.py
```

## Coordination

Keep edits scoped. This project is expected to be worked on by agents that may
resume from local files rather than chat history.

When this repository is being developed under an active FlowPilot route, update
that workspace's `.flowpilot/` state when changing the plan:

- route structure changes: create a new route version;
- execution progress: update `state.json`, heartbeat records, and node reports;
- capability decisions: update `capabilities.json` and capability evidence;
- major verified milestone: write a checkpoint.

## Documentation Language

Use English for repository files. The project is intended for public GitHub
distribution and cross-agent handoff.

## Hard Gates

Never silently change these without explicit user approval:

- frozen acceptance contract;
- release/publish/deploy actions;
- major technology stack changes;
- destructive or irreversible changes;
- handling secrets or private account data;
- lowering completion standards.
