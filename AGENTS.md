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

## FlowGuard Project Topology

This mature FlowGuard project maintains an automatically generated project
topology map:

- Machine artifact: `docs/flowguard_project_topology.json`
- Human artifact: `docs/flowguard_project_topology.md`
- Generator/checker: `python scripts/flowguard_project_topology.py build`
  and `python scripts/flowguard_project_topology.py check`

Before non-trivial planning, proposal, coding, prompt/card, model, test,
release, install, or validation work, read the topology Markdown after the
standard FlowGuard package/project audit. Use it as background architecture for
which model families, tests, code surfaces, evidence summaries, and known-bad
signals to inspect next.

The topology is orientation only. It is not a FlowGuard Report, not child model
evidence, not test evidence, and not a release or install pass. Completion
claims still need the owning executable checks, result artifacts, install
audits, and freshness evidence.

When FlowGuard models, runners, result paths, tests, code ownership surfaces,
prompt/card boundaries, AGENTS rules, or readiness checks change, rebuild and
check the topology before claiming done, or explicitly report why it is left
stale.

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

<!-- BEGIN FLOWGUARD PROJECT RULES -->
## FlowGuard Project Rules

This project uses FlowGuard for non-trivial maintenance, feature work, bug
fixes, refactors, tests, release work, project upgrades, and evidence-sensitive
process changes.

FlowGuard repository:
https://github.com/liuyingxuvka/FlowGuard

Project FlowGuard record:
- Manifest: `.flowguard/project.toml`
- Machine log: `.flowguard/adoption_log.jsonl`
- Human log: `docs/flowguard_adoption_log.md`

Current adoption record:
- FlowGuard package version: `0.39.1`
- FlowGuard schema version: `1.0`

Before non-trivial work:
1. Verify the real package:
   `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
2. Check the installed package version:
   `python -c "import importlib.metadata as m; print(m.version('flowguard'))"`
3. Audit the project record:
   `python -m flowguard project-audit --root .`
4. Compare the installed version with `.flowguard/project.toml`.
5. If the installed version is newer, run:
   `python -m flowguard project-upgrade --root .`
   Then rerun affected models/tests before broad confidence and record the result.
6. If the installed version is older than the project record, stop and upgrade
   the local FlowGuard toolchain before claiming FlowGuard confidence.

Do not create a fake local FlowGuard replacement. Do not claim full FlowGuard
completion from an AGENTS/manifest/log update alone; executable model checks,
tests, replay, and closure evidence still need to be current for the claim.
<!-- END FLOWGUARD PROJECT RULES -->
