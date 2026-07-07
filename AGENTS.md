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

## No Compatibility Or Fallback Surfaces By Default

FlowPilot is a current-contract runtime. New planning, repair, prompt,
runtime, and validation work must keep one explicit structured path per
behavior. Do not add compatibility shims, legacy aliases, prose/shape guessing,
missing-field defaults, old-router fallback, newest-run fallback, repo-root
fallback, dual-authority paths, or automatic translation from old field names
unless the user explicitly approves a named migration.

Allowed recovery must stay current-runtime and model-owned: it must name the
single owner, current run, current packet or node, blocking state, required
repair command, and validation evidence. Recovery may reissue, block, or ask
for a current structured result; it must not silently convert old input into a
valid current result or treat historical artifacts as completion evidence.

When fixing a failure, delete or reject the unsupported path rather than
teaching the runtime to accept both old and new forms. Add a negative test for
each removed compatibility surface.

## Minimal Current-Contract Repair Framework

When repairing FlowPilot runtime, route, prompt, card, gate, or recovery
failures, prefer the smallest current-contract change that fixes the observed
state-machine problem. Do not add a new ledger, table, packet kind, prompt
channel, role, or state family when the existing packet/result/gate surfaces
can express the repair.

Use this default ownership split:

- Runtime/router owns mechanical validity: schema, packet kind, route scope,
  current run, current packet/result/node ids, path/hash presence, supported
  command names, and rejection of legacy aliases, wrappers, fallback prose, or
  missing-field defaults.
- FlowGuard owns substantive process and state review: whether the real current
  artifact, evidence, route effect, repair effect, or recovery effect can
  execute without stale evidence, loops, future-state assumptions, or broken
  refinement.
- Reviewer owns substantive quality review: whether the real current artifact
  satisfies the task, evidence is credible, contradictions are handled, and the
  output is good enough for the next gate or user-facing claim.

For gated side effects, prefer one lightweight staged-effect concept over
per-scenario candidate ledgers. A staged effect records only the current result
or gate identity, effect kind, target node/route/blocker when needed, status,
and the command or runtime path that will commit it after review. It must not
copy sealed bodies or recreate a parallel candidate system. Use staged effects
only for effects that are currently blocked by a real timing mismatch, such as
"review must inspect the real submitted artifact before runtime binds it as an
accepted node plan" or "route mutation must be reviewed before active route
version changes."

Before adding new fields or state, require a clear answer to all of these:

- Which observed blocker, loop, stale-evidence hazard, or unsupported path does
  this prevent?
- Can the same repair be represented with existing packet, result, gate,
  blocker, or route-node records?
- Is this mechanical validation better owned by runtime/router instead of
  FlowGuard or Reviewer?
- Does the added state have one owner, one commit point, a negative test, and a
  cleanup/terminal disposition?

If any answer is unclear, first reduce the repair plan instead of expanding the
runtime shape. Avoid recreating old-router complexity through many specialized
candidate records, compatibility surfaces, or role-specific state machines.

For FlowPilot current-contract repairs, also follow
`docs/flowpilot_current_contract_repair_discipline.md`. That document is the
durable rule set for future agents: shrink wrong requirements back to their
owning stage, keep role boundaries clean, cover all package and blocker repair
families, carry repeated-repair lineage, and leave old names only in
forbidden/deleted lists, negative tests, or historical labels.

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

FlowGuard agent skill suite:
- Primary agent surface: `.agents/skills/`
- Default entry skill: `.agents/skills/model-first-function-flow/SKILL.md`
- Complete AI-agent setup means the agent can read `AGENTS.md` and all
  FlowGuard sibling `SKILL.md` files under `.agents/skills/`.
- The Python `flowguard` module/CLI is executable check support, not the
  AI-agent skill installation surface.

Project FlowGuard record:
- Manifest: `.flowguard/project.toml`
- Machine log: `.flowguard/adoption_log.jsonl`
- Human log: `docs/flowguard_adoption_log.md`

Current adoption record:
- FlowGuard check-engine version: `0.52.5`
- FlowGuard schema version: `1.0`

Before non-trivial work:
1. Verify the real FlowGuard check engine:
   `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
2. Check the installed check-engine version:
   `python -c "import importlib.metadata as m; print(m.version('flowguard'))"`
3. Audit the project record:
   `python -m flowguard project-audit --root .`
4. Compare the installed version with `.flowguard/project.toml`.
5. If the installed version is newer, run:
   `python -m flowguard project-upgrade --root .`
   This updates the project record and scans existing FlowGuard artifacts,
   model evidence, tests, docs, and guidance for deterministic upgrades into
   the current FlowGuard shape. Use `--records-only` only when intentionally
   scoping out artifact/model/test upgrade scanning.
   Then rerun affected models/tests before broad confidence and record the result.
6. If the installed version is older than the project record, stop and connect
   a current FlowGuard check engine before claiming FlowGuard confidence.

FlowGuard runtime guidance is latest-schema-first: old artifacts may be
detected and upgraded at project/tool boundaries, but normal route logic should
not preserve long-lived compatibility branches for obsolete fields, aliases, or
wrappers.

Default replacement means dispose the old path, old field, alias, wrapper, or
fallback unless compatibility or preservation is explicitly requested. If
compatibility is explicit, record the preserved surface, compatibility intent,
and current evidence; otherwise delete, block, migrate, delegate, repair, or
scope it out with a concrete reason.

Field-bearing work should use or update FieldLifecycleMesh: high-level behavior
models include behavior-bearing fields, while child/leaf field rows account all
discovered fields and record owner, readers, writers, projection, lifecycle,
and old-field disposition.

UI runnable claims and file/work-package claims need current UI click-through
or artifact-payload evidence gates before broad done/release confidence.

Non-trivial rough-plan discussion, multi-skill/tool workflow setup, staged
execution, install/sync, release/archive/publish, post-change owner scans, and
final process claims enter `flowguard-development-process-flow` first as the
development-process simulator. Record `plan_detailing`, `agent_workflow`, and
`execution_freshness` modes; delegate to PlanDetailing or
AgentWorkflowRehearsal only when explicit or simulator-selected.

After non-trivial FlowGuard-managed work, let DevelopmentProcessFlow consume
post-change scan signals for changed artifacts, skipped routes, stale evidence,
open obligations, or split/reduction pressure. The scan output routes each gap
to the owning specialist, such as Model-Test Alignment, Architecture
Reduction, StructureMesh, ModelMesh, TestMesh, or AgentWorkflowRehearsal.

Do not create a fake local FlowGuard replacement. Do not claim full FlowGuard
completion from an AGENTS/manifest/log update alone; executable model checks,
tests, replay, and closure evidence still need to be current for the claim.
<!-- END FLOWGUARD PROJECT RULES -->
