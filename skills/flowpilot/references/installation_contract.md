# Installation Contract

FlowPilot requires:

- real `flowguard` Python package;
- installed/readable `model-first-function-flow` skill;
- this `flowpilot` skill;
- writable project workspace for `.flowpilot/`;
- Python available on `PATH` for checks and task-local models.
- optional external scheduler, such as Windows Task Scheduler, when a formal
  route needs an outside watchdog in addition to Codex host automation.

Minimum runtime check:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python scripts/check_install.py
python scripts/flowpilot_watchdog.py --root . --stale-minutes 10 --dry-run --json
```

Expected result:

- FlowGuard import succeeds;
- schema version is reported;
- `skills/flowpilot/SKILL.md` exists and declares `name: flowpilot`;
- template and simulation files exist;
- project-control files under `.flowpilot/` exist.
- the watchdog can read `.flowpilot/state.json`, the active route, and the
  latest heartbeat, then plan or perform an automation reset without claiming
  recovery before a later heartbeat proves it.

If dependencies are missing, the installing agent should connect the real
FlowGuard source before using this skill. Do not create a local mini-framework
or bypass the dependency check.

## Automatic Installation Policy

FlowPilot may automatically install missing project-local tools and libraries
when all of these are true:

- the dependency is needed for the active route node, current chunk, checks, or
  implementation;
- the install is local to the project or active virtual environment;
- it does not require secrets, payment, private accounts, or global system
  changes;
- it is reversible by normal project dependency cleanup;
- the agent records the command and verification result.

Startup should write a dependency plan and install only the minimum tooling
needed to run FlowPilot and current model checks. Future route, chunk, UI,
native-build, or packaging dependencies should be recorded as `deferred` until
their node or verification command is active.

Ask the user before heavy, global, system-wide, paid, private-account,
destructive, or irreversible installation work.

User approval permits the install when it becomes necessary. It does not mean
all approved tools should be installed at startup.

FlowPilot v1 intentionally avoids being a standalone package manager. That does
not prohibit automatic dependency installation during a project run.
