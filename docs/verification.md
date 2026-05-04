# Verification

## Preflight Checks

Run:

```powershell
python simulations/run_startup_pm_review_checks.py
python simulations/run_release_tooling_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/audit_local_install_sync.py
python scripts/smoke_autopilot.py
```

Expected:

- zero invariant failures;
- zero missing required labels;
- zero progress findings;
- zero stuck states;
- reachable success.
- FlowPilot release tooling cannot publish or package companion skills.
- execution frontier and visible Codex plan sync labels are present before
  behavior-bearing work.
- startup PM-review checks reject shadow routes, report-only reviewer bypasses,
  wrong heartbeat cadence, and any work before PM startup opening.

Route-local models under `.flowpilot/task-models/` belong to an adopted target
project's runtime evidence. They should be checked when present in that target
project, but this public package check does not require this repository's
private development `.flowpilot/` state.

## Install Checks

Run:

```powershell
python scripts/install_flowpilot.py --check
python scripts/audit_local_install_sync.py
python scripts/check_install.py
```

Expected:

- real FlowGuard import works;
- `flowpilot.dependencies.json` parses;
- required project files exist;
- required dependencies are installed and fresh; missing optional companion
  skills are reported as warnings rather than blocking the FlowPilot package
  check;
- `skills/flowpilot/SKILL.md` exists and declares `name: flowpilot`;
- reusable FlowPilot templates exist;
- simulation scripts exist;
- template JSON files parse.
- `templates/flowpilot/execution_frontier.template.json` parses.
- repository-owned installed skills are source-fresh;
- installed skill names are unique, so stale backup skills cannot shadow the
  active FlowPilot skill;
- the legacy Cockpit prototype is absent from the active source tree before a
  from-scratch UI restart.
- If local `.flowpilot/` runtime state exists, its main JSON files parse.

## Public Release Check

Run before publishing this repository:

```powershell
python scripts/check_public_release.py
```

Expected:

- tracked files do not include `.flowpilot/`, `.flowguard/`, `kb/`, local
  environment files, caches, or secret-shaped content;
- the dependency manifest parses and has explicit sources for GitHub-backed
  dependencies;
- external dependency `SKILL.md` links are reachable when URL checking is not
  skipped;
- release tooling reports FlowPilot repository scope only and no companion
  publishing authority;
- validation commands pass.

If companion skill GitHub URLs are intentionally not filled in yet, the public
release check should block and report those missing sources. The user decides
whether and when to publish or update those companion skill repositories.

## Smoke Checks

Run:

```powershell
python scripts/smoke_autopilot.py
```

Expected:

- release tooling simulation passes;
- meta simulation passes;
- capability simulation passes.
- startup PM-review simulation passes.

## Startup PM Review Check

For an active target project after route, state, frontier, crew, role memory,
continuation, and visible-plan evidence have been written, the human-like
reviewer must personally check the real startup facts and write
`.flowpilot/runs/<run-id>/startup_review/latest.json`.

The reviewer report is not approval. It must check user authorization versus
actual state, route/state/frontier consistency, requested old-route or old-asset
cleanup, heartbeat or manual-resume evidence, background-agent role evidence,
and shadow or residual route state. If the report has blockers, the
PM sends remediation back to authorized workers through a packet and requires another
reviewer report.

After the project manager opens `pm_start_gate` from the current clean reviewer
report, PM writes `.flowpilot/runs/<run-id>/startup_pm_gate/latest.json` and updates state
plus frontier with `work_beyond_startup_allowed: true`.

Expected:

- `.flowpilot/current.json` resolves to the active run and
  `.flowpilot/index.json` records that run;
- current-run `state.json`, `execution_frontier.json`, and
  `routes/<active-route>/flow.json`
  agree on the same active nonterminal route;
- old top-level control state is absent, legacy-only, or quarantined and is
  not used as current state;
- continuing prior work has a current-run prior-work import packet;
- `crew_ledger.json` is current for that route and all six role memory packets
  are present and current;
- continuation is either a complete automated bundle or explicit
  `manual-resume` evidence with no automation claim;
- `startup_activation.live_subagent_startup` records either six live
  background agents started/resumed after a user decision or explicit
  user-authorized single-agent six-role continuity;
- `startup_activation.startup_preflight_review` records a clean report-only
  reviewer audit;
- `startup_activation.pm_start_gate` records the project manager's open
  decision based on that report;
- `startup_activation` in state and frontier records the hard gate and sets
  `work_beyond_startup_allowed: true`.

If the reviewer report is blocked or PM has not opened startup, FlowPilot must
not run child skills, image generation, implementation, route chunks, or
completion work. A route-local file without matching canonical
state/frontier/crew/continuation evidence is a shadow route, not a recoverable
partial pass.

## Heartbeat Lifecycle Check

Run:

```powershell
python scripts/flowpilot_lifecycle.py --root . --mode scan --write-record --json
```

Expected:

- the active route, latest heartbeat/manual-resume evidence, state, and
  execution frontier are loaded;
- automated routes record a one-minute heartbeat schedule and official
  automation source when supported;
- manual-resume routes record that no heartbeat automation exists;
- terminal routes write inactive lifecycle state back to state/frontier
  evidence before completion is claimed.

## Lifecycle Reconciliation Check

Before pausing, restarting, or closing a formal route, run a unified lifecycle
inventory:

```powershell
python scripts/flowpilot_lifecycle.py --root . --mode pause --write-record --json
python scripts/flowpilot_lifecycle.py --root . --mode restart --write-record --json
python scripts/flowpilot_lifecycle.py --root . --mode terminal --write-record --json
```

Use the mode that matches the lifecycle operation. The command is read-only
except for writing `.flowpilot/runs/<run-id>/lifecycle/latest.json` and events. It does not
change Codex automations. If it reports required actions, complete them through
the official Codex app automation interface, then rerun the inventory before
claiming pause, restart, or terminal cleanup.

Expected:

- Codex heartbeat automations, local state, execution frontier, and
  heartbeat/manual-resume evidence are all represented;
- local state/frontier lifecycle fields agree with the intended operation;
- `.flowpilot/runs/<run-id>/lifecycle/latest.json` exists for the latest lifecycle operation.
